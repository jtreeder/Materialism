# Materialism: Hansen Solubility Parameter Software — Build Plan

## What We're Building

A web-based alternative to [HSPiP](https://www.hansen-solubility.com/HSPiP/) ($1,195 commercial software) for computing, visualizing, and optimizing Hansen Solubility Parameters. The tool helps predict whether materials are compatible — will a solvent dissolve a polymer? Will a coating adhere to a surface? Will nanoparticles disperse properly?

### Core Science (3 numbers that predict compatibility)

Every material gets three values measured in MPa½:
- **δD** — Dispersion forces (van der Waals)
- **δP** — Polar forces (dipole-dipole)
- **δH** — Hydrogen bonding forces

Compatibility is predicted by the **HSP Distance**:

```
Ra² = 4(δD₁ - δD₂)² + (δP₁ - δP₂)² + (δH₁ - δH₂)²
```

If `Ra < R₀` (the solubility sphere radius), the materials are compatible. The ratio `RED = Ra / R₀` quantifies this: RED < 1 = compatible, RED > 1 = incompatible.

---

## Recommended Tech Stack

### Backend: Python + FastAPI
- **Why**: Scientific computing ecosystem (NumPy, SciPy, pandas), async support, auto-generated API docs
- **Database**: PostgreSQL with pgvector extension (enables nearest-neighbor queries in 3D HSP space — critical for "find me similar solvents" queries across 10k+ records)
- **ORM**: SQLAlchemy 2.0 with async support

### Frontend: React + TypeScript + Plotly.js
- **Why**: Plotly.js has native 3D scatter/surface/mesh rendering with WebGL (handles 10k+ points), interactive rotation, and hover tooltips
- **UI framework**: Tailwind CSS + shadcn/ui for rapid component development
- **State management**: Zustand (lightweight, good for scientific apps)

### Data Layer
- **Large tables**: PostgreSQL for persistent storage, Redis for caching frequently-accessed datasets
- **Search**: Full-text search on chemical names/CAS numbers via PostgreSQL `tsvector`
- **Import/Export**: CSV, XLSX, JSON, HSD/HSDX format support

### Alternative: Streamlit or Dash (Simpler but Limited)
If speed-to-prototype matters more than long-term UX:
- **Plotly Dash** gives you Python-only full-stack with native Plotly integration
- **Streamlit** is fastest to prototype but re-runs entire app on every interaction (bad for large datasets)
- **Tradeoff**: These limit your UI customization and scale poorly for multi-user deployment

**Recommendation**: Start with **Dash** for rapid prototyping phases 1-3, then migrate to React+FastAPI if you need a polished multi-user product.

---

## Data Strategy

### Available Open-Source HSP Data

| Source | Records | Fields | Access |
|--------|---------|--------|--------|
| [Mendeley Solvent Dataset](https://data.mendeley.com/datasets/b4dmjzk8w6/1) | ~500 solvents | HSP, boiling point, vapor pressure, density, MW, molar volume, GHS, cost, CAS, SMILES | Free download |
| [Wolfram Data Repository](https://datarepository.wolframcloud.com/resources/JoshuaSchrier_Hansen-Solubility-Parameters/) | 211 solvents | δD, δP, δH | Free |
| [HSPiP Preview Dataset](https://hansen-solubility.com/HSPiP/datasets.php) | 11,200 names | Chemical name + CAS only (no HSP values) | Free XLS |
| [HSPiPy Library](https://github.com/Gnpd/HSPiPy) | Varies | Reads CSV/HSD/HSDX, includes sample data | MIT License |
| Published literature | 1,200+ | The "standard Hansen set" values are widely published in textbooks and papers | Public domain (pre-1990 data) |

### Building a 10k+ Chemical Database

The full 10k+ dataset must be constructed, not downloaded. Strategy:

1. **Seed with open data** — Start with the Mendeley 500 + Wolfram 211 + literature values (~1,200 standard set)
2. **HSP estimation engine** — Implement group contribution methods (Van Krevelen, Hoftyzer) to estimate HSP from molecular structure (SMILES → functional groups → HSP). This is how HSPiP gets its 10k estimates.
3. **PubChem/ChemSpider API integration** — Pull molecular properties (MW, density, boiling point) for any CAS number
4. **User-contributed data** — Allow users to upload experimental HSP data and share datasets
5. **RDKit integration** — Open-source cheminformatics library for parsing SMILES, computing molecular descriptors, identifying functional groups

### Database Schema (Core Tables)

```
chemicals
├── id, name, cas_number, smiles, molecular_formula
├── molecular_weight, density, boiling_point, molar_volume
├── delta_d, delta_p, delta_h  (the HSP values)
├── data_source (measured/estimated/user)
├── confidence_score
└── created_at, updated_at

polymers
├── id, name, trade_name, type
├── delta_d, delta_p, delta_h
├── radius_r0  (solubility sphere radius)
└── data_source

solubility_tests
├── id, solvent_id, material_id
├── score (1-6 scale or binary)
├── temperature, notes
└── user_id

mixtures
├── id, name
├── components[] (solvent_id, volume_fraction)
├── calculated_delta_d, _p, _h
└── notes
```

---

## Build Phases (Vibecoding Sequence)

### Phase 1: Data Foundation
**Goal**: Get a searchable chemical database running with HSP values.

- [ ] Set up project scaffolding (Python package, database, config)
- [ ] Ingest Mendeley + Wolfram open datasets into PostgreSQL
- [ ] Build chemical search API (by name, CAS number, SMILES)
- [ ] Implement basic CRUD for chemicals, polymers, and user data
- [ ] Add CSV/XLSX import and export endpoints

**Vibecoding approach**: Have Claude generate the SQLAlchemy models, FastAPI routes, and data ingestion scripts. The schema is well-defined, making this highly automatable.

### Phase 2: Core HSP Calculations
**Goal**: Compute distances, find compatible solvents, rank results.

- [ ] HSP distance calculator (Ra² formula)
- [ ] RED (Relative Energy Difference) computation
- [ ] Nearest-neighbor solvent search ("find the 20 closest solvents to this polymer")
- [ ] Solubility sphere fitting from experimental data (optimization problem — given a set of good/bad solvents, find the center δD/δP/δH and radius R₀ that best separates them)
- [ ] Mixture HSP calculator (volume-weighted or activity-coefficient-weighted blending)

**Vibecoding approach**: The math is well-documented. Feed Claude the formulas and have it generate NumPy/SciPy implementations. The sphere fitting is a constrained optimization — use `scipy.optimize.minimize` or similar.

### Phase 3: 3D Visualization
**Goal**: Interactive Hansen space plots — the signature feature.

- [ ] 3D scatter plot of solvents in (δD, δP, δH) space with Plotly
- [ ] Solubility sphere rendering (transparent sphere overlay)
- [ ] Color-coding by compatibility score (RED value gradient)
- [ ] Hover tooltips showing chemical name, CAS, exact HSP values
- [ ] 2D projection views (δD vs δP, δD vs δH, δP vs δH)
- [ ] Click-to-select chemicals and add them to mixtures

**Vibecoding approach**: Plotly's `scatter3d` and `mesh3d` traces handle this directly. Generate sphere meshes parametrically. WebGL handles 10k points natively.

### Phase 4: Solvent Optimizer
**Goal**: "I need to dissolve polymer X — what solvent blend should I use?"

- [ ] Single-solvent ranking by RED score
- [ ] Multi-solvent blend optimization (2-8 components)
- [ ] Constraints: cost, toxicity (GHS), boiling point range, evaporation rate
- [ ] Pareto frontier visualization (cost vs. performance tradeoff)

**Vibecoding approach**: This is a constrained optimization problem. Use SciPy's `minimize` with bounds and constraints, or a genetic algorithm for the multi-objective version.

### Phase 5: HSP Estimation Engine
**Goal**: Predict HSP for any chemical from its structure — this is how you get to 10k+.

- [ ] SMILES parser using RDKit
- [ ] Group contribution method (Van Krevelen / Hoftyzer)
- [ ] Y-MB method (Yamamoto Molecular Breaking)
- [ ] Comparison/validation against known values
- [ ] Confidence scoring for estimates

**Vibecoding approach**: Group contribution methods are table-driven — you need a table of functional group contributions and code to decompose molecules into groups. RDKit handles the molecular decomposition. Have Claude generate the group contribution tables from published literature.

### Phase 6: Advanced Features (Post-MVP)
- [ ] Temperature-dependent HSP modeling
- [ ] Polymer property calculator (Tg, solubility from structure)
- [ ] Diffusion modeling
- [ ] QSAR fitting module
- [ ] User accounts and shared datasets
- [ ] Evaporation rate modeling for solvent blends
- [ ] PDF report generation

---

## Key Architecture Decisions

### Why PostgreSQL + pgvector over SQLite
With 10k+ chemicals each represented as a 3D point (δD, δP, δH), nearest-neighbor queries are the core operation. `pgvector` provides indexed approximate nearest-neighbor search that's orders of magnitude faster than scanning all rows. A query like "find the 50 solvents closest to this point in Hansen space" runs in milliseconds instead of seconds.

### Why Not Just Use HSPiPy?
[HSPiPy](https://github.com/Gnpd/HSPiPy) (MIT license) is useful for sphere fitting but:
- It's a library, not an application — no UI, no database, no optimization
- Limited to matplotlib (no interactive 3D in-browser)
- No mixture optimization or solvent selection
- We can use it as a reference or even wrap parts of it, but it doesn't replace what we're building

### Data Validation Strategy
HSP values have known physical ranges:
- δD: typically 12–22 MPa½ (most organics)
- δP: 0–20 MPa½
- δH: 0–25 MPa½
- Water is an outlier: δD=15.5, δP=16.0, δH=42.3

Any estimated or imported values outside these ranges should be flagged for review.

---

## Vibecoding Tips for This Project

1. **Start with the data, not the UI**. Get your database populated and your calculation engine working in Jupyter notebooks or CLI scripts first. Visualization is meaningless without correct underlying math.

2. **Validate against known results**. HSPiP and published papers have well-known results for common systems (e.g., PLA solubility sphere, toluene-acetone-ethanol mixtures). Use these as test cases.

3. **The 3D plot is the hero feature**. When you do build the UI, the interactive 3D Hansen space visualization is what differentiates this from a spreadsheet. Invest time in making it smooth and informative.

4. **Group contribution tables are the bottleneck**. The estimation engine (Phase 5) requires carefully transcribed tables of functional group contributions from published sources. This is tedious but essential for scaling beyond the ~1,200 measured chemicals.

5. **Prompt Claude with the math**. The formulas for HSP distance, sphere fitting, and mixture calculations are well-defined. Include the exact equations in your prompts and ask for NumPy implementations with unit tests.

6. **Leverage RDKit heavily**. Don't reinvent molecular structure parsing. RDKit is battle-tested for SMILES parsing, substructure search, and molecular descriptor calculation.

---

## File Structure (Proposed)

```
Materialism/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry
│   │   ├── models/              # SQLAlchemy models
│   │   ├── routes/              # API endpoints
│   │   ├── services/            # Business logic
│   │   │   ├── hsp_calculator.py    # Distance, RED, mixtures
│   │   │   ├── sphere_fitter.py     # Optimization for sphere fitting
│   │   │   ├── solvent_optimizer.py # Blend optimization
│   │   │   └── estimator.py         # Group contribution HSP estimation
│   │   ├── data/                # Data ingestion scripts
│   │   └── db/                  # Database config, migrations
│   ├── tests/
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── HansenPlot3D.tsx     # The 3D visualization
│   │   │   ├── SolventTable.tsx     # Searchable data table
│   │   │   ├── MixtureBuilder.tsx   # Drag-and-drop blend builder
│   │   │   └── OptimizerPanel.tsx   # Solvent optimization UI
│   │   ├── hooks/
│   │   ├── services/            # API client
│   │   └── types/
│   ├── package.json
│   └── tsconfig.json
├── data/
│   ├── raw/                     # Downloaded datasets
│   ├── processed/               # Cleaned, merged data
│   └── group_contributions/     # Functional group tables
├── notebooks/                   # Jupyter notebooks for prototyping
├── PLANNING.md
└── README.md
```

---

## What the User Modifications Might Include

Since you mentioned "with some modifications," common reasons people build HSPiP alternatives:

- **Domain-specific focus** — e.g., only cannabis extraction solvents, only pharmaceutical excipients, only 3D printing materials
- **Better UX** — HSPiP has a dated Windows-only desktop UI; a modern web app is more accessible
- **Custom scoring** — Weighting HSP distance with cost, toxicity, availability, or regulatory compliance
- **Integration** — Connecting to internal material databases, ERP systems, or lab equipment
- **Collaboration** — Multi-user shared datasets and experiments (HSPiP is single-user)
- **Open data** — Building on open datasets rather than being locked into a proprietary database

Clarify your specific modifications early — they may change which phases to prioritize.
