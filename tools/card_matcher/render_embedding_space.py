"""Render an existing embedding projection; never fit embeddings or UMAP here."""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import html
import json
from pathlib import Path
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
import numpy as np
from PIL import Image

PALETTE = {
    'Pokémon': '#6dd6b0', 'Supporter': '#f2b66d', 'Item': '#78b7ee',
    'Pokémon Tool': '#c3a0f0', 'Stadium': '#f08b93', 'Energy': '#e7d96f',
    'Other Trainer': '#c5b59b', 'Unknown': '#8994a7',
}
HEADINGS = {'サポート': 'Supporter', 'グッズ': 'Item', 'ポケモンのどうぐ': 'Pokémon Tool',
            'スタジアム': 'Stadium', '基本エネルギー': 'Energy', '特殊エネルギー': 'Energy', 'エネルギー': 'Energy'}
STYLE = {'font.family': 'DejaVu Sans', 'text.color': '#e6edf3', 'axes.labelcolor': '#aab3c2', 'xtick.color': '#aab3c2', 'ytick.color': '#aab3c2'}
BACKGROUND = '#0d1117'

def classify(point: dict, metadata_dir: Path) -> dict:
    """Use explicit official detail-page headings; never infer subtype from a name."""
    point = dict(point)
    point['card_type'] = 'Unknown'
    point['card_type_source'] = 'unavailable'
    if not point['id'].startswith('official-jp-'):
        return point
    source = metadata_dir / f"{point['id'].removeprefix('official-jp-')}.html"
    if not source.exists():
        return point
    text = source.read_text(encoding='utf-8')
    headings = [html.unescape(re.sub('<[^>]+>', '', h)).strip() for h in re.findall(r'<h2\b[^>]*>(.*?)</h2>', text, re.S)]
    for heading in headings:
        if heading in HEADINGS:
            point['card_type'] = HEADINGS[heading]
            point['card_type_source'] = 'official-detail-heading'
            break
    if point['card_type'] == 'Unknown' and 'hp-type' in text and 'ワザ' in headings:
        point['card_type'] = 'Pokémon'
        point['card_type_source'] = 'official-hp-and-attacks'
    if point['card_type'] == 'Unknown' and any(h in {'トレーナー', 'トレーナーズ'} for h in headings):
        point['card_type'] = 'Other Trainer'
        point['card_type_source'] = 'official-detail-heading'
    return point

def draw(points: list[dict], coords: np.ndarray, visible: np.ndarray, bounds: np.ndarray) -> tuple[plt.Figure, plt.Axes]:
    """Dark focused view shared by the still figure and the turntable. Call inside plt.rc_context(STYLE)."""
    counts = Counter(p['card_type'] for p in points)
    fig = plt.figure(figsize=(12, 8), facecolor=BACKGROUND)
    ax = fig.add_axes([.015, .10, .76, .84], projection='3d', facecolor=BACKGROUND)
    for category, color in PALETTE.items():
        select = np.array([p['card_type'] == category for p in points]) & visible
        ax.scatter(*coords[select].T, c=color, s=3.0, alpha=.72, edgecolors='none', depthshade=False, rasterized=True)
    ax.set(xlim=bounds[0], ylim=bounds[1], zlim=bounds[2], xlabel='UMAP 1', ylabel='UMAP 2', zlabel='UMAP 3')
    ax.view_init(elev=21, azim=-62)
    ax.set_box_aspect(np.diff(bounds, axis=1).ravel(), zoom=1.02)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.set_major_locator(MaxNLocator(4))
        axis.pane.fill = False
        axis.pane.set_edgecolor('#29313c')
        axis.line.set_color('#484f58')
        axis._axinfo['grid']['color'] = '#29313c'
        axis.set_tick_params(labelsize=9, colors='#aab3c2')
    fig.text(.05, .955, 'Pokémon cards in DINOv3 feature space', fontsize=19, weight='medium')
    handles = [Line2D([], [], marker='o', linestyle='', color=color, markersize=6, label=f'{category}  {counts[category]:,}') for category, color in PALETTE.items() if counts[category]]
    fig.legend(handles=handles, loc='upper left', bbox_to_anchor=(.755, .8), frameon=False, fontsize=10, labelspacing=1.0, title='Card type · all cards', title_fontsize=11)
    fig.text(.05, .045, f'{len(points):,} cards · CLS + register-token mean · 3D UMAP\nFocused view: {visible.sum():,} points shown; all points remain in the interactive viewer.', fontsize=10, color='#aab3c2', linespacing=1.6)
    return fig, ax

def write_turntable(fig: plt.Figure, ax: plt.Axes, path: Path, frames: int = 288, dpi: int = 80) -> None:
    """Turn the still figure's view once, slowly, for the README: 1.25 degrees per 100 ms frame.

    The axes are hidden while turning, because matplotlib moves axis lines and titles to whichever
    box edges face the camera, so they jump sides every quarter turn. Card types keep their drawing
    order for the same reason; depth-sorting whole groups makes overlapping colours swap suddenly.
    The GIF palette is built from the figure's own colours faded into the background, so every
    card type keeps its colour and the background stays exactly BACKGROUND.
    """
    fig.set_dpi(dpi)
    ax.set_axis_off()
    ax.computed_zorder = False
    images = []
    for step in range(frames):
        ax.view_init(elev=21, azim=-62 + 360 * step / frames)
        fig.canvas.draw()
        images.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3]))
    ax.view_init(elev=21, azim=-62)
    ax.computed_zorder = True
    ax.set_axis_on()
    background = np.array(to_rgb(BACKGROUND))
    inks = [np.array(to_rgb(ink)) for ink in [*PALETTE.values(), '#e6edf3', '#aab3c2', '#484f58', '#29313c']]
    colours = [background] + [background + t * (ink - background) for ink in inks for t in np.linspace(.1, 1, 10)]
    palette = Image.new('P', (1, 1))
    palette.putpalette([round(255 * channel) for colour in colours for channel in colour])
    indexed = [image.quantize(palette=palette, dither=Image.Dither.NONE) for image in images]
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=100, loop=0)

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--points', type=Path, required=True)
    parser.add_argument('--metadata-dir', type=Path, required=True, help='Cached official detail HTML directory; no network requests are made.')
    parser.add_argument('--output-dir', type=Path, required=True, help='The site folder, docs/ in this repository: writes data/ and figures/.')
    args = parser.parse_args()
    data = json.loads(args.points.read_text(encoding='utf-8'))
    with ThreadPoolExecutor(max_workers=8) as pool:
        points = list(pool.map(lambda p: classify(p, args.metadata_dir), data['points']))
    coords = np.array([[p[k] for k in ('x', 'y', 'z')] for p in points])
    assert np.isfinite(coords).all()
    bounds = np.quantile(coords, [.005, .995], axis=0).T
    visible = np.all((coords >= bounds[:, 0]) & (coords <= bounds[:, 1]), axis=1)
    counts = Counter(p['card_type'] for p in points)
    figures = args.output_dir / 'figures'
    figures.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'data').mkdir(exist_ok=True)
    # The page (index.html) fetches this file; keys and dumps settings match the earlier inlined viewer.
    data_path = args.output_dir / 'data' / 'embedding-space.json'
    payload = {'summary': data['summary'], 'palette': PALETTE, 'limits': bounds.tolist(), 'points': points}
    data_path.write_bytes(json.dumps(payload, ensure_ascii=True).encode('utf-8'))
    with plt.rc_context(STYLE):
        fig, ax = draw(points, coords, visible, bounds)
        fig.savefig(figures / 'embedding-space.png', dpi=180, facecolor=fig.get_facecolor())
        write_turntable(fig, ax, figures / 'embedding-space.gif')
        plt.close(fig)
    provenance = {
        'summary': data['summary'], 'points_json_sha256': hashlib.sha256(args.points.read_bytes()).hexdigest(),
        'data_sha256': hashlib.sha256(data_path.read_bytes()).hexdigest(),
        'coordinate_transform': 'None: existing x/y/z retained exactly; no embedding or UMAP fit.',
        'card_types': dict(counts), 'category_sources': dict(Counter(p['card_type_source'] for p in points)),
        'category_method': 'Explicit headings or HP/attack sections in locally cached official catalogue pages. Missing labels remain Unknown.',
        'focused_bounds': bounds.tolist(), 'focused_points': int(visible.sum()),
        'view': 'Dark categorical preview. Axis bounds at the 0.5th and 99.5th percentiles; HTML Full extent restores all points.',
        'renderer': 'tools/card_matcher/render_embedding_space.py',
    }
    (figures / 'embedding-provenance.json').write_text(json.dumps(provenance, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
    print(json.dumps({'cards': len(points), 'focused_points': int(visible.sum()), 'card_types': dict(counts)}, ensure_ascii=True))

if __name__ == '__main__':
    main()
