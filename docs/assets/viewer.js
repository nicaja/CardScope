// The saved projection sits next to the page in data/, so any static host can serve both.
const plot = document.getElementById('plot');
const colorMode = document.getElementById('colorMode');
const typeFilter = document.getElementById('typeFilter');
const search = document.getElementById('search');
const extent = document.getElementById('extent');
let fullExtent = false;
let viewRevision = 0;
let pendingSearch;
function status(message) { const note = document.createElement('p'); note.className = 'plot-status'; note.textContent = message; plot.replaceChildren(note); }
let data;
try {
  const response = await fetch(new URL('../data/embedding-space.json', import.meta.url));
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  data = await response.json();
} catch (error) {
  status('The card data could not load. Reload the page to try again.');
  throw error;
}
const { points: allPoints, palette, limits } = data;
const categoryColors = Object.values(palette);
Object.keys(palette).forEach(label => { const option = document.createElement('option'); option.value = label; option.textContent = label; typeFilter.append(option); });
function hash(value) { let result = 2166136261; for (const char of value) result = Math.imul(result ^ char.charCodeAt(0), 16777619); return result >>> 0; }
function color(point) {
  if (colorMode.value === 'card_type') return palette[point.card_type];
  return categoryColors[hash(point.set_id) % categoryColors.length];
}
function escapeText(value) { return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c])); }
function focused(point) { return ['x','y','z'].every((axis, i) => point[axis] >= limits[i][0] && point[axis] <= limits[i][1]); }
function trace(points, opacity, highlighted = false) {
  return { type:'scatter3d', mode:'markers', x:points.map(p=>p.x), y:points.map(p=>p.y), z:points.map(p=>p.z), customdata:points,
    text:points.map(p => `${escapeText(p.name)}<br>${escapeText(p.set_id)} · ${escapeText(p.number)}<br>${escapeText(p.card_type)}`),
    hovertemplate:'%{text}<extra></extra>', marker:{size:highlighted ? 5 : 2.2, opacity, color:points.map(color), line:{width:0}} };
}
function axis(title, i) { return { title:{text:title,font:{size:12}}, color:'#aab3c2', gridcolor:'#29313c', zeroline:false, showbackground:false, nticks:5, ...(fullExtent ? {autorange:true} : {range:limits[i]}) }; }
function legend(points) {
  const list = document.getElementById('legend'); list.replaceChildren();
  document.getElementById('legendTitle').textContent = colorMode.value === 'set_id' ? 'Sets · inspect a point for its set' : 'Card types';
  if (colorMode.value === 'set_id') { const li = document.createElement('li'); li.textContent = `${new Set(points.map(p=>p.set_id)).size} sets; colours repeat across sets.`; list.append(li); return; }
  Object.keys(palette).forEach(label => { const selected = points.filter(p=>p.card_type === label); if (!selected.length) return;
    const li=document.createElement('li'), swatch=document.createElement('span'), name=document.createElement('span'), count=document.createElement('span');
    swatch.className='swatch'; swatch.style.background=color(selected[0]); name.textContent=label; count.className='count'; count.textContent=selected.length.toLocaleString(); li.append(swatch,name,count); list.append(li); });
}
function showPoint(point) {
  document.getElementById('detailName').textContent = point.name || point.id;
  const meta=document.getElementById('detailMeta'); meta.replaceChildren();
  [point.card_type, `${point.set_id} · ${point.number}`, point.set_name, point.uid].filter(Boolean).forEach(value=>{const line=document.createElement('div');line.textContent=value;meta.append(line);});
  const img=document.getElementById('detailImage'); if (/^https:\/\//.test(point.image_url)) img.src=point.image_url; else img.removeAttribute('src'); img.alt=point.name || point.id;
  const links=document.getElementById('detailLinks'); links.replaceChildren();
  if (/^https:\/\//.test(point.marketplace_url)) { const link=document.createElement('a');link.href=point.marketplace_url;link.textContent='Open catalogue entry';link.target='_blank';link.rel='noreferrer';links.append(link); }
}
function render() {
  if (!window.Plotly) { status('Plotly could not load. Check your connection and reload the page.'); return; }
  plot.querySelector('.plot-status')?.remove();
  const points=allPoints.filter(p=>typeFilter.value === 'all' || p.card_type === typeFilter.value);
  const query=search.value.trim().toLowerCase(); const matches=query ? points.filter(p=>(p.search+' '+p.card_type).toLowerCase().includes(query)) : [];
  const traces=query ? [trace(points,.10),trace(matches,.98,true)] : [trace(points,.85)];
  legend(points);
  const inView=fullExtent ? points.length : points.filter(focused).length;
  document.getElementById('viewNote').textContent=`${inView.toLocaleString()} of ${points.length.toLocaleString()} cards in ${fullExtent ? 'full' : 'focused'} view${query ? ` · ${matches.length.toLocaleString()} search matches` : ''}. ${fullExtent ? '' : 'Use Full extent to include outliers.'}`;
  window.Plotly.react(plot,traces,{paper_bgcolor:'#0d1117',plot_bgcolor:'#0d1117',margin:{l:0,r:0,t:0,b:0},uirevision:viewRevision,
    scene:{xaxis:axis('UMAP 1',0),yaxis:axis('UMAP 2',1),zaxis:axis('UMAP 3',2),bgcolor:'#0d1117',aspectmode:'data',camera:{eye:{x:1.2,y:1.2,z:.8}}},showlegend:false},
    {responsive:true,displaylogo:false}).then(()=>{ if(plot.dataset.bound) return; plot.dataset.bound='true'; ['plotly_hover','plotly_click'].forEach(event=>plot.on(event,e=>{const point=e.points?.[0]?.customdata;if(point)showPoint(point);})); });
}
colorMode.addEventListener('change',render); typeFilter.addEventListener('change',render);
search.addEventListener('input',()=>{clearTimeout(pendingSearch);pendingSearch=setTimeout(render,160);});
extent.addEventListener('click',()=>{fullExtent=!fullExtent;viewRevision++;extent.textContent=fullExtent ? 'Focused view' : 'Full extent';render();});
document.getElementById('reset').addEventListener('click',()=>{fullExtent=false;viewRevision++;extent.textContent='Full extent';colorMode.value='card_type';typeFilter.value='all';search.value='';render();});
render();
