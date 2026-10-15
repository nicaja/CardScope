# CardScope — Pokémon Card Recognition with DINOv3

[![Japanese Pokémon cards in DINOv3 feature space, coloured by card type and turning slowly](docs/figures/embedding-space.gif)](https://nicaja.github.io/CardScope/)

*Japanese Pokémon cards in DINOv3 feature space. [Open the interactive view](https://nicaja.github.io/CardScope/) to rotate it, highlight a card or set, and see each card's image.*

An ongoing research project exploring how visual embeddings identify Japanese Pokémon cards from photographs. DINOv3 provides the image representation; OpenCV, OCR, and catalogue metadata help distinguish the exact set, printing, and variant. A mobile web interface connects recognition experiments with price comparison.

## Inside the embedding space

The [interactive view](https://nicaja.github.io/CardScope/) runs in the browser. Rotate the projection, highlight a card or set, filter by card type, or switch between type, set, and source colours. Hover over a point to see the card and its catalogue entry. Use **Full extent** to see outliers beyond the initial close view.

The saved experiment contains **23,362 cards** represented by **DINOv3 ViT-B/16**, using the mean of the CLS token and four register tokens. The full-card vectors are projected into three dimensions with UMAP and cosine distance. The original coordinates are retained.

Colours distinguish Pokémon, Supporters, Items, Pokémon Tools, Stadiums, and Energy cards using labels from the official catalogue. The 536 cards without verified labels remain **Unknown**. The animation at the top shows 22,660 points in a closer view; all 23,362 are in the interactive view. [Figure provenance](docs/figures/embedding-provenance.json).

The projection is useful for inspecting how card layouts organise the representation. Separation in UMAP is not a measurement of recognition accuracy.

## Recognition experiments

- **Representation:** pretrained DINOv3 embeddings, L2 normalisation, and CLS/register-token pooling.
- **Retrieval:** cosine similarity against reference cards, with full-card and cropped reference views.
- **Identification:** OpenCV image evidence, OCR of names and collector numbers, and metadata-based reranking.
- **Application:** matching identified prints to market-price sources and inspecting results through a Next.js interface.

`tools/card_matcher/` contains the Python experiments, including the DINOv3 implementation and the [viewer renderer](tools/card_matcher/render_embedding_space.py). `docs/` holds the interactive page, which GitHub Pages serves. `src/` contains the interface, provider adapters, and price calculations. The [architecture report](docs/pokearbitrage_architecture_report.pdf) records the broader project design.

## Local exploration

Use Node.js 22 LTS, run `npm ci`, then `npm run dev`. The app opens directly, with no passcode. DINOv3 setup and commands are in the [matcher README](tools/card_matcher/README.md); optional services are configured through `.env.example`.

This remains a research prototype with incomplete card and price coverage. Model weights, reference-image caches, personal photos, and credentials are not included. Account-backed services are intended for local use.

Software checks: `npm test`, `npm run lint`, and `npm run build`. These check code behaviour, not real-photo recognition accuracy.
