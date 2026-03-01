# Materialism — Session Handoff Document

## What This Project Is

Materialism is an open-source web-based alternative to HSPiP ($1,195 commercial software) for computing, visualizing, and optimizing Hansen Solubility Parameters (HSP). It predicts whether materials are compatible — will a solvent dissolve a polymer, will a coating adhere, will nanoparticles disperse.

Every material gets three values (δD, δP, δH) in MPa½. Compatibility is predicted by the distance formula: `Ra² = 4(δD₁-δD₂)² + (δP₁-δP₂)² + (δH₁-δH₂)²`. If `Ra < R₀` (the solubility sphere radius), materials are compatible. RED = Ra/R₀: below 1 = compatible, above 1 = incompatible.

**Live site**: Deployed to GitHub Pages via `materialism.html → index.html`. The deploy workflow triggers on pushes to `main` and the `claude/hansen-solubility-planning-D5iok` branch.

---

## Architecture & How It's Structured

### Everything is generated into self-contained HTML files

The app is NOT a React/Vue SPA. It's **standalone HTML files with all data baked in as JSON**. No server required — works offline from `file://`.

The generation pipeline:
```
data/datasets/*/chemicals.csv + polymers.csv
        ↓  (build_unified.py)
data/processed/unified_chemicals.csv + unified_polymers.csv
        ↓  (generate_html.py)
materialism.html  ← main app (search page)
database.html     ← database management page
```

`generate_html.py` (5,322 lines) is the single most important file. It:
1. Reads unified CSVs (chemicals + polymers)
2. Reads per-dataset data from `data/datasets/*/`
3. Loads manifest metadata from `data/manifest.json`
4. Embeds Plotly.js inline for offline use
5. Generates all CSS, HTML, and JavaScript as one giant f-string
6. Writes `materialism.html` and `database.html`

### Two main pages

**materialism.html** (the search page / main app):
- Header with "Materialism" title and stats (solvent/polymer counts)
- Search bar with natural language queries ("good solvents for polystyrene", "what dissolves nylon", "solvents similar to toluene")
- "Common Materials Only" toggle to filter to ~90 readily-available lab solvents
- Example query chips below search bar
- Result count selector (10/25/50)
- Left panel: 3D Plotly scatter plot (WebGL) with custom overlay legend
  - Solvents = colored circles, Polymers = colored diamonds
  - Colors by chemical category (hydrocarbon, aromatic, ketone, etc.) or polymer type
  - Legend has collapsible Solvents/Polymers groups with per-category toggles
  - Solubility sphere overlay when a polymer is the search target
  - Custom tooltip system using Plotly scene annotations (not native hover)
- Right panel: Either search results table (when searching) or home panel with Solvents/Polymers tabs showing all materials
- Linked selection: clicking a row highlights the marker on the plot and vice versa

**database.html** (the database management page):
- Sidebar with "Active Database" button and per-dataset cards
- Active Database view: merged/deduplicated data from all active datasets
  - Solvents and Polymers tabs
  - Lock/unlock toggle for inline cell editing
  - Infer Missing Values button (uses Claude API to fill gaps)
  - Cell drag-select and row selection
  - CAS crosslink badges for materials missing CAS numbers
- Per-dataset view: click a dataset card to see its raw data
  - Delete button for user-imported datasets
  - Toggle active/inactive for search page filtering
- Import section: upload CSV/Excel, paste URL, or search for databases via Claude API
- Export: download any dataset as CSV

### Data pipeline

```
Raw sources (.xlsx, .csv, .json) in data/raw/
    ↓
Per-dataset standardization in data/datasets/<id>/chemicals.csv
    ↓  (build_unified.py — merge, deduplicate, classify, score confidence, enrich CAS)
data/processed/unified_chemicals.csv (1,630 records)
data/processed/unified_polymers.csv (471 records)
    ↓  (generate_html.py — embed as JSON in HTML)
materialism.html + database.html
```

Five active datasets:
- **hansen_a1**: 1,130 solvents from Hansen Handbook 2007
- **hansen_a2**: 466 polymers from Hansen Handbook 2007
- **hspip_solvents**: 1,218 solvents from HSPiP database
- **accudyne_solvents**: 87 solvents from Accudyne surface tension database
- **accudyne_polymers**: 40 polymers from Accudyne

### Backend (mostly for the data pipeline, not serving)

- `backend/app/services/hsp_calculator.py` — All HSP math (distance, RED, mixture blending, solvent ranking, sphere fitting, blend optimization). Fully tested.
- `backend/app/models/database.py` — SQLAlchemy models (Chemical, Polymer, SolubilityTest, Mixture, MixtureComponent). SQLite backend.
- `backend/app/data/seed_data.py` — Seeds the SQLite database from unified CSVs.
- `backend/tests/test_hsp_calculator.py` — 13 pytest cases covering all HSP math.

### Support libraries

- `lib/schema.py` — Canonical field definitions & column alias mapping
- `lib/normalize.py` — Chemical name/CAS normalization
- `lib/classify.py` — Chemical/polymer categorization into 20+ categories
- `lib/confidence.py` — Confidence scoring (based on source quality, completeness)
- `lib/merge.py` — Cross-dataset deduplication logic
- `lib/import_utils.py` — File type detection and parsing

### Key scripts

- `build_unified.py` — Merges all datasets into unified CSVs
- `generate_html.py` — Generates the HTML pages
- `import_dataset.py` — CLI tool for importing new datasets
- `enrich_cas.py` / `enrich_properties.py` — CAS number and property enrichment via PubChem
- `clean_database.py` — Database maintenance

---

## Current Limitations

### Structural / Technical
1. **generate_html.py is 5,322 lines of Python generating JavaScript as f-strings** — extremely difficult to debug, no syntax highlighting for the JS, escape sequences cause bugs (e.g., `{{` vs `{` confusion). Every JS change requires regenerating the HTML.
2. **No component system** — all UI is monolithic HTML/JS inside f-strings. No reusable components, no module system.
3. **Data is baked at generation time** — adding/editing data requires re-running `generate_html.py`. The database page works around this with localStorage edits and imported datasets, but the search page only sees what was baked in.
4. **SQLite, not PostgreSQL** — adequate for 1,600 records but won't scale to 10k+ with efficient nearest-neighbor search.
5. **No pgvector** — nearest-neighbor search is brute-force (fine at current scale).
6. **The Dash app (backend/app/main.py) and the static HTML pages have diverged** — the static HTML pages are the real product; the Dash app is mostly unused now.

### Data
7. **~1,630 chemicals and ~471 polymers** — far short of the 10k+ goal. The HSP estimation engine (Phase 5) that would predict HSP from molecular structure hasn't been started.
8. **No RDKit integration** — can't parse SMILES or identify functional groups.
9. **No group contribution method** — can't estimate HSP for arbitrary molecules.
10. **~12% of chemicals still missing CAS numbers** — CAS review tool exists but requires manual curation.

### UI/UX
11. **Tooltip system is fragile** — custom annotation-based tooltips required extensive debugging (plot freezing, annotation clearing). Native Plotly hover is disabled via CSS.
12. **Color consistency issues** — multiple rounds of fixes for markers rendering gray, wrong category colors after filtering, etc.
13. **No mixture calculator on the search page** — the Dash app had one but the static HTML search page doesn't.
14. **No sphere fitting UI on the search page** — same story, was in Dash but not ported.
15. **Mobile responsiveness is limited** — layout is desktop-optimized with fixed heights.

---

## What's Been Built (Phase Status)

- **Phase 1 (Data Foundation)**: DONE — searchable database, CSV import, multi-source merge, CAS enrichment, classification, confidence scoring
- **Phase 2 (Core HSP Calculations)**: DONE — distance, RED, mixture blending, ranking, sphere fitting, blend optimization. All tested.
- **Phase 3 (3D Visualization)**: DONE — 3D scatter, sphere overlay, category colors, 2D projections, linked selection, custom tooltips, legend toggles
- **Phase 4 (Solvent Optimizer)**: PARTIALLY DONE — ranking works on search page; blend optimization exists in backend but not fully exposed in UI
- **Phase 5 (HSP Estimation Engine)**: NOT STARTED — no RDKit, no group contribution, no SMILES parsing
- **Phase 6 (Advanced Features)**: NOT STARTED — no temperature modeling, no PDF reports, no user accounts

---

## User Preferences & Design Opinions

These are the design decisions and preferences that have been established through development:

### Architecture Preferences
1. **Static HTML over server-dependent apps** — The product is standalone HTML files that work offline. No server dependency for the end user. This is a core design principle.
2. **Client-side everything** — File upload, PDF parsing, URL analysis, and even Claude API calls are done client-side in the browser. The backend is for data pipeline only.
3. **GitHub Pages deployment** — Push to branch → auto-deploy. `materialism.html` gets copied to `index.html`.

### UI/UX Preferences
4. **Light mode only** — the UI uses a light theme (#f5f6fa background, #2d3436 text, #e94560 accent/brand color).
5. **No emojis in the UI**.
6. **Column header naming**: "Classification" not "Type" or "Category" for the chemical/polymer type field.
7. **The "Abbreviation" column was added then removed** — decided it wasn't needed.
8. **The "Industry Uses" / "Commercial Products" column was added then removed** — too noisy.
9. **Confidence/Source columns removed from the search page** — cluttered the results. Kept on database page.
10. **Dataset selection checkboxes removed from search page** — filtering happens via the database page toggles instead.
11. **Column width lock button removed from homepage table** — unnecessary UI chrome.
12. **Units in column headers** — δD, δP, δH show MPa½; MW shows g/mol; BP shows °C. Use superscript for ½.
13. **Solvents = circles, Polymers = diamonds** on the 3D plot. This is consistent and important.
14. **Custom legend overlay** on the 3D plot with collapsible Solvents/Polymers groups and per-category toggles. Top-level headers use black markers.
15. **Custom tooltip system** — uses Plotly scene annotations with a caret/triangle pointing at the marker. Native Plotly hover is disabled.
16. **Linked selection** — clicking a table row highlights the marker on the plot, clicking a marker highlights the table row. Uses annotation text box above the highlighted marker.
17. **"Common Materials Only" toggle** — filters to ~90 well-known lab solvents and common polymers. Non-common markers are hidden by setting size to 0.
18. **Natural language search** — queries like "good solvents for polystyrene" are parsed client-side into structured operations (find target material, compute distances, rank).
19. **Result count selector** (10/25/50) below the search bar.
20. **Delete confirmation text**: "Are you sure?" (not longer messages).
21. **3D plot**: cube aspect ratio for equal visual axis lengths. No spike lines on hover. Middle-mouse drag = pan (not zoom). Camera position preserved across updates.

### Data Preferences
22. **Deduplication across sources** — when the same chemical appears in multiple datasets, merge intelligently. Track which datasets each entry comes from.
23. **Confidence scoring** — rate data quality based on source reliability and field completeness.
24. **CAS numbers are critical** — extensive work on CAS enrichment via PubChem, manual CAS review tool, crosslink badges for missing CAS.
25. **HSPiP database is the primary solvent source** (replaced earlier OCR data from Hansen Handbook with HSPiP software database values).
26. **Colors are baked at generation time** — per-category color maps for both solvents and polymers are defined in `generate_html.py` (CATEGORY_COLORS and POLYMER_CAT_COLORS dicts).

### Performance Requirements
27. **No plot freezing** — extensive work on debouncing, O(1) lookups, deferred DOM operations, and avoiding full Plotly re-renders. Use `Plotly.restyle` instead of `Plotly.react` where possible.
28. **Incremental updates** — search results update via `addTraces`/`deleteTraces`, not full re-render.
29. **Typed arrays and quickselect** for search ranking performance.

### What NOT to Do
30. Do not add a server dependency for the main app pages.
31. Do not use `Plotly.react` for marker updates — use `Plotly.restyle` to avoid camera resets and performance issues.
32. Do not add columns to the search page results table without asking — previous additions (abbreviation, industry uses, confidence, source) were all later removed.
33. Do not disable the custom tooltip system in favor of native Plotly hover.
34. Do not change the color scheme (#e94560 brand red, light mode).

---

## File Map (Key Files)

```
generate_html.py          ← THE main file. Generates materialism.html + database.html
build_unified.py          ← Merges all datasets into unified CSVs
materialism.html          ← Generated search page (the product)
database.html             ← Generated database management page
materialism.db            ← SQLite database (seeded from unified CSVs)
data/manifest.json        ← Dataset registry (which datasets exist, metadata)
data/processed/unified_chemicals.csv  ← 1,630 merged chemicals
data/processed/unified_polymers.csv   ← 471 merged polymers
data/datasets/*/          ← Per-dataset directories with chemicals.csv/polymers.csv
backend/app/services/hsp_calculator.py  ← All HSP math
backend/tests/test_hsp_calculator.py    ← Tests for HSP math
lib/classify.py           ← Chemical/polymer categorization
lib/merge.py              ← Deduplication logic
lib/confidence.py         ← Confidence scoring
lib/normalize.py          ← Name/CAS normalization
PLANNING.md               ← Original 6-phase build plan
```

---

## Workflow for Making Changes

1. Edit `generate_html.py` (for search page or database page changes)
2. Run `python generate_html.py` to regenerate the HTML files
3. Open `materialism.html` or `database.html` in a browser to test
4. Commit and push — GitHub Actions deploys to Pages automatically

For data pipeline changes:
1. Edit files in `lib/` or `scripts/` or `data/datasets/`
2. Run `python build_unified.py` to rebuild unified CSVs
3. Run `python generate_html.py` to regenerate HTML
4. Test in browser

For HSP math changes:
1. Edit `backend/app/services/hsp_calculator.py`
2. Run `pytest backend/tests/test_hsp_calculator.py -v` to verify
