"""Generate a standalone interactive HTML file with the full HSP visualization."""

import os
import sys
import json
import csv

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import numpy as np

from backend.app.models.database import init_db, get_engine, get_session, Chemical, Polymer
from backend.app.data.seed_data import seed_database

DB_PATH = os.path.join(os.path.dirname(__file__), "materialism.db")
engine = init_db(get_engine(DB_PATH))
session = get_session(engine)
seed_database(session)

# Load data from CSV (has per-field source URLs after enrichment)
CHEM_CSV = os.path.join(os.path.dirname(__file__), "data", "processed", "hsp_chemicals.csv")
POLY_CSV = os.path.join(os.path.dirname(__file__), "data", "processed", "hsp_polymers.csv")

# Source display name mapping
SOURCE_NAMES = {
    "handbook": "Hansen Handbook 2007",
    "hansen_a1": "Hansen Handbook A.1",
    "hansen_a2": "Hansen Handbook A.2",
    "mendeley": "Mendeley (Langner 2022)",
    "pang2024": "Pang et al. 2024",
    "solvpred": "SolvPred (Fang)",
    "wolfram": "Wolfram Data Repo",
    "accudyne": "Accudyne Test",
}

# Common solvents: readily available lab/industrial solvents
# Identified by CAS number for precise matching
COMMON_SOLVENT_CAS = {
    "7732-18-5",   # Water
    "67-56-1",     # Methanol
    "64-17-5",     # Ethanol
    "67-63-0",     # 2-Propanol (isopropanol)
    "71-36-3",     # 1-Butanol
    "71-23-8",     # 1-Propanol
    "78-83-1",     # Isobutanol
    "75-65-0",     # tert-Butanol
    "111-87-5",    # 1-Octanol
    "111-27-3",    # 1-Hexanol
    "98-00-0",     # Furfuryl alcohol
    "107-21-1",    # Ethylene glycol
    "57-55-6",     # Propylene glycol
    "56-81-5",     # Glycerol
    "67-64-1",     # Acetone
    "78-93-3",     # Methyl ethyl ketone (MEK)
    "108-10-1",    # MIBK
    "591-78-6",    # 2-Hexanone
    "108-94-1",    # Cyclohexanone
    "108-88-3",    # Toluene
    "1330-20-7",   # Xylene (mixed)
    "100-41-4",    # Ethylbenzene
    "71-43-2",     # Benzene
    "110-82-7",    # Cyclohexane
    "110-54-3",    # n-Hexane
    "142-82-5",    # n-Heptane
    "111-65-9",    # n-Octane
    "109-66-0",    # n-Pentane
    "75-09-2",     # Dichloromethane (DCM)
    "67-66-3",     # Chloroform
    "56-23-5",     # Carbon tetrachloride
    "71-55-6",     # 1,1,1-Trichloroethane
    "79-01-6",     # Trichloroethylene
    "127-18-4",    # Tetrachloroethylene (PERC)
    "107-06-2",    # 1,2-Dichloroethane
    "141-78-6",    # Ethyl acetate
    "123-86-4",    # Butyl acetate
    "108-21-4",    # Isopropyl acetate
    "79-20-9",     # Methyl acetate
    "109-60-4",    # Propyl acetate
    "68-12-2",     # DMF
    "67-68-5",     # DMSO
    "872-50-4",    # NMP (1-Methyl-2-pyrrolidinone)
    "127-19-5",    # DMAc
    "109-99-9",    # THF
    "60-29-7",     # Diethyl ether
    "1634-04-4",   # MTBE
    "75-05-8",     # Acetonitrile
    "110-86-1",    # Pyridine
    "68-12-2",     # N,N-Dimethylformamide
    "64-19-7",     # Acetic acid
    "88-99-3",     # Formic acid
    "75-07-0",     # Acetaldehyde
    "108-95-2",    # Phenol
    "91-22-5",     # Quinoline
    "110-91-8",    # Morpholine
    "109-89-7",    # Diethylamine
    "75-50-3",     # Trimethylamine
    "100-42-5",    # Styrene
    "75-15-0",     # Carbon disulfide
    "108-90-7",    # Chlorobenzene
    "95-50-1",     # 1,2-Dichlorobenzene
    "98-95-3",     # Nitrobenzene
    "98-86-2",     # Acetophenone
    "100-66-3",    # Anisole
    "100-51-6",    # Benzyl alcohol
    "98-01-1",     # Furfural
    "96-48-0",     # gamma-Butyrolactone
    "120-92-3",    # Cyclopentanone
    "78-92-2",     # 2-Butanol
    "108-32-7",    # Propylene carbonate
    "96-49-1",     # Ethylene carbonate
    "110-80-5",    # 2-Ethoxyethanol
    "111-76-2",    # 2-Butoxyethanol
    "109-86-4",    # 2-Methoxyethanol
    "112-07-2",    # 2-Butoxyethyl acetate
    "110-49-6",    # 2-Methoxyethyl acetate
    "111-15-9",    # 2-Ethoxyethyl acetate
    "112-34-5",    # Diethylene glycol monobutyl ether
    "111-90-0",    # Diethylene glycol monoethyl ether
    "64-18-6",     # Formic acid
    "124-38-9",    # Carbon dioxide (supercritical)
    "78-70-6",     # Linalool
    "5989-27-5",   # d-Limonene
    "8052-41-3",   # Stoddard solvent / mineral spirits
    "64742-88-7",  # Mineral spirits
    "7664-41-7",   # Ammonia
    "302-01-2",    # Hydrazine
}

# Common solvents also identified by name (for entries without CAS)
COMMON_SOLVENT_NAMES = {n.lower() for n in [
    "water", "methanol", "ethanol", "isopropanol", "2-propanol", "acetone",
    "toluene", "xylene", "hexane", "heptane", "benzene", "cyclohexane",
    "dichloromethane", "chloroform", "ethyl acetate", "butyl acetate",
    "thf", "tetrahydrofuran", "diethyl ether", "acetonitrile", "dmf",
    "dmso", "nmp", "pyridine", "acetic acid", "methyl ethyl ketone",
    "mek", "mibk", "chlorobenzene", "carbon tetrachloride", "pentane",
    "octane", "phenol", "nitrobenzene", "carbon disulfide", "glycerol",
    "ethylene glycol", "propylene glycol", "formic acid", "styrene",
    "cyclohexanone", "furfural", "morpholine", "aniline", "benzyl alcohol",
    "anisole", "d-limonene", "mineral spirits", "turpentine",
    "1-butanol", "2-butanol", "1-propanol", "1-hexanol", "1-octanol",
    "acetophenone", "propylene carbonate", "gamma-butyrolactone",
    "2-butoxyethanol", "2-ethoxyethanol", "2-methoxyethanol",
    "trichloroethylene", "tetrachloroethylene",
]}

# Common polymers identified by name patterns
COMMON_POLYMER_NAMES = {n.lower() for n in [
    "polystyrene", "polyethylene", "polypropylene", "pvc",
    "poly(vinyl chloride)", "pmma", "poly(methyl methacrylate)",
    "nylon 6,6", "nylon", "polyamide", "polyester", "pet",
    "poly(ethylene terephthalate)", "polyurethane", "polycarbonate",
    "epoxy", "silicone", "polybutadiene", "abs",
    "poly(vinyl acetate)", "pvac", "pvdf",
    "poly(vinylidene fluoride)", "ptfe", "teflon", "polytetrafluoroethylene",
    "cellulose acetate", "cellulose nitrate", "nitrocellulose",
    "polyisoprene", "natural rubber", "sbr", "neoprene",
    "poly(vinyl alcohol)", "pva", "polyacetal", "polyimide",
    "polysulfone", "peek", "pei", "pps", "pbt",
    "poly(ethylene oxide)", "peo", "polylactic acid", "pla",
    "acrylic", "alkyd", "shellac", "polyvinyl butyral",
    "chlorinated rubber", "poly(vinyl butyral)", "phenolic",
    "phenol formaldehyde", "urea formaldehyde", "melamine formaldehyde",
    "poly(dimethyl siloxane)", "pdms",
]}


def _is_common_solvent(name, cas):
    """Check if a solvent is in the common materials list."""
    if cas and cas in COMMON_SOLVENT_CAS:
        return True
    if name and name.lower() in COMMON_SOLVENT_NAMES:
        return True
    return False


def _is_common_polymer(name):
    """Check if a polymer is in the common materials list."""
    nl = name.lower()
    if nl in COMMON_POLYMER_NAMES:
        return True
    # Also match partial names like "polystyrene (gp)" or "nylon 6"
    for cn in COMMON_POLYMER_NAMES:
        if cn in nl or nl in cn:
            return True
    return False


solvents = []
with open(CHEM_CSV) as f:
    for row in csv.DictReader(f):
        dd = row.get("delta_d", "").strip()
        dp = row.get("delta_p", "").strip()
        dh = row.get("delta_h", "").strip()
        if not (dd and dp and dh):
            continue
        src_key = row.get("source", "").strip()
        src_url = row.get("source_url", "").strip()
        mw_src = row.get("mw_source", "").strip() or src_url
        bp_src = row.get("bp_source", "").strip() or src_url
        mw_val = row.get("molecular_weight", "").strip()
        bp_val = row.get("boiling_point", "").strip()
        if row.get("hidden", "").strip().lower() in ("1", "true", "yes"):
            continue
        chem_name = row["name"].strip()
        chem_cas = row.get("cas_number", "").strip()
        solvents.append({
            "name": chem_name,
            "cas": chem_cas,
            "dd": float(dd), "dp": float(dp), "dh": float(dh),
            "mw": float(mw_val) if mw_val else None,
            "bp": float(bp_val) if bp_val else None,
            "cat": row.get("category", "other").strip() or "other",
            "smiles": row.get("smiles", "").strip(),
            "src": SOURCE_NAMES.get(src_key, src_key),
            "srcUrl": src_url,
            "mwSrc": mw_src if mw_val else "",
            "bpSrc": bp_src if bp_val else "",
            "common": _is_common_solvent(chem_name, chem_cas),
        })

poly_data = []
with open(POLY_CSV) as f:
    for row in csv.DictReader(f):
        dd = row.get("delta_d", "").strip()
        dp = row.get("delta_p", "").strip()
        dh = row.get("delta_h", "").strip()
        if not (dd and dp and dh):
            continue
        src_key = row.get("source", "").strip()
        src_url = row.get("source_url", "").strip()
        r_val = row.get("radius", "").strip()
        if row.get("hidden", "").strip().lower() in ("1", "true", "yes"):
            continue
        poly_name = row["name"].strip()
        poly_data.append({
            "name": poly_name,
            "dd": float(dd), "dp": float(dp), "dh": float(dh),
            "r": float(r_val) if r_val else None,
            "type": row.get("type", "").strip(),
            "cas": row.get("cas_number", "").strip(),
            "src": SOURCE_NAMES.get(src_key, src_key),
            "srcUrl": src_url,
            "common": _is_common_polymer(poly_name),
        })

CATEGORY_COLORS = {
    "hydrocarbon": "#636EFA", "aromatic": "#EF553B", "halogenated": "#00CC96",
    "ether": "#AB63FA", "ketone": "#FFA15A", "ester": "#19D3F3",
    "alcohol": "#FF6692", "amide": "#B6E880", "sulfoxide": "#FF97FF",
    "acid": "#FECB52", "nitrile": "#1F77B4", "glycol ether": "#2CA02C",
    "amine": "#D62728", "terpene": "#9467BD", "inorganic": "#8C564B",
    "nitro": "#E377C2", "glycol": "#7F7F7F", "fluorinated": "#BCBD22",
    "heterocyclic": "#17BECF",
    "aldehyde": "#FF7F0E", "sulfur compound": "#AEC7E8", "other": "#888888",
}

# Serialize data for JS embedding
solvents_json = json.dumps(solvents)
polymers_json = json.dumps(poly_data)
cat_colors_json = json.dumps(CATEGORY_COLORS)

# Embed Plotly.js inline so the file works offline / from file://
import plotly as _plotly_pkg
_plotly_js_path = os.path.join(os.path.dirname(_plotly_pkg.__file__), "package_data", "plotly.min.js")
with open(_plotly_js_path) as _f:
    plotly_js_inline = _f.read()

# Generate full HTML
full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Materialism — Hansen Solubility Parameters</title>
    <script>{plotly_js_inline}</script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: #f5f6fa; color: #2d3436; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
        .header {{ background: #fff; padding: 15px 30px; display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #dfe6e9; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
        .header h1 {{ font-size: 1.5rem; color: #e94560; cursor: pointer; }}
        .header .stats {{ color: #636e72; font-size: 0.9rem; }}
        .tabs {{ display: flex; gap: 0; background: #fff; border-bottom: 2px solid #dfe6e9; }}
        .tab {{ padding: 12px 24px; cursor: pointer; border: none; background: transparent; color: #636e72; font-size: 0.95rem; transition: all 0.2s; }}
        .tab:hover {{ color: #2d3436; background: #f5f6fa; }}
        .tab.active {{ color: #e94560; border-bottom: 2px solid #e94560; background: #f5f6fa; }}
        .panel {{ display: none; padding: 20px; }}
        .panel.active {{ display: block; }}
        .results-layout {{ display: flex; gap: 0; height: calc(100vh - 140px); min-height: 500px; }}
        .plot-side {{ flex: 1 1 55%; min-width: 0; border-right: 1px solid #dfe6e9; overflow: hidden; background: #fff; display: flex; flex-direction: column; }}
        .plot-container {{ width: 100%; flex: 1; min-height: 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.85rem; }}
        th {{ background: #f0f2f5; color: #e94560; padding: 10px; text-align: left; position: sticky; top: 0; cursor: pointer; z-index: 1; border-bottom: 2px solid #dfe6e9; }}
        th:hover {{ background: #e8eaed; }}
        td {{ padding: 8px 10px; border-bottom: 1px solid #eee; color: #2d3436; }}
        tr:hover {{ background: #f8f9fa; }}
        .table-wrapper {{ max-height: 500px; overflow-y: auto; border: 1px solid #dfe6e9; border-radius: 4px; }}
        input[type="text"] {{ background: #fff; border: 1px solid #dfe6e9; color: #2d3436; padding: 8px 12px; border-radius: 4px; width: 300px; margin: 10px 0; }}
        input[type="text"]:focus {{ outline: none; border-color: #e94560; }}
        .info {{ background: #fff; padding: 20px; border-radius: 8px; margin: 10px 0; line-height: 1.7; border: 1px solid #eee; }}
        .info h3 {{ color: #e94560; margin-bottom: 10px; }}
        .info code {{ background: #f0f2f5; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; color: #2d3436; }}
        .compatible {{ color: #00b894; font-weight: bold; }}
        .incompatible {{ color: #d63031; }}

        /* --- Chat / Search UI --- */
        .search-bar {{
            display: flex; align-items: center; gap: 10px; padding: 16px 20px;
            background: #fff; border-bottom: 1px solid #dfe6e9;
        }}
        .search-bar input {{
            flex: 1; max-width: 700px; padding: 12px 18px; font-size: 1rem;
            background: #f5f6fa; border: 2px solid #dfe6e9; color: #2d3436;
            border-radius: 8px; outline: none; transition: border-color 0.2s;
        }}
        .search-bar input:focus {{ border-color: #e94560; }}
        .search-bar input::placeholder {{ color: #b2bec3; }}
        .search-bar button {{
            padding: 12px 24px; font-size: 1rem; background: #e94560; color: white;
            border: none; border-radius: 8px; cursor: pointer; font-weight: 600;
            transition: background 0.2s;
        }}
        .search-bar button:hover {{ background: #c73652; }}
        .simple-toggle {{
            display: flex; align-items: center; gap: 8px; cursor: pointer;
            user-select: none; white-space: nowrap;
        }}
        .simple-toggle input {{ display: none; }}
        .simple-slider {{
            position: relative; width: 36px; height: 20px; background: #dfe6e9;
            border-radius: 10px; transition: background 0.2s;
        }}
        .simple-slider::after {{
            content: ''; position: absolute; top: 2px; left: 2px;
            width: 16px; height: 16px; background: #fff; border-radius: 50%;
            transition: transform 0.2s;
        }}
        .simple-toggle input:checked + .simple-slider {{ background: #e94560; }}
        .simple-toggle input:checked + .simple-slider::after {{ transform: translateX(16px); }}
        .simple-label {{ font-size: 0.85rem; color: #636e72; font-weight: 600; }}
        .simple-toggle input:checked ~ .simple-label {{ color: #e94560; }}
        .search-options {{
            display: flex; align-items: center; justify-content: space-between;
            padding: 4px 20px 10px; background: #fff;
            border-bottom: 2px solid #dfe6e9;
        }}
        .search-examples {{
            font-size: 0.8rem; color: #636e72;
        }}
        .search-examples span {{
            cursor: pointer; color: #74b9ff; margin-right: 14px;
            transition: color 0.2s;
        }}
        .search-examples span:hover {{ color: #e94560; }}
        .result-count-selector {{
            font-size: 0.8rem; color: #636e72; display: flex; align-items: center; gap: 4px;
            white-space: nowrap;
        }}
        .rc-btn {{
            background: #f5f6fa; border: 1px solid #dfe6e9; color: #636e72;
            padding: 3px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8rem;
            transition: all 0.2s;
        }}
        .rc-btn:hover {{ border-color: #e94560; color: #2d3436; }}
        .rc-btn.active {{ background: #e94560; color: white; border-color: #e94560; }}

        /* --- Chat Panel (right side of results layout) --- */
        .chat-panel {{
            display: none; flex: 1 1 45%; min-width: 0;
            overflow-y: auto; padding: 12px 14px;
            height: calc(100vh - 140px); box-sizing: border-box;
            background: #fff;
        }}
        .chat-panel.visible {{ display: block; }}

        /* --- Home Panel (right side, shown when no search results) --- */
        .home-panel {{
            flex: 1 1 45%; min-width: 0; display: flex; flex-direction: column;
            height: calc(100vh - 140px); box-sizing: border-box;
            background: #fff;
        }}
        .home-panel-header {{
            display: flex; align-items: center; padding: 10px 14px;
            border-bottom: 1px solid #dfe6e9; flex-shrink: 0;
        }}
        .home-tabs {{
            display: flex; gap: 0; border-bottom: 1px solid #dfe6e9; flex-shrink: 0;
        }}
        .home-tab {{
            padding: 8px 18px; cursor: pointer; border: none; background: transparent;
            color: #636e72; font-size: 0.85rem; transition: all 0.2s;
        }}
        .home-tab:hover {{ color: #2d3436; background: #f5f6fa; }}
        .home-tab.active {{ color: #e94560; border-bottom: 2px solid #e94560; background: #fff; }}
        .home-table-wrap {{ flex: 1; overflow-y: auto; min-height: 0; }}

        /* --- Column Lock Button --- */
        .col-lock-btn {{
            margin-left: auto; cursor: pointer; background: none; border: 1px solid #dfe6e9;
            border-radius: 4px; padding: 3px 7px; display: flex; align-items: center; gap: 4px;
            color: #636e72; font-size: 0.75rem; transition: all 0.2s;
        }}
        .col-lock-btn:hover {{ background: #f5f6fa; border-color: #b2bec3; }}
        .col-lock-btn.locked {{ color: #e94560; border-color: #e94560; }}
        .col-lock-btn svg {{ width: 14px; height: 14px; fill: currentColor; }}

        .chat-context {{
            display: inline-block; background: #f0f2f5; color: #636e72; padding: 2px 8px;
            border-radius: 4px; font-size: 0.75rem; margin-bottom: 8px;
        }}

        /* --- Results Table --- */
        .results-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 8px; table-layout: fixed; }}
        .results-table th {{
            background: #f0f2f5; color: #e94560; padding: 8px 10px;
            text-align: left; font-weight: 600; position: sticky; top: 0; z-index: 1; border-bottom: 2px solid #dfe6e9;
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }}
        .results-table td {{ padding: 8px 10px; border-bottom: 1px solid #eee; position: relative; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .results-table tr:hover {{ background: #f8f9fa; }}
        .results-table .rank {{ color: #e94560; font-weight: bold; }}
        .red-good {{ color: #00b894; font-weight: bold; }}
        .red-boundary {{ color: #e17055; font-weight: bold; }}
        .red-bad {{ color: #d63031; font-weight: bold; }}
        .target-chip {{
            display: inline-block; background: #e94560; color: white; padding: 2px 10px;
            border-radius: 12px; font-size: 0.8rem; font-weight: 600; margin-left: 8px;
        }}

        /* --- Structure Tooltip --- */
        .struct-tooltip {{
            display: none; position: fixed; z-index: 9999;
            background: #fff; border: 2px solid #e94560; border-radius: 8px;
            padding: 4px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            pointer-events: none;
        }}
        .struct-tooltip img {{
            display: block; width: 200px; height: 200px; border-radius: 4px;
        }}
        .struct-tooltip .struct-name {{
            text-align: center; font-size: 0.7rem; color: #333; padding: 2px 4px;
            max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }}
        .struct-tooltip.loading img {{ opacity: 0.3; }}
        .struct-tooltip.error {{ display: none; }}
        .hoverable-name {{ cursor: help; border-bottom: 1px dotted #b2bec3; }}
        th.sort-asc::after {{ content: ' ▲'; font-size: 0.7em; color: #e94560; }}
        th.sort-desc::after {{ content: ' ▼'; font-size: 0.7em; color: #e94560; }}
    </style>
</head>
<body>
    <div class="header">
        <h1 onclick="goHome()">Materialism</h1>
        <div class="stats"><a href="database.html" style="color:#636e72;text-decoration:none;border-bottom:1px dotted #b2bec3;cursor:pointer">Database</a></div>
    </div>

    <div class="search-bar">
        <input type="text" id="nl-search" placeholder="Ask anything — e.g. &quot;good solvents for polystyrene&quot;"
               onkeydown="if(event.key==='Enter')runSearch()">
        <button onclick="runSearch()">Search</button>
        <label class="simple-toggle" title="When enabled, show only common, readily accessible solvents and polymers">
            <input type="checkbox" id="simple-mode" onchange="onSimpleModeChange()">
            <span class="simple-slider"></span>
            <span class="simple-label">Common Materials Only</span>
        </label>
    </div>
    <div class="search-options">
        <div class="search-examples">
            Try:
            <span onclick="exampleSearch('good solvents for polystyrene')">good solvents for polystyrene</span>
            <span onclick="exampleSearch('bad solvents for PVC')">bad solvents for PVC</span>
            <span onclick="exampleSearch('solvents similar to toluene')">solvents similar to toluene</span>
            <span onclick="exampleSearch('what dissolves nylon')">what dissolves nylon</span>
            <span onclick="exampleSearch('polymers similar to epoxy')">polymers similar to epoxy</span>
            <span onclick="exampleSearch('good solvent for both cellulose acetate and PVC')">good for cellulose acetate AND PVC</span>
            <span onclick="exampleSearch('good for silicone, bad for epoxy')">good for silicone, bad for epoxy</span>
        </div>
        <div class="result-count-selector">
            Results:
            <button class="rc-btn" onclick="setResultCount(10)">10</button>
            <button class="rc-btn active" onclick="setResultCount(25)">25</button>
            <button class="rc-btn" onclick="setResultCount(50)">50</button>
        </div>
    </div>

    <div id="results-layout" class="results-layout">
        <div id="panel-plot" class="plot-side">
            <div class="plot-container">
                <div id="plotly-div" style="width:100%; height:100%;"></div>
            </div>
            <p style="color:#636e72; padding:6px 10px; font-size:0.8rem; margin:0;">
                Drag to rotate &middot; Scroll to zoom &middot; Gold diamonds = polymers, colored dots = solvents by category
            </p>
        </div>
        <div id="chat-panel" class="chat-panel"></div>
        <div id="home-panel" class="home-panel">
            <div class="home-panel-header">
                <input type="text" id="home-filter" placeholder="Filter by name..." oninput="filterHomeTable(this.value)" style="width:180px;font-size:0.8rem;">
                <button id="col-lock-btn" class="col-lock-btn" onclick="toggleColumnLock()" title="Lock column widths">
                    <svg id="lock-icon-unlocked" viewBox="0 0 24 24"><path d="M12 17a2 2 0 0 0 2-2 2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2m6-9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2h9V6a3 3 0 0 0-3-3 3 3 0 0 0-3 3H7a5 5 0 0 1 5-5 5 5 0 0 1 5 5v2h1z"/></svg>
                    <svg id="lock-icon-locked" viewBox="0 0 24 24" style="display:none"><path d="M12 17a2 2 0 0 0 2-2 2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2m6-9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2h1V6a5 5 0 0 1 5-5 5 5 0 0 1 5 5v2h1m-6-5a3 3 0 0 0-3 3v2h6V6a3 3 0 0 0-3-3z"/></svg>
                    <span id="lock-label">Widths</span>
                </button>
            </div>
            <div class="home-tabs">
                <button id="tab-solvents" class="home-tab active" onclick="switchHomeTab('solvents')">Solvents</button>
                <button id="tab-polymers" class="home-tab" onclick="switchHomeTab('polymers')">Polymers</button>
            </div>
            <div class="home-table-wrap">
                <table id="home-table" class="results-table">
                    <thead id="home-thead"></thead>
                    <tbody id="home-tbody"></tbody>
                </table>
            </div>
        </div>
    </div>


    <!-- Structure tooltip -->
    <div id="struct-tooltip" class="struct-tooltip">
        <img id="struct-img" src="" alt="Structure">
        <div id="struct-name" class="struct-name"></div>
    </div>

    <script>
        // ===================== DATA =====================
        const SOLVENTS = {solvents_json};
        const POLYMERS = {polymers_json};
        const CAT_COLORS = {cat_colors_json};

        // ===================== APPLY DATABASE EDITS =====================
        (function applyDbEdits() {{
            try {{
                var raw = localStorage.getItem('materialism_db_edits');
                if (!raw) return;
                var edits = JSON.parse(raw);
                for (var k in edits) {{
                    var parts = k.split(':');
                    var type = parts[0], idx = parseInt(parts[1]), field = parts[2];
                    var arr = type === 'solvents' ? SOLVENTS : POLYMERS;
                    if (!arr[idx]) continue;
                    var val = edits[k];
                    // Map database field names to materialism field names
                    if (field === 'dd') arr[idx].dd = parseFloat(val) || arr[idx].dd;
                    else if (field === 'dp') arr[idx].dp = parseFloat(val) || arr[idx].dp;
                    else if (field === 'dh') arr[idx].dh = parseFloat(val) || arr[idx].dh;
                    else if (field === 'mw') arr[idx].mw = parseFloat(val) || arr[idx].mw;
                    else if (field === 'bp') arr[idx].bp = parseFloat(val) || arr[idx].bp;
                    else if (field === 'name') arr[idx].name = val;
                    else if (field === 'cas') arr[idx].cas = val;
                    else if (field === 'cat') arr[idx].cat = val;
                    else if (field === 'r' && type === 'polymers') arr[idx].r = parseFloat(val) || arr[idx].r;
                    else if (field === 'type' && type === 'polymers') arr[idx].type = val;
                    else if (field === 'src') arr[idx].src = val;
                }}
            }} catch(e) {{}}
        }})();

        // ===================== COLUMN WIDTH LOCK =====================
        var columnWidthsLocked = false;
        // Default widths for each table context
        var DEFAULT_WIDTHS = {{
            solvents: ['25%','10%','48px','48px','48px','52px','52px','9%','11%'],
            polymers: ['25%','10%','48px','48px','48px','52px','9%','11%'],
            results:  ['35px','22%','10%','48px','48px','48px','52px','52px']
        }};
        // User-locked widths (saved to localStorage)
        var lockedWidths = {{ solvents: null, polymers: null, results: null }};

        function loadLockedWidths() {{
            try {{
                var saved = localStorage.getItem('materialism_col_widths');
                if (saved) {{
                    var parsed = JSON.parse(saved);
                    lockedWidths = parsed.widths || lockedWidths;
                    columnWidthsLocked = !!parsed.locked;
                }}
            }} catch(e) {{}}
            updateLockUI();
        }}

        function saveLockedWidths() {{
            try {{
                localStorage.setItem('materialism_col_widths', JSON.stringify({{
                    locked: columnWidthsLocked,
                    widths: lockedWidths
                }}));
            }} catch(e) {{}}
        }}

        function captureCurrentWidths(tableEl, context) {{
            if (!tableEl) return null;
            var ths = tableEl.querySelectorAll('thead th');
            if (!ths.length) return null;
            var widths = [];
            for (var i = 0; i < ths.length; i++) {{
                widths.push(ths[i].offsetWidth + 'px');
            }}
            return widths;
        }}

        function toggleColumnLock() {{
            if (!columnWidthsLocked) {{
                // Locking: capture current pixel widths from whichever table is visible
                var homeTbl = document.getElementById('home-table');
                if (homeTbl && homeTbl.querySelector('thead th')) {{
                    lockedWidths[homeTab] = captureCurrentWidths(homeTbl, homeTab);
                }}
                // Also capture the other home tab default (will be overridden when that tab is shown)
                columnWidthsLocked = true;
            }} else {{
                columnWidthsLocked = false;
            }}
            saveLockedWidths();
            updateLockUI();
            buildHomeTable();
        }}

        function updateLockUI() {{
            var btn = document.getElementById('col-lock-btn');
            var iconUnlocked = document.getElementById('lock-icon-unlocked');
            var iconLocked = document.getElementById('lock-icon-locked');
            if (!btn) return;
            if (columnWidthsLocked) {{
                btn.classList.add('locked');
                btn.title = 'Unlock column widths';
                iconUnlocked.style.display = 'none';
                iconLocked.style.display = '';
            }} else {{
                btn.classList.remove('locked');
                btn.title = 'Lock column widths';
                iconUnlocked.style.display = '';
                iconLocked.style.display = 'none';
            }}
        }}

        function getWidths(context) {{
            if (columnWidthsLocked && lockedWidths[context]) {{
                return lockedWidths[context];
            }}
            return DEFAULT_WIDTHS[context] || null;
        }}

        // ===================== ALIASES =====================
        const SOLVENT_ALIASES = {{
            'nmp': '1-Methyl-2-Pyrrolidinone',
            'n-methyl-2-pyrrolidone': '1-Methyl-2-Pyrrolidinone',
            'dmso': 'Dimethyl sulfoxide',
            'dmf': 'N,N-Dimethylformamide',
            'dma': 'N,N-Dimethylacetamide',
            'dmac': 'N,N-Dimethylacetamide',
            'thf': 'Tetrahydrofuran',
            'dcm': 'Dichloromethane',
            'methylene chloride': 'Dichloromethane',
            'meoh': 'Methanol',
            'etoh': 'Ethanol',
            'ipa': '2-Propanol',
            'isopropanol': '2-Propanol',
            'isopropyl alcohol': '2-Propanol',
            'mek': 'Methyl ethyl ketone',
            'mibk': 'Methyl Isobutyl Ketone',
            'acn': 'Acetonitrile',
            'tce': 'Trichloroethylene',
            'chloroform': 'Chloroform',
            'chcl3': 'Chloroform',
            'water': 'Water',
            'h2o': 'Water',
            'acetone': 'Acetone',
            'toluene': 'Toluene',
            'benzene': 'Benzene',
            'hexane': 'Hexane',
            'pentane': 'Pentane',
            'cyclohexane': 'Cyclohexane',
            'xylene': 'Xylene',
            'ethyl acetate': 'Ethyl Acetate',
            'etoac': 'Ethyl Acetate',
            'diethyl ether': 'Diethyl ether',
            'ether': 'Diethyl ether',
            'formamide': 'Formamide',
            'dmpu': 'DMPU (1,3-Dimethyl-3,4,5,6-Tetrahydro-2(1H)-Pyrimidinone)',
            'pgmea': 'Propylene Glycol Methyl Ether Acetate',
            'nma': 'N-Methyl Acetamide',
            'gbl': 'gamma-Butyrolactone',
            'butyrolactone': 'gamma-Butyrolactone',
            'dioxane': '1,4-Dioxane',
            'pyridine': 'Pyridine',
            'nitromethane': 'Nitromethane',
        }};

        const POLYMER_ALIASES = {{
            'pvc': 'Polyvinyl chloride (PVC)',
            'polyvinyl chloride': 'Polyvinyl chloride (PVC)',
            'pmma': 'Poly(methyl methacrylate) (PMMA)',
            'plexiglass': 'Polymethyl methacrylate (PMMA, acrylic, plexiglas)',
            'acrylic': 'Polymethyl methacrylate (PMMA, acrylic, plexiglas)',
            'ps': 'Polystyrene (PS)',
            'polystyrene': 'Polystyrene (PS)',
            'pe': 'Polyethylene',
            'polyethylene': 'Polyethylene',
            'hdpe': 'HDPE',
            'ldpe': 'LDPE',
            'pp': 'Polypropylene',
            'polypropylene': 'Polypropylene',
            'ptfe': 'Polytetrafluoroethylene (PTFE)',
            'teflon': 'Polytetrafluoroethylene (PTFE)',
            'pet': 'Polyethylene terephthalate (PET)',
            'abs': 'Acrylonitrile butadiene styrene (ABS)',
            'nylon': 'Nylon 6,6',
            'nylon 6': 'Nylon 6 (polycaprolactum, aramid 6)',
            'nylon 66': 'Nylon 6,6',
            'nylon 6,6': 'Nylon 6,6',
            'nylon 11': 'Nylon 11',
            'nylon 12': 'Nylon 12',
            'pa': 'Nylon 6,6',
            'pa6': 'Nylon 6 (polycaprolactum, aramid 6)',
            'pa66': 'Nylon 6,6',
            'pc': 'Polycarbonate',
            'polycarbonate': 'Polycarbonate',
            'pu': 'Polyurethane',
            'polyurethane': 'Polyurethane',
            'pla': 'PLA',
            'polylactic acid': 'PLA',
            'pvdf': 'PVDF',
            'pva': 'Poly(vinyl alcohol)',
            'pvac': 'Poly(vinyl acetate)',
            'pvb': 'Poly(vinyl butyral)',
            'epoxy': 'Epoxy resin (Bisphenol A)',
            'silicone': 'Silicone (PDMS)',
            'pdms': 'Silicone (PDMS)',
            'polydimethylsiloxane': 'Silicone (PDMS)',
            'rubber': 'Natural rubber',
            'natural rubber': 'Natural rubber',
            'peek': 'PEEK',
            'polyetheretherketone': 'PEEK',
            'pei': 'PEI',
            'polyetherimide': 'PEI',
            'pps': 'Polyphenylene sulfide (PPS)',
            'petg': 'PETG',
            'cellulose acetate': 'Cellulose acetate',
            'cellulose': 'Cellulose acetate',
            'ca': 'Cellulose acetate',
            'eva': 'Ethylene vinyl acetate (EVA)',
            'san': 'Styrene acrylonitrile (SAN)',
        }};

        // ===================== COMMON MATERIALS FILTER =====================
        var simpleMode = false;
        function onSimpleModeChange() {{
            simpleMode = document.getElementById('simple-mode').checked;
            // Update the 3D plot to show/hide non-common materials
            _updatePlotForCommonFilter();
            // Rebuild home table with filter applied
            buildHomeTable();
            // Re-run last search if there was one
            if (lastSearchQuery) {{
                document.getElementById('nl-search').value = lastSearchQuery;
                runSearch();
            }}
        }}

        function _updatePlotForCommonFilter() {{
            if (!plotDiv || !plotDiv.data) return;
            if (simpleMode) {{
                // Dim non-common materials but keep marker sizes unchanged
                var filteredColors = SOLVENTS.map(function(s, i) {{
                    return s.common ? (_solventColors[i] || '#888') : 'rgba(200,200,200,0.05)';
                }});
                var filteredOpacity = SOLVENTS.map(function(s) {{ return s.common ? 0.9 : 0.03; }});
                var filteredPolyColors = POLYMERS.map(function(p) {{ return p.common ? 'gold' : 'rgba(200,200,200,0.05)'; }});
                var filteredPolyOpacity = POLYMERS.map(function(p) {{ return p.common ? 0.95 : 0.03; }});
                Plotly.restyle(plotDiv, {{
                    'marker.color': [filteredColors, filteredPolyColors],
                    'marker.opacity': [filteredOpacity, filteredPolyOpacity],
                }}, [0, 1]);
            }} else {{
                // Restore normal appearance
                Plotly.restyle(plotDiv, {{
                    'marker.color': [_solventColors, 'gold'],
                    'marker.opacity': [0.85, 0.95],
                }}, [0, 1]);
            }}
        }}

        // ===================== HSP MATH =====================
        // Pre-compute typed arrays for fast distance calculations
        var _sDD = new Float64Array(SOLVENTS.length);
        var _sDP = new Float64Array(SOLVENTS.length);
        var _sDH = new Float64Array(SOLVENTS.length);
        var _sCommon = new Uint8Array(SOLVENTS.length);
        for (var _si = 0; _si < SOLVENTS.length; _si++) {{
            _sDD[_si] = SOLVENTS[_si].dd; _sDP[_si] = SOLVENTS[_si].dp; _sDH[_si] = SOLVENTS[_si].dh;
            _sCommon[_si] = SOLVENTS[_si].common ? 1 : 0;
        }}

        function hspDistance(a, b) {{
            var ddd = a.dd - b.dd, ddp = a.dp - b.dp, ddh = a.dh - b.dh;
            return Math.sqrt(4 * ddd * ddd + ddp * ddp + ddh * ddh);
        }}
        function redNumber(solvent, polymer) {{
            if (!polymer.r || polymer.r <= 0) return null;
            return hspDistance(solvent, polymer) / polymer.r;
        }}

        // Partial sort: get top-K smallest items without sorting the full array.
        // Uses quickselect (O(N) average) then sorts only the top K (O(K log K)).
        function topK(arr, k, key) {{
            if (arr.length <= k) {{ arr.sort(function(a, b) {{ return key(a) - key(b); }}); return arr; }}
            // Quickselect partition
            function swap(i, j) {{ var t = arr[i]; arr[i] = arr[j]; arr[j] = t; }}
            function partition(lo, hi) {{
                var pivot = key(arr[hi]), i = lo;
                for (var j = lo; j < hi; j++) {{
                    if (key(arr[j]) <= pivot) {{ swap(i, j); i++; }}
                }}
                swap(i, hi);
                return i;
            }}
            var lo = 0, hi = arr.length - 1;
            while (lo < hi) {{
                var p = partition(lo, hi);
                if (p === k) break;
                else if (p < k) lo = p + 1;
                else hi = p - 1;
            }}
            var top = arr.slice(0, k);
            top.sort(function(a, b) {{ return key(a) - key(b); }});
            return top;
        }}
        // Same but for largest (bottom-K by descending key)
        function bottomK(arr, k, key) {{
            return topK(arr, k, function(x) {{ return -key(x); }});
        }}

        // ===================== COLOR SCALING =====================
        function distanceToColor(t) {{
            t = Math.max(0, Math.min(1, t));
            let r, g, b;
            if (t < 0.5) {{
                const s = t * 2;
                r = Math.round(0x00 + s * (0xCC - 0x00));
                g = Math.round(0xCC + s * (0xCC - 0xCC));
                b = Math.round(0x66 + s * (0x00 - 0x66));
            }} else {{
                const s = (t - 0.5) * 2;
                r = Math.round(0xCC + s * (0xEF - 0xCC));
                g = Math.round(0xCC + s * (0x55 - 0xCC));
                b = Math.round(0x00 + s * (0x3B - 0x00));
            }}
            return 'rgb(' + r + ',' + g + ',' + b + ')';
        }}

        function computeResultColors(validResults) {{
            if (validResults.length === 0) return [];
            const distances = validResults.map(r => {{
                if (r.ra != null) return r.ra;
                if (r.combinedScore != null) return r.combinedScore;
                return 0;
            }});
            const minD = Math.min(...distances);
            const maxD = Math.max(...distances);
            const range = maxD - minD;
            return distances.map(d => {{
                if (range === 0) return distanceToColor(0);
                return distanceToColor((d - minD) / range);
            }});
        }}

        // ===================== FUZZY MATCH =====================
        function normalize(s) {{ return s.toLowerCase().replace(/[^a-z0-9]/g, ''); }}

        function resolveAlias(query, aliases) {{
            const q = query.toLowerCase().trim();
            if (aliases[q]) return aliases[q];
            const qn = normalize(q);
            for (const [alias, name] of Object.entries(aliases)) {{
                if (normalize(alias) === qn) return name;
            }}
            return null;
        }}

        function fuzzyMatch(query, items, key) {{
            const q = normalize(query);
            if (!q) return null;
            let best = null, bestScore = 0;
            for (const item of items) {{
                const name = normalize(item[key || 'name']);
                let score = 0;
                if (name === q) score = 1000;
                else if (name.startsWith(q)) score = 500 + q.length;
                else if (name.includes(q)) score = 200 + q.length;
                else if (q.includes(name) && name.length > 2) score = 100 + name.length;
                else {{
                    const qWords = query.toLowerCase().split(/[\s,]+/).filter(w => w.length > 1);
                    for (const w of qWords) {{
                        if (name.includes(normalize(w))) score += 30 + w.length;
                    }}
                }}
                if (score > bestScore) {{ bestScore = score; best = item; }}
            }}
            return bestScore > 0 ? best : null;
        }}

        function findSolvent(query) {{
            const aliased = resolveAlias(query, SOLVENT_ALIASES);
            if (aliased) {{
                const exact = SOLVENTS.find(s => s.name === aliased);
                if (exact) return exact;
            }}
            return fuzzyMatch(query, SOLVENTS, 'name');
        }}

        function findPolymer(query) {{
            const aliased = resolveAlias(query, POLYMER_ALIASES);
            if (aliased) {{
                const exact = POLYMERS.find(p => p.name === aliased);
                if (exact) return exact;
                return fuzzyMatch(aliased, POLYMERS, 'name');
            }}
            return fuzzyMatch(query, POLYMERS, 'name');
        }}

        function findMaterial(query) {{
            const p = findPolymer(query);
            const s = findSolvent(query);
            return {{ polymer: p, solvent: s }};
        }}

        // ===================== RESULT COUNT =====================
        let resultCount = 25;

        var lastSearchQuery = '';
        function setResultCount(n) {{
            resultCount = n;
            document.querySelectorAll('.rc-btn').forEach(btn => {{
                btn.classList.toggle('active', parseInt(btn.textContent) === n);
            }});
            if (lastSearchQuery) {{
                var parsed = parseQuery(lastSearchQuery);
                var result = executeSearch(parsed);
                var html = renderResultsHTML(result);
                showResults(html);
                if (!result.error) updatePlotWithResults(result);
            }}
        }}

        // ===================== CHAT STATE =====================
        let chatContext = null;
        let chatMessages = [];

        // ===================== NLP QUERY PARSER =====================
        function parseQuery(raw) {{
            const q = raw.toLowerCase().trim();

            // --- Multi-material detection ---
            // Separator: "and", "but", comma, semicolon
            var sep = /\s*(?:,\s*(?:and\s+|but\s+)?|;\s*|\s+and\s+|\s+but\s+)\s*/;
            // "solvents?" is optional in all patterns so "good for X, bad for Y" works
            var optSolv = '(?:solvents?\\\\s+)?';

            // "good (solvents) for X, bad (solvents) for Y"
            var multiGoodBad = q.match(new RegExp('good\\\\s+' + optSolv + 'for\\\\s+(.+?)' + sep.source + '(?:a\\\\s+)?bad\\\\s+' + optSolv + 'for\\\\s+(.+)', 'i'));
            if (multiGoodBad) {{
                return {{ intent: 'multi_material', materials: [
                    {{ name: multiGoodBad[1].replace(/[?.!]/g, '').trim(), requirement: 'good' }},
                    {{ name: multiGoodBad[2].replace(/[?.!]/g, '').trim(), requirement: 'bad' }},
                ]}};
            }}
            // "bad (solvents) for X, good (solvents) for Y"
            var multiBadGood = q.match(new RegExp('bad\\\\s+' + optSolv + 'for\\\\s+(.+?)' + sep.source + '(?:a\\\\s+)?good\\\\s+' + optSolv + 'for\\\\s+(.+)', 'i'));
            if (multiBadGood) {{
                return {{ intent: 'multi_material', materials: [
                    {{ name: multiBadGood[1].replace(/[?.!]/g, '').trim(), requirement: 'bad' }},
                    {{ name: multiBadGood[2].replace(/[?.!]/g, '').trim(), requirement: 'good' }},
                ]}};
            }}
            // "good (solvents) for (both) X and Y"
            var multiBoth = q.match(new RegExp('good\\\\s+' + optSolv + 'for\\\\s+(?:both\\\\s+)?(.+?)' + sep.source + '(.+)', 'i'));
            if (multiBoth) {{
                return {{ intent: 'multi_material', materials: [
                    {{ name: multiBoth[1].replace(/[?.!]/g, '').trim(), requirement: 'good' }},
                    {{ name: multiBoth[2].replace(/[?.!]/g, '').trim(), requirement: 'good' }},
                ]}};
            }}
            // "bad (solvents) for (both) X and Y"
            var multiBothBad = q.match(new RegExp('bad\\\\s+' + optSolv + 'for\\\\s+(?:both\\\\s+)?(.+?)' + sep.source + '(.+)', 'i'));
            if (multiBothBad) {{
                return {{ intent: 'multi_material', materials: [
                    {{ name: multiBothBad[1].replace(/[?.!]/g, '').trim(), requirement: 'bad' }},
                    {{ name: multiBothBad[2].replace(/[?.!]/g, '').trim(), requirement: 'bad' }},
                ]}};
            }}
            // "dissolves (both) X and Y"
            var dissolvesBoth = q.match(new RegExp('(?:dissolves?|dissolve)\\\\s+(?:both\\\\s+)?(.+?)' + sep.source + '(.+)', 'i'));
            if (dissolvesBoth) {{
                return {{ intent: 'multi_material', materials: [
                    {{ name: dissolvesBoth[1].replace(/[?.!]/g, '').trim(), requirement: 'good' }},
                    {{ name: dissolvesBoth[2].replace(/[?.!]/g, '').trim(), requirement: 'good' }},
                ]}};
            }}

            const hasStandardIntent = /good\s+solvent|bad\s+solvent|best\s+solvent|worst\s+solvent|poor\s+solvent|dissolve|compatible\s+with|incompatible|similar\s+to|close\s+to|solvents?\s+for|polymers?\s+for|polymers?\s+similar|solvents?\s+similar|polymers?\s+(?:dissolved|compatible)|what\s+(?:does|can|will)|which\s+polymers/i.test(q);

            if (!hasStandardIntent && chatContext) {{
                const followUpPatterns = [
                    /^(?:what|how)\s+about\s+(.+)/i,
                    /^(?:and|also|try|check|test|evaluate)\s+(.+)/i,
                    /^(?:would)\s+(.+?)\s+(?:work)/i,
                ];
                for (const p of followUpPatterns) {{
                    const m = q.match(p);
                    if (m) return {{ intent: 'followup', material: m[1].replace(/[?.!]/g, '').trim() }};
                }}
                const anyIntentWord = /good|bad|best|worst|similar|close|near|dissolve|compatible|incompatible|find|search|show|list|solvent|polymer/i;
                if (!anyIntentWord.test(q)) {{
                    return {{ intent: 'followup', material: q.replace(/[?.!]/g, '').trim() }};
                }}
            }}

            const badPatterns = [
                /bad\s+solvents?\s+for/i, /bad\s+for/i,
                /(?:poor|worst|incompatible)\s+(?:solvents?\s+)?for/i,
                /solvents?\s+(?:that\s+)?(?:won'?t|will\s+not|cannot|can'?t)\s+dissolve/i,
                /(?:resist|resistant|insoluble)/i, /non[- ]?solvents?\s+for/i,
            ];
            const goodPatterns = [
                /good\s+solvents?\s+(for|to\s+dissolve)/i, /good\s+for/i,
                /best\s+(?:solvents?\s+)?for/i,
                /(?:what|which)\s+(?:solvents?\s+)?(?:dissolves?|will\s+dissolve|can\s+dissolve)/i,
                /solvents?\s+(?:that\s+)?(?:dissolves?|for|compatible\s+with)/i,
                /dissolve\s+/i, /compatible\s+(?:solvents?\s+)?for/i, /soluble\s+in/i,
                /find\s+(?:me\s+)?(?:a\s+)?solvents?\s+for/i,
            ];
            const similarSolventPatterns = [
                /solvents?\s+(?:similar|close|near)\s+to/i,
                /(?:similar|close|near)\s+(?:to\s+)?(?:the\s+)?solvents?/i,
                /(?:alternatives?\s+to)\s+/i, /replace(?:ment)?\s+for\s+/i,
            ];
            const similarPolymerPatterns = [
                /polymers?\s+(?:similar|close|near)\s+to/i,
                /(?:similar|close|near)\s+(?:to\s+)?(?:the\s+)?polymers?/i,
                /materials?\s+(?:similar|close|near)\s+to/i,
            ];
            const polymersForSolventPatterns = [
                /(?:which|what)\s+polymers?\s+(?:does|can|will)\s+(.+?)\s+dissolve/i,
                /(?:which|what)\s+polymers?\s+(?:are\s+)?(?:dissolved|soluble|compatible)\s+(?:by|in|with)\s+(.+)/i,
                /polymers?\s+(?:dissolved|soluble|compatible)\s+(?:by|in|with)\s+/i,
                /(?:what|which)\s+(?:can|does|will)\s+(.+?)\s+dissolve/i,
                /polymers?\s+for\s+/i,
            ];

            // Check polymers-for-solvent FIRST (before good/bad which would misinterpret)
            for (const p of polymersForSolventPatterns) {{
                var m = q.match(p);
                if (m) {{
                    var mat = m[1] ? m[1].replace(/[?.!]/g, '').trim() : q.replace(p, '').replace(/[?.!]/g, '').trim();
                    return {{ intent: 'polymers_for_solvent', material: mat }};
                }}
            }}
            for (const p of badPatterns) {{ if (p.test(q)) return {{ intent: 'bad_solvents', material: q.replace(p, '').replace(/[?.!]/g, '').trim() }}; }}
            for (const p of goodPatterns) {{ if (p.test(q)) return {{ intent: 'good_solvents', material: q.replace(p, '').replace(/[?.!]/g, '').trim() }}; }}
            for (const p of similarPolymerPatterns) {{ if (p.test(q)) return {{ intent: 'similar_polymers', material: q.replace(p, '').replace(/[?.!]/g, '').trim() }}; }}
            for (const p of similarSolventPatterns) {{ if (p.test(q)) return {{ intent: 'similar_solvents', material: q.replace(p, '').replace(/[?.!]/g, '').trim() }}; }}

            const polyMatch = findPolymer(q.replace(/[?.!]/g, ''));
            if (polyMatch) return {{ intent: 'good_solvents', material: q.replace(/[?.!]/g, '').trim() }};

            const solvMatch = findSolvent(q.replace(/[?.!]/g, ''));
            if (solvMatch) return {{ intent: 'similar_solvents', material: q.replace(/[?.!]/g, '').trim() }};

            return {{ intent: 'unknown', material: q }};
        }}

        // ===================== SEARCH ENGINE =====================
        function executeSearch(parsed) {{
            const {{ intent, material }} = parsed;

            if (intent === 'followup' && chatContext) {{
                const names = material.split(/\s+(?:or|and|,|\/)\s*|\s*[,\/]\s*/i).map(s => s.trim()).filter(Boolean);
                const results = [];
                for (const name of names) {{
                    if (chatContext.intent === 'good_solvents' || chatContext.intent === 'bad_solvents') {{
                        const s = findSolvent(name);
                        if (s) {{
                            const ra = hspDistance(s, chatContext.target);
                            const red = redNumber(s, chatContext.target);
                            results.push({{ ...s, ra, red, queryName: name }});
                        }} else {{
                            const p = findPolymer(name);
                            if (p) {{ results.push({{ ...p, ra: hspDistance(p, chatContext.target), red: null, queryName: name, isPolymer: true }}); }}
                            else {{ results.push({{ name: name, queryName: name, notFound: true }}); }}
                        }}
                    }} else if (chatContext.intent === 'similar_solvents') {{
                        const s = findSolvent(name);
                        if (s) {{ results.push({{ ...s, ra: hspDistance(s, chatContext.target), queryName: name }}); }}
                        else {{ results.push({{ name: name, queryName: name, notFound: true }}); }}
                    }} else if (chatContext.intent === 'similar_polymers') {{
                        const p = findPolymer(name);
                        if (p) {{ results.push({{ ...p, ra: hspDistance(p, chatContext.target), queryName: name }}); }}
                        else {{ results.push({{ name: name, queryName: name, notFound: true }}); }}
                    }}
                }}
                return {{ intent: 'followup', target: chatContext.target, results, description: 'Evaluating specific materials against ' + chatContext.target.name, targetType: chatContext.targetType, parentIntent: chatContext.intent }};
            }}

            if (intent === 'multi_material') {{
                const targets = [];
                for (const mat of parsed.materials) {{
                    const target = findPolymer(mat.name);
                    if (!target) return {{ error: 'Could not find polymer "' + mat.name + '". Try names like "polystyrene", "PVC", "PMMA", or "nylon".' }};
                    targets.push({{ ...target, requirement: mat.requirement }});
                }}
                // Compute combined scores using typed arrays — lightweight objects, defer spread
                var N = SOLVENTS.length, scored = new Array(N);
                var tDDs = targets.map(function(t) {{ return t.dd; }});
                var tDPs = targets.map(function(t) {{ return t.dp; }});
                var tDHs = targets.map(function(t) {{ return t.dh; }});
                var tRs = targets.map(function(t) {{ return (t.r && t.r > 0) ? t.r : 0; }});
                var tGood = targets.map(function(t) {{ return t.requirement === 'good' ? 1 : -1; }});
                for (var si = 0; si < N; si++) {{
                    var cs = 0, dd0 = _sDD[si], dp0 = _sDP[si], dh0 = _sDH[si];
                    for (var ti = 0; ti < targets.length; ti++) {{
                        var ddd = dd0 - tDDs[ti], ddp = dp0 - tDPs[ti], ddh = dh0 - tDHs[ti];
                        cs += tGood[ti] * Math.sqrt(4 * ddd * ddd + ddp * ddp + ddh * ddh);
                    }}
                    scored[si] = {{ _i: si, combinedScore: cs }};
                }}
                if (simpleMode) scored = scored.filter(function(x) {{ return _sCommon[x._i]; }});
                var top = topK(scored, resultCount, function(x) {{ return x.combinedScore; }});
                var results = top.map(function(x) {{
                    var s = SOLVENTS[x._i], info = {{ ...s, reds: {{}}, ras: {{}}, combinedScore: x.combinedScore }};
                    for (var ti = 0; ti < targets.length; ti++) {{
                        var ra = hspDistance(s, targets[ti]);
                        info.ras[targets[ti].name] = ra;
                        info.reds[targets[ti].name] = tRs[ti] > 0 ? ra / tRs[ti] : null;
                    }}
                    return info;
                }});
                const desc = targets.map(t => (t.requirement === 'good' ? 'compatible with' : 'incompatible with') + ' ' + t.name).join(' AND ');
                chatContext = {{ intent: 'multi_material', targets, targetType: 'polymer' }};
                return {{ intent: 'multi_material', targets, results, description: 'Top ' + resultCount + ' solvents: ' + desc + '.', targetType: 'polymer' }};
            }}

            if (intent === 'good_solvents' || intent === 'bad_solvents') {{
                let target = findPolymer(material);
                if (!target) {{ const words = material.split(/\s+/); for (const w of words) {{ target = findPolymer(w); if (target) break; }} }}
                if (!target) return {{ error: 'Could not find a matching polymer for "' + material + '". Try names like "polystyrene", "PVC", "PMMA", or "nylon".' }};
                // Typed-array distance computation + quickselect — avoids spreading 1630 objects
                var tDD = target.dd, tDP = target.dp, tDH = target.dh, N = SOLVENTS.length;
                var scored = new Array(N);
                for (var si = 0; si < N; si++) {{
                    var ddd = _sDD[si] - tDD, ddp = _sDP[si] - tDP, ddh = _sDH[si] - tDH;
                    scored[si] = {{ _i: si, ra: Math.sqrt(4 * ddd * ddd + ddp * ddp + ddh * ddh) }};
                }}
                if (simpleMode) scored = scored.filter(function(x) {{ return _sCommon[x._i]; }});
                var top;
                if (intent === 'good_solvents') {{
                    top = topK(scored, resultCount, function(x) {{ return x.ra; }});
                }} else {{
                    top = bottomK(scored, resultCount, function(x) {{ return x.ra; }});
                }}
                var results = top.map(function(x) {{
                    var s = SOLVENTS[x._i];
                    return {{ ...s, ra: x.ra, red: (target.r && target.r > 0) ? x.ra / target.r : null }};
                }});
                chatContext = {{ intent, target, targetType: 'polymer' }};
                var simpleSuffix = simpleMode ? ' (Common materials only)' : '';
                if (intent === 'good_solvents') {{
                    return {{ intent, target, results, description: 'Top ' + resultCount + ' solvents by HSP distance (Ra). RED < 1 = inside solubility sphere = compatible.' + simpleSuffix, targetType: 'polymer' }};
                }} else {{
                    return {{ intent, target, results, description: 'Top ' + resultCount + ' most incompatible solvents by HSP distance (Ra). RED > 1 = outside sphere.' + simpleSuffix, targetType: 'polymer' }};
                }}
            }}

            if (intent === 'similar_solvents') {{
                let target = findSolvent(material);
                if (!target) {{ const words = material.split(/\s+/); for (const w of words) {{ target = findSolvent(w); if (target) break; }} }}
                if (!target) return {{ error: 'Could not find solvent "' + material + '". Try "toluene", "acetone", "NMP", "DMSO", etc.' }};
                var tDD = target.dd, tDP = target.dp, tDH = target.dh;
                var scored = [];
                for (var si = 0; si < SOLVENTS.length; si++) {{
                    if (SOLVENTS[si].name === target.name) continue;
                    if (simpleMode && !_sCommon[si]) continue;
                    var ddd = _sDD[si] - tDD, ddp = _sDP[si] - tDP, ddh = _sDH[si] - tDH;
                    scored.push({{ _i: si, ra: Math.sqrt(4 * ddd * ddd + ddp * ddp + ddh * ddh) }});
                }}
                var top = topK(scored, resultCount, function(x) {{ return x.ra; }});
                var results = top.map(function(x) {{ return {{ ...SOLVENTS[x._i], ra: x.ra }}; }});
                chatContext = {{ intent, target, targetType: 'solvent' }};
                return {{ intent, target, results, description: 'Solvents closest to ' + target.name + ' in Hansen space.' + (simpleMode ? ' (Common materials only)' : ''), targetType: 'solvent' }};
            }}

            if (intent === 'similar_polymers') {{
                let target = findPolymer(material);
                if (!target) {{ const words = material.split(/\s+/); for (const w of words) {{ target = findPolymer(w); if (target) break; }} }}
                if (!target) return {{ error: 'Could not find polymer "' + material + '". Try "polystyrene", "epoxy", "PMMA", etc.' }};
                var scored = POLYMERS.filter(p => p.name !== target.name);
                if (simpleMode) scored = scored.filter(function(p) {{ return p.common; }});
                scored = scored.map(p => ({{ ...p, ra: hspDistance(p, target) }}));
                var results = topK(scored, resultCount, function(x) {{ return x.ra; }});
                chatContext = {{ intent, target, targetType: 'polymer' }};
                return {{ intent, target, results, description: 'Polymers closest to ' + target.name + ' in Hansen space.', targetType: 'polymer' }};
            }}

            if (intent === 'polymers_for_solvent') {{
                let target = findSolvent(material);
                if (!target) {{ const words = material.split(/\s+/); for (const w of words) {{ target = findSolvent(w); if (target) break; }} }}
                if (!target) return {{ error: 'Could not find solvent "' + material + '". Try "toluene", "acetone", "NMP", "DMSO", etc.' }};
                var scored = POLYMERS.filter(p => p.r && p.r > 0);
                if (simpleMode) scored = scored.filter(function(p) {{ return p.common; }});
                scored = scored.map(p => ({{ ...p, ra: hspDistance(target, p), red: redNumber(target, p) }}));
                var results = topK(scored, resultCount, function(x) {{ return x.ra; }});
                chatContext = {{ intent: 'polymers_for_solvent', target, targetType: 'solvent' }};
                return {{ intent: 'polymers_for_solvent', target, results, description: 'Polymers most easily dissolved by ' + target.name + '. RED < 1 = inside solubility sphere = compatible.', targetType: 'solvent' }};
            }}

            return {{ error: 'Could not understand the query. Try "good solvents for polystyrene", "bad solvents for PVC", "solvents similar to toluene", or "what polymers does acetone dissolve?".' }};
        }}

        // ===================== SHOW RESULTS (replaces, not appends) =====================
        function showResults(html) {{
            hideHomePanel();
            const panel = document.getElementById('chat-panel');
            panel.innerHTML = html;
            panel.classList.add('visible');
            panel.scrollTop = 0;
        }}

        // ===================== RESULTS TABLE SORTING =====================
        let resultSortDir = {{}};
        function sortResultsTable(tableEl, colIdx) {{
            const tbody = tableEl.querySelector('tbody');
            const allRows = Array.from(tbody.rows);
            const pinned = allRows.filter(r => r.dataset.target);
            const sortable = allRows.filter(r => !r.dataset.target);
            const key = 'rt-' + colIdx;
            resultSortDir[key] = !resultSortDir[key];
            const dir = resultSortDir[key] ? 1 : -1;
            sortable.sort((a, b) => {{
                let va = a.cells[colIdx].textContent.trim();
                let vb = b.cells[colIdx].textContent.trim();
                const na = parseFloat(va), nb = parseFloat(vb);
                if (!isNaN(na) && !isNaN(nb)) return (na - nb) * dir;
                return va.localeCompare(vb) * dir;
            }});
            const frag = document.createDocumentFragment();
            pinned.forEach(row => frag.appendChild(row));
            sortable.forEach(row => frag.appendChild(row));
            tbody.appendChild(frag);
            tableEl.querySelectorAll('th').forEach((th, i) => {{
                th.classList.remove('sort-asc', 'sort-desc');
                if (i === colIdx) th.classList.add(dir === 1 ? 'sort-asc' : 'sort-desc');
            }});
        }}

        function renderResultsHTML(result) {{
            if (result.error) return '<span style="color:#EF553B">' + result.error + '</span>';

            const {{ intent, results, description }} = result;
            const target = result.target || (result.targets ? result.targets[0] : null);
            const parentIntent = result.parentIntent || intent;

            var h = []; // array + join is faster than string +=

            const isMulti = intent === 'multi_material';
            const showRed = parentIntent === 'good_solvents' || parentIntent === 'bad_solvents' || parentIntent === 'polymers_for_solvent';
            const targetList = isMulti ? (result.targets || []) : (target ? [target] : []);
            const showTarget = targetList.length > 0 && intent !== 'followup';

            // --- Single unified table with shared columns ---
            const tableId = 'rt-' + Date.now();
            h.push('<table class="results-table" id="', tableId, '" style="margin-top:10px">');
            // Fixed column widths so table doesn't shift between queries
            var rw = getWidths('results');
            h.push('<colgroup>');
            rw.forEach(function(w) {{ h.push('<col style="width:', w, '">'); }});
            h.push('</colgroup>');
            h.push('<thead><tr>');
            let colNum = 0;
            var _rColTips = {{
                'CAS #': 'CAS Registry Number \u2014 unique identifier for chemical substances',
                '&delta;D (MPa<sup>\u00bd</sup>)': 'Dispersion \u2014 van der Waals / London dispersion forces (MPa\u00bd)',
                '&delta;P (MPa<sup>\u00bd</sup>)': 'Polarity \u2014 dipole-dipole intermolecular forces (MPa\u00bd)',
                '&delta;H (MPa<sup>\u00bd</sup>)': 'Hydrogen bonding \u2014 hydrogen bond donor/acceptor capability (MPa\u00bd)',
                'MW (g/mol)': 'Molecular weight (g/mol)',
                'BP (&deg;C)': 'Boiling point in degrees Celsius',
                'Ra (MPa<sup>\u00bd</sup>)': 'HSP distance between solvent and polymer in 3D Hansen space (MPa\u00bd)',
                'R&#8320; (MPa<sup>\u00bd</sup>)': 'Interaction radius of the polymer solubility sphere (MPa\u00bd)',
                'RED': 'Relative Energy Difference = Ra/R\u2080. RED < 1 = compatible, RED > 1 = incompatible'
            }};
            const th = (label) => {{
                var tip = _rColTips[label] || '';
                if (!tip && label.indexOf('Ra(') === 0) tip = _rColTips['Ra (MPa<sup>\u00bd</sup>)'];
                if (!tip && label.indexOf('RED(') === 0) tip = _rColTips['RED'];
                return '<th onclick="sortResultsTable(this.closest(\\x27table\\x27),' + (colNum++) + ')" style="cursor:pointer"' + (tip ? ' title="' + tip + '"' : '') + '>' + label + '</th>';
            }};
            h.push(th('#'), th('Name'), th('CAS #'), th('&delta;D (MPa<sup>\u00bd</sup>)'), th('&delta;P (MPa<sup>\u00bd</sup>)'), th('&delta;H (MPa<sup>\u00bd</sup>)'), th('MW (g/mol)'), th('BP (&deg;C)'));
            if (isMulti) {{ result.targets.forEach(t => {{ h.push(th('Ra(' + t.name.slice(0, 15) + ')'), th('RED(' + t.name.slice(0, 15) + ')')); }}); }}
            else if (showRed) {{ h.push(th('Ra (MPa<sup>\u00bd</sup>)'), th('RED')); }}
            else if (parentIntent === 'similar_solvents') {{ h.push(th('Ra (MPa<sup>\u00bd</sup>)'), th('Category')); }}
            else {{ h.push(th('Ra (MPa<sup>\u00bd</sup>)'), th('R&#8320; (MPa<sup>\u00bd</sup>)'), th('Type')); }}
            h.push(th('Source'));
            h.push('</tr></thead><tbody>');

            // --- Target material rows ---
            if (showTarget) {{
                targetList.forEach(t => {{
                    h.push('<tr data-target="1" style="background:#eef1f6;border-bottom:2px solid #dfe6e9">',
                        '<td style="color:#e94560;font-weight:bold">★</td>',
                        '<td><strong style="color:#e94560">', t.name, '</strong></td>',
                        '<td>', (t.cas || ''), '</td>',
                        '<td>', (t.dd != null ? t.dd.toFixed(1) : ''), '</td>',
                        '<td>', (t.dp != null ? t.dp.toFixed(1) : ''), '</td>',
                        '<td>', (t.dh != null ? t.dh.toFixed(1) : ''), '</td>',
                        '<td>', (t.mw != null ? t.mw : ''), '</td>',
                        '<td>', (t.bp != null ? t.bp : ''), '</td>');
                    if (isMulti) {{
                        result.targets.forEach(tt => {{
                            h.push('<td></td>');
                            if (tt.name === t.name) {{
                                const chipColor = t.requirement === 'bad' ? '#EF553B' : '#00CC96';
                                h.push('<td><span style="display:inline-block;background:', chipColor, ';color:white;padding:2px 10px;border-radius:12px;font-size:0.8rem;font-weight:600">', t.requirement, '</span></td>');
                            }} else {{ h.push('<td></td>'); }}
                        }});
                    }} else if (showRed) {{
                        h.push('<td></td><td style="color:#636e72">R&#8320;=', (t.r || 'N/A'), '</td>');
                    }} else if (parentIntent === 'similar_solvents') {{
                        h.push('<td></td><td>', (t.cat || ''), '</td>');
                    }} else {{
                        h.push('<td></td><td>', (t.r || ''), '</td><td>', (t.type || ''), '</td>');
                    }}
                    h.push('<td>', ((t.src && t.srcUrl) ? '<a href="' + t.srcUrl + '" target="_blank" rel="noopener" style="color:#0984e3;text-decoration:none">' + t.src + '</a>' : (t.src || '')), '</td>');
                    h.push('</tr>');
                }});
            }}

            // --- Candidate result rows ---
            results.forEach((r, i) => {{
                if (r.notFound) {{ h.push('<tr><td class="rank">', (i + 1), '</td><td colspan="11" style="color:#EF553B">Could not find "', r.queryName, '" in the database</td></tr>'); return; }}
                var enc = encodeURIComponent(r.name);
                h.push('<tr data-name="', r.name.replace(/"/g, '&quot;'), '" onclick="highlightInPlot(\\x27', enc, '\\x27)" style="cursor:pointer"><td class="rank">', (i + 1), '</td><td><span class="hoverable-name" onmouseenter="showStructure(event,\\x27', enc, '\\x27)" onmouseleave="hideStructure()">', r.name, '</span></td>');
                h.push('<td>', (r.cas || ''), '</td>');
                h.push('<td>', (r.dd != null ? r.dd.toFixed(1) : ''), '</td><td>', (r.dp != null ? r.dp.toFixed(1) : ''), '</td><td>', (r.dh != null ? r.dh.toFixed(1) : ''), '</td>');
                h.push('<td>', (r.mw != null ? r.mw : ''), '</td><td>', (r.bp != null ? r.bp : ''), '</td>');
                if (isMulti) {{ result.targets.forEach(t => {{ const ra = r.ras[t.name]; const red = r.reds[t.name]; h.push('<td>', (ra != null ? ra.toFixed(2) : ''), '</td>'); let cls = 'red-bad'; if (red != null) {{ if (red < 1) cls = 'red-good'; else if (red < 1.2) cls = 'red-boundary'; }} h.push('<td class="', cls, '">', (red != null ? red.toFixed(2) : 'N/A'), '</td>'); }}); }}
                else {{ h.push('<td>', (r.ra != null ? r.ra.toFixed(2) : ''), '</td>'); if (showRed) {{ const red = r.red; let cls = 'red-bad'; if (red !== null) {{ if (red < 1) cls = 'red-good'; else if (red < 1.2) cls = 'red-boundary'; }} h.push('<td class="', cls, '">', (red !== null ? red.toFixed(2) : 'N/A'), '</td>'); }} else if (parentIntent === 'similar_solvents') {{ h.push('<td>', (r.cat || ''), '</td>'); }} else {{ h.push('<td>', (r.r || ''), '</td><td>', (r.type || ''), '</td>'); }} }}
                h.push('<td>', ((r.src && r.srcUrl) ? '<a href="' + r.srcUrl + '" target="_blank" rel="noopener" style="color:#0984e3;text-decoration:none">' + r.src + '</a>' : (r.src || '')), '</td>');
                h.push('</tr>');
            }});
            h.push('</tbody></table>');
            return h.join('');
        }}

        // ===================== 3D PLOT =====================
        let plotDiv;
        let fullTraces = [];

        function buildFullPlot() {{
            plotDiv = document.getElementById('plotly-div');
            // Single trace for all solvents with per-point colors (instead of 22+ traces)
            _solventColors = SOLVENTS.map(s => CAT_COLORS[s.cat] || '#888');
            fullTraces = [
                {{
                    type: 'scatter3d', mode: 'markers',
                    name: 'Solvents',
                    x: SOLVENTS.map(s => s.dd), y: SOLVENTS.map(s => s.dp), z: SOLVENTS.map(s => s.dh),
                    text: SOLVENTS.map(s => s.name + '<br>CAS: ' + s.cas + '<br>MW: ' + s.mw + '<br>BP: ' + s.bp + '°C'),
                    hovertemplate: '<b>%{{text}}</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>',
                    marker: {{ size: 5, color: _solventColors, opacity: 0.85 }},
                }},
                {{
                    type: 'scatter3d', mode: 'markers',
                    name: 'Polymers',
                    x: POLYMERS.map(p => p.dd), y: POLYMERS.map(p => p.dp), z: POLYMERS.map(p => p.dh),
                    text: POLYMERS.map(p => p.name + '<br>R₀=' + p.r),
                    hovertemplate: '<b>%{{text}}</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>',
                    marker: {{ size: 7, color: 'gold', symbol: 'diamond', opacity: 0.95 }},
                }},
            ];
            // Pre-allocate a hidden highlight trace so clicking in the home table works
            fullTraces.push({{
                type: 'scatter3d', mode: 'markers',
                name: '★ Highlighted',
                x: [0], y: [0], z: [0],
                text: [''],
                hovertemplate: '<b>%{{text}}</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>',
                marker: {{ size: 16, color: '#e94560', symbol: 'circle', opacity: 1, line: {{ width: 2, color: 'white' }} }},
                visible: false,
                showlegend: false,
            }});
            _baseTraceCount = fullTraces.length;
            _highlightIdx = _baseTraceCount - 1;
            Plotly.newPlot(plotDiv, fullTraces, makeLayout(), {{ responsive: true }});
        }}

        // Fixed axis ranges — never change
        var FIXED_AXES = {{
            xRange: [12, 22], yRange: [0, 28], zRange: [0, 45],
        }};
        var axisStyle = {{
            gridcolor: '#dfe6e9', zerolinecolor: '#b2bec3',
            backgroundcolor: '#f8f9fa', showbackground: true,
            tickfont: {{ size: 11, color: '#636e72' }},
        }};

        function makeLayout(title) {{
            // Preserve the current camera position so the plot doesn't reset on updates
            var cam = (plotDiv && plotDiv.layout && plotDiv.layout.scene && plotDiv.layout.scene.camera)
                ? plotDiv.layout.scene.camera : undefined;
            var sceneObj = {{
                    xaxis: Object.assign({{ title: {{ text: '\u03b4D (Dispersion) MPa\u00b9\u2044\u00b2', font: {{ size: 14, color: '#2d3436' }} }}, range: FIXED_AXES.xRange.slice(), autorange: false }}, axisStyle),
                    yaxis: Object.assign({{ title: {{ text: '\u03b4P (Polar) MPa\u00b9\u2044\u00b2', font: {{ size: 14, color: '#2d3436' }} }}, range: FIXED_AXES.yRange.slice(), autorange: false }}, axisStyle),
                    zaxis: Object.assign({{ title: {{ text: '\u03b4H (H-bonding) MPa\u00b9\u2044\u00b2', font: {{ size: 14, color: '#2d3436' }} }}, range: FIXED_AXES.zRange.slice(), autorange: false }}, axisStyle),
                    aspectmode: 'cube',
            }};
            if (cam) sceneObj.camera = cam;
            return {{
                scene: sceneObj,
                paper_bgcolor: '#fff', plot_bgcolor: '#fff',
                margin: {{ l: 0, r: 0, t: 40, b: 0 }},
                legend: {{ x: 0.01, y: 0.99, bgcolor: 'rgba(255,255,255,0.85)', bordercolor: '#dfe6e9', borderwidth: 1, font: {{ color: '#2d3436' }} }},
                title: {{ text: title || 'Hansen Solubility Parameter Space', x: 0.5, font: {{ size: 18, color: '#2d3436' }} }},
            }};
        }}

        function addSphere(traces, tgt, sphereColor) {{
            if (!tgt.r || tgt.r <= 0) return;
            const N = 10, M = 8, x = [], y = [], z = [];
            for (let i = 0; i <= N; i++) {{
                const xr = [], yr = [], zr = [], u = (i / N) * 2 * Math.PI;
                for (let j = 0; j <= M; j++) {{
                    const v = (j / M) * Math.PI;
                    xr.push(tgt.dd + (tgt.r / 2) * Math.cos(u) * Math.sin(v));
                    yr.push(tgt.dp + tgt.r * Math.sin(u) * Math.sin(v));
                    zr.push(tgt.dh + tgt.r * Math.cos(v));
                }}
                x.push(xr); y.push(yr); z.push(zr);
            }}
            traces.push({{ type: 'surface', x, y, z, opacity: 0.12,
                colorscale: [[0, sphereColor], [1, sphereColor]],
                showscale: false, name: 'Sphere: ' + tgt.name, hoverinfo: 'name' }});
        }}

        // Track result traces layered on top of the 2 base traces
        var _baseTraceCount = 0;
        var _solventColors = [];
        var _resultTraceCount = 0;
        var _plotDimmed = false;

        function _dimBaseTraces() {{
            // Restyle the 2 base traces to be dim background dots.
            // No Plotly.react, no layout rebuild — camera stays exactly where it is.
            if (_plotDimmed) return;
            _plotDimmed = true;
            Plotly.restyle(plotDiv, {{
                'marker.size': [2, 3],
                'marker.color': ['#999', '#aa8800'],
                'marker.opacity': [0.1, 0.12],
                'hoverinfo': ['skip', 'skip'],
                'hovertemplate': [null, null],
            }}, [0, 1]);
        }}

        function _restoreBaseTraces() {{
            // Restore the 2 base traces to full interactive appearance.
            if (!_plotDimmed) return;
            _plotDimmed = false;
            Plotly.restyle(plotDiv, {{
                'marker.size': [5, 7],
                'marker.color': [_solventColors, 'gold'],
                'marker.opacity': [0.85, 0.95],
                'hoverinfo': ['all', 'all'],
                'hovertemplate': [fullTraces[0].hovertemplate, fullTraces[1].hovertemplate],
            }}, [0, 1]);
            // Re-apply common filter if active
            if (simpleMode) _updatePlotForCommonFilter();
        }}

        function updatePlotWithResults(result) {{
            if (!result || result.error) return;
            const {{ results }} = result;
            const target = result.target || (result.targets ? result.targets[0] : null);
            const parentIntent = result.parentIntent || result.intent;
            const isMulti = result.intent === 'multi_material';

            // Deactivate any open tab panel
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));

            // Dim base traces (no-op if already dimmed)
            _dimBaseTraces();

            // Remove previous result traces (everything after the base traces)
            if (_resultTraceCount > 0) {{
                var idxs = [];
                for (var i = 0; i < _resultTraceCount; i++) idxs.push(_baseTraceCount + i);
                Plotly.deleteTraces(plotDiv, idxs);
                _resultTraceCount = 0;
            }}

            const valid = results.filter(r => !r.notFound);
            const resultColors = computeResultColors(valid);
            var newTraces = [];

            if (isMulti) {{
                newTraces.push({{
                    type: 'scatter3d', mode: 'markers+text', name: 'Results',
                    x: valid.map(r => r.dd), y: valid.map(r => r.dp), z: valid.map(r => r.dh),
                    text: valid.map((r, i) => (i + 1) + '. ' + r.name),
                    textposition: 'top center', textfont: {{ size: 9, color: '#2d3436' }},
                    hovertemplate: valid.map((r, i) => {{
                        let h = '<b>' + (i+1) + '. ' + r.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}';
                        result.targets.forEach(t => {{ h += '<br>' + t.name.slice(0, 20) + ': RED=' + (r.reds[t.name] != null ? r.reds[t.name].toFixed(2) : 'N/A'); }});
                        return h + '<extra></extra>';
                    }}),
                    marker: {{ size: 10, color: resultColors, opacity: 1, line: {{ color: '#2d3436', width: 1 }} }},
                }});
                const tgtColors = ['#e94560', '#3A86FF', '#06D6A0', '#FFBE0B'];
                const sphereColors = ['rgba(233,69,96,0.2)', 'rgba(58,134,255,0.2)', 'rgba(6,214,160,0.2)', 'rgba(255,190,11,0.2)'];
                result.targets.forEach((tgt, ti) => {{
                    const c = tgtColors[ti % tgtColors.length];
                    newTraces.push({{ type: 'scatter3d', mode: 'markers+text',
                        name: (tgt.requirement === 'good' ? '✓ ' : '✗ ') + tgt.name,
                        x: [tgt.dd], y: [tgt.dp], z: [tgt.dh], text: [tgt.name],
                        textposition: 'top center', textfont: {{ size: 12, color: c }},
                        hovertemplate: '<b>' + tgt.name + '</b> (' + tgt.requirement + ')<br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<br>R₀=' + tgt.r + '<extra></extra>',
                        marker: {{ size: 14, color: c, symbol: 'diamond', opacity: 1, line: {{ color: '#2d3436', width: 2 }} }},
                    }});
                    addSphere(newTraces, tgt, sphereColors[ti % sphereColors.length]);
                }});
            }} else if (parentIntent === 'good_solvents' || parentIntent === 'bad_solvents' || parentIntent === 'polymers_for_solvent') {{
                var isReverse = parentIntent === 'polymers_for_solvent';
                newTraces.push({{
                    type: 'scatter3d', mode: 'markers+text', name: 'Results',
                    x: valid.map(r => r.dd), y: valid.map(r => r.dp), z: valid.map(r => r.dh),
                    text: valid.map((r, i) => (i + 1) + '. ' + r.name),
                    textposition: 'top center', textfont: {{ size: 9, color: '#2d3436' }},
                    hovertemplate: valid.map((r, i) =>
                        '<b>' + (i+1) + '. ' + r.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<br>Ra=' + r.ra.toFixed(2) +
                        (r.red !== null ? '<br>RED=' + r.red.toFixed(2) : '') + '<extra></extra>'),
                    marker: {{ size: 10, color: resultColors, symbol: isReverse ? 'diamond' : 'circle', opacity: 1, line: {{ color: '#2d3436', width: 1 }} }},
                }});
                newTraces.push({{ type: 'scatter3d', mode: 'markers+text', name: '★ Target: ' + target.name,
                    x: [target.dd], y: [target.dp], z: [target.dh], text: ['★ ' + target.name],
                    textposition: 'top center', textfont: {{ size: 13, color: '#e94560' }},
                    hovertemplate: '<b>★ ' + target.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}' + (target.r ? '<br>R₀=' + target.r : '') + '<extra></extra>',
                    marker: {{ size: 16, color: '#e94560', symbol: isReverse ? 'circle' : 'diamond', opacity: 1, line: {{ color: '#2d3436', width: 2 }} }},
                }});
                if (!isReverse) addSphere(newTraces, target, 'rgba(233,69,96,0.2)');
            }} else {{
                const sym = (parentIntent === 'similar_polymers') ? 'diamond' : 'circle';
                newTraces.push({{
                    type: 'scatter3d', mode: 'markers+text', name: 'Results',
                    x: valid.map(r => r.dd), y: valid.map(r => r.dp), z: valid.map(r => r.dh),
                    text: valid.map((r, i) => (i + 1) + '. ' + r.name),
                    textposition: 'top center', textfont: {{ size: 9, color: '#2d3436' }},
                    hovertemplate: valid.map((r, i) =>
                        '<b>' + (i+1) + '. ' + r.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<br>Ra=' + r.ra.toFixed(2) + '<extra></extra>'),
                    marker: {{ size: 10, color: resultColors, symbol: sym, opacity: 1, line: {{ color: '#2d3436', width: 1 }} }},
                }});
                const tsym = (parentIntent === 'similar_polymers') ? 'diamond' : 'circle';
                newTraces.push({{ type: 'scatter3d', mode: 'markers+text', name: '★ Target: ' + target.name,
                    x: [target.dd], y: [target.dp], z: [target.dh], text: ['★ ' + target.name],
                    textposition: 'top center', textfont: {{ size: 13, color: '#e94560' }},
                    hovertemplate: '<b>★ ' + target.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>',
                    marker: {{ size: 16, color: '#e94560', symbol: tsym, opacity: 1, line: {{ color: '#2d3436', width: 2 }} }},
                }});
            }}

            // Pre-allocate a hidden highlight trace so highlightInPlot never needs addTraces
            newTraces.push({{
                type: 'scatter3d', mode: 'markers+text', name: '★ Highlighted',
                x: [0], y: [0], z: [0], text: [''], visible: false,
                textposition: 'top center', textfont: {{ size: 13, color: '#FFD700' }},
                hovertemplate: '<extra></extra>',
                marker: {{ size: 18, color: '#FFD700', symbol: 'circle', opacity: 1, line: {{ color: '#2d3436', width: 2 }} }},
            }});

            // Add only the new result traces (base traces are untouched)
            _resultTraceCount = newTraces.length;
            _highlightIdx = _baseTraceCount + newTraces.length - 1; // last trace = highlight
            Plotly.addTraces(plotDiv, newTraces);
            var title = isMulti ? 'Multi-Material Search' : 'Search Results — ' + target.name;
            Plotly.relayout(plotDiv, {{ 'title.text': title }});
        }}

        function resetPlot() {{
            // Remove any result/highlight traces added by search
            if (_resultTraceCount > 0) {{
                var idxs = [];
                for (var i = 0; i < _resultTraceCount; i++) idxs.push(_baseTraceCount + i);
                Plotly.deleteTraces(plotDiv, idxs);
                _resultTraceCount = 0;
            }}
            // Restore highlight index to the pre-allocated base highlight trace and hide it
            _highlightIdx = _baseTraceCount - 1;
            Plotly.restyle(plotDiv, {{ visible: false }}, [_highlightIdx]);
            // Restore base traces to full appearance
            _restoreBaseTraces();
            Plotly.relayout(plotDiv, {{ 'title.text': 'Hansen Solubility Parameter Space' }});
        }}

        // ===================== HIGHLIGHT IN PLOT =====================
        var _highlightIdx = -1; // index of the pre-allocated highlight trace
        function highlightInPlot(encodedName) {{
            const name = decodeURIComponent(encodedName);
            let mat = SOLVENTS.find(s => s.name === name);
            let sym = 'circle';
            if (!mat) {{ mat = POLYMERS.find(p => p.name === name); sym = 'diamond'; }}
            if (!mat || _highlightIdx < 0) return;
            // Restyle the pre-allocated highlight trace — no addTraces/deleteTraces,
            // no scene rebuild, camera stays exactly where it is.
            Plotly.restyle(plotDiv, {{
                x: [[mat.dd]], y: [[mat.dp]], z: [[mat.dh]],
                text: [['★ ' + mat.name]],
                hovertemplate: ['<b>' + mat.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>'],
                'marker.symbol': sym,
                visible: true,
            }}, [_highlightIdx]);
            selectInTable(name);
        }}

        function selectInTable(name) {{
            // If the home panel is visible, switch tabs if needed so the material is in view
            var homePanel = document.getElementById('home-panel');
            if (homePanel && homePanel.style.display !== 'none') {{
                var isSolvent = SOLVENTS.some(function(s) {{ return s.name === name; }});
                var isPolymer = !isSolvent && POLYMERS.some(function(p) {{ return p.name === name; }});
                if (isSolvent && homeTab !== 'solvents') {{
                    switchHomeTab('solvents');
                }} else if (isPolymer && homeTab !== 'polymers') {{
                    switchHomeTab('polymers');
                }}
            }}
            // Highlight in whichever table is visible: results (chat-panel) or home table
            var containers = [document.getElementById('chat-panel'), homePanel];
            for (var ci = 0; ci < containers.length; ci++) {{
                var c = containers[ci];
                if (!c || c.style.display === 'none' || !c.classList.contains('visible') && ci === 0) continue;
                var rows = c.querySelectorAll('tr[data-name]');
                if (!rows.length) continue;
                rows.forEach(function(r) {{ r.style.background = ''; }});
                for (var i = 0; i < rows.length; i++) {{
                    if (rows[i].getAttribute('data-name') === name) {{
                        rows[i].style.background = '#fff3cd';
                        rows[i].scrollIntoView({{ block: 'center', behavior: 'smooth' }});
                        return;
                    }}
                }}
            }}
        }}

        // ===================== HOME PANEL (all materials) =====================
        var homeTab = 'solvents';
        var homeFilterText = '';

        function buildHomeTable() {{
            var thead = document.getElementById('home-thead');
            var tbody = document.getElementById('home-tbody');
            var tbl = document.getElementById('home-table');
            var headerHtml, rowsHtml;

            var colTips = {{
                'CAS #': 'CAS Registry Number \u2014 unique identifier for chemical substances',
                '&delta;D (MPa<sup>\u00bd</sup>)': 'Dispersion \u2014 van der Waals / London dispersion forces (MPa\u00bd)',
                '&delta;P (MPa<sup>\u00bd</sup>)': 'Polarity \u2014 dipole-dipole intermolecular forces (MPa\u00bd)',
                '&delta;H (MPa<sup>\u00bd</sup>)': 'Hydrogen bonding \u2014 hydrogen bond donor/acceptor capability (MPa\u00bd)',
                'MW (g/mol)': 'Molecular weight (g/mol)',
                'BP (&deg;C)': 'Boiling point in degrees Celsius',
                'Ra (MPa<sup>\u00bd</sup>)': 'HSP distance between solvent and polymer in 3D Hansen space (MPa\u00bd)',
                'R&#8320; (MPa<sup>\u00bd</sup>)': 'Interaction radius of the polymer solubility sphere (MPa\u00bd)',
                'RED': 'Relative Energy Difference = Ra/R\u2080. RED &lt; 1 = compatible, RED &gt; 1 = incompatible'
            }};
            function thWithTip(label, idx) {{
                var tip = colTips[label] || '';
                return '<th onclick="sortResultsTable(this.closest(\\x27table\\x27),' + idx + ')" style="cursor:pointer"' + (tip ? ' title="' + tip + '"' : '') + '>' + label + '</th>';
            }}

            // Set fixed colgroup for consistent column widths
            var existingCg = tbl.querySelector('colgroup');
            if (existingCg) existingCg.remove();
            var cg = document.createElement('colgroup');

            if (homeTab === 'solvents') {{
                // Name, CAS #, δD, δP, δH, MW, BP, Category, Source
                var solWidths = getWidths('solvents');
                solWidths.forEach(function(w) {{
                    var col = document.createElement('col');
                    col.style.width = w;
                    cg.appendChild(col);
                }});
                tbl.insertBefore(cg, thead);
                headerHtml = '<tr>';
                ['Name','CAS #','&delta;D (MPa<sup>\u00bd</sup>)','&delta;P (MPa<sup>\u00bd</sup>)','&delta;H (MPa<sup>\u00bd</sup>)','MW (g/mol)','BP (&deg;C)','Category','Source'].forEach(function(label, i) {{
                    headerHtml += thWithTip(label, i);
                }});
                headerHtml += '</tr>';
                var filtered = SOLVENTS;
                if (simpleMode) {{
                    filtered = filtered.filter(function(s) {{ return s.common; }});
                }}
                if (homeFilterText) {{
                    var q = homeFilterText.toLowerCase();
                    filtered = filtered.filter(function(s) {{ return s.name.toLowerCase().indexOf(q) !== -1 || (s.cas && s.cas.indexOf(q) !== -1) || (s.src && s.src.toLowerCase().indexOf(q) !== -1); }});
                }}
                document.getElementById('tab-solvents').textContent = 'Solvents (' + filtered.length + ')';
                rowsHtml = '';
                for (var i = 0; i < filtered.length; i++) {{
                    var s = filtered[i];
                    var catColor = CAT_COLORS[s.cat] || '#888';
                    function lnk(val, url) {{ if (val == null || val === '') return ''; var v = (typeof val === 'number') ? val.toFixed(1) : val; return url ? '<a href="' + url + '" target="_blank" rel="noopener" style="color:#0984e3;text-decoration:none">' + v + '</a>' : v; }}
                    rowsHtml += '<tr data-name="' + s.name.replace(/"/g, '&quot;') + '" onclick="highlightInPlot(\\x27' + encodeURIComponent(s.name) + '\\x27)" style="cursor:pointer;border-left:3px solid ' + catColor + '">';
                    rowsHtml += '<td><span class="hoverable-name" onmouseenter="showStructure(event,\\x27' + encodeURIComponent(s.name) + '\\x27)" onmouseleave="hideStructure()">' + s.name + '</span></td>';
                    rowsHtml += '<td>' + (s.cas || '') + '</td>';
                    rowsHtml += '<td>' + lnk(s.dd, s.srcUrl) + '</td>';
                    rowsHtml += '<td>' + lnk(s.dp, s.srcUrl) + '</td>';
                    rowsHtml += '<td>' + lnk(s.dh, s.srcUrl) + '</td>';
                    rowsHtml += '<td>' + lnk(s.mw, s.mwSrc) + '</td>';
                    rowsHtml += '<td>' + (s.bp != null ? lnk(s.bp, s.bpSrc) : '') + '</td>';
                    rowsHtml += '<td style="color:' + catColor + '">' + (s.cat || '') + '</td>';
                    rowsHtml += '<td>' + ((s.src && s.srcUrl) ? '<a href="' + s.srcUrl + '" target="_blank" rel="noopener" style="color:#0984e3;text-decoration:none">' + s.src + '</a>' : (s.src || '')) + '</td>';
                    rowsHtml += '</tr>';
                }}
            }} else {{
                // Name, CAS, δD, δP, δH, R₀, Type, Source
                var polyWidths = getWidths('polymers');
                polyWidths.forEach(function(w) {{
                    var col = document.createElement('col');
                    col.style.width = w;
                    cg.appendChild(col);
                }});
                tbl.insertBefore(cg, thead);
                headerHtml = '<tr>';
                ['Name','CAS #','&delta;D (MPa<sup>\u00bd</sup>)','&delta;P (MPa<sup>\u00bd</sup>)','&delta;H (MPa<sup>\u00bd</sup>)','R&#8320; (MPa<sup>\u00bd</sup>)','Type','Source'].forEach(function(label, i) {{
                    headerHtml += thWithTip(label, i);
                }});
                headerHtml += '</tr>';
                var filtered = POLYMERS;
                if (simpleMode) {{
                    filtered = filtered.filter(function(p) {{ return p.common; }});
                }}
                if (homeFilterText) {{
                    var q = homeFilterText.toLowerCase();
                    filtered = filtered.filter(function(p) {{ return p.name.toLowerCase().indexOf(q) !== -1 || (p.cas && p.cas.indexOf(q) !== -1) || (p.src && p.src.toLowerCase().indexOf(q) !== -1); }});
                }}
                document.getElementById('tab-polymers').textContent = 'Polymers (' + filtered.length + ')';
                rowsHtml = '';
                for (var i = 0; i < filtered.length; i++) {{
                    var p = filtered[i];
                    function lnk(val, url) {{ if (val == null || val === '') return ''; var v = (typeof val === 'number') ? val.toFixed(1) : val; return url ? '<a href="' + url + '" target="_blank" rel="noopener" style="color:#0984e3;text-decoration:none">' + v + '</a>' : v; }}
                    rowsHtml += '<tr data-name="' + p.name.replace(/"/g, '&quot;') + '" onclick="highlightInPlot(\\x27' + encodeURIComponent(p.name) + '\\x27)" style="cursor:pointer">';
                    rowsHtml += '<td><span class="hoverable-name">' + p.name + '</span></td>';
                    rowsHtml += '<td>' + (p.cas || '') + '</td>';
                    rowsHtml += '<td>' + lnk(p.dd, p.srcUrl) + '</td>';
                    rowsHtml += '<td>' + lnk(p.dp, p.srcUrl) + '</td>';
                    rowsHtml += '<td>' + lnk(p.dh, p.srcUrl) + '</td>';
                    rowsHtml += '<td>' + (p.r || '') + '</td>';
                    rowsHtml += '<td>' + (p.type || '') + '</td>';
                    rowsHtml += '<td>' + ((p.src && p.srcUrl) ? '<a href="' + p.srcUrl + '" target="_blank" rel="noopener" style="color:#0984e3;text-decoration:none">' + p.src + '</a>' : (p.src || '')) + '</td>';
                    rowsHtml += '</tr>';
                }}
            }}

            thead.innerHTML = headerHtml;
            tbody.innerHTML = rowsHtml;

            // Update the inactive tab count too
            if (homeTab === 'solvents') {{
                var pf = POLYMERS;
                if (simpleMode) pf = pf.filter(function(p) {{ return p.common; }});
                if (homeFilterText) {{ var q = homeFilterText.toLowerCase(); pf = pf.filter(function(p) {{ return p.name.toLowerCase().indexOf(q) !== -1 || (p.cas && p.cas.indexOf(q) !== -1) || (p.src && p.src.toLowerCase().indexOf(q) !== -1); }}); }}
                document.getElementById('tab-polymers').textContent = 'Polymers (' + pf.length + ')';
            }} else {{
                var sf = SOLVENTS;
                if (simpleMode) sf = sf.filter(function(s) {{ return s.common; }});
                if (homeFilterText) {{ var q = homeFilterText.toLowerCase(); sf = sf.filter(function(s) {{ return s.name.toLowerCase().indexOf(q) !== -1 || (s.cas && s.cas.indexOf(q) !== -1) || (s.src && s.src.toLowerCase().indexOf(q) !== -1); }}); }}
                document.getElementById('tab-solvents').textContent = 'Solvents (' + sf.length + ')';
            }}
        }}

        function switchHomeTab(tab) {{
            // Capture current widths before switching if locked
            if (columnWidthsLocked) {{
                var curTbl = document.getElementById('home-table');
                var captured = captureCurrentWidths(curTbl, homeTab);
                if (captured) {{
                    lockedWidths[homeTab] = captured;
                    saveLockedWidths();
                }}
            }}
            homeTab = tab;
            document.querySelectorAll('.home-tab').forEach(function(t) {{ t.classList.remove('active'); }});
            var btns = document.querySelectorAll('.home-tab');
            if (tab === 'solvents' && btns[0]) btns[0].classList.add('active');
            if (tab === 'polymers' && btns[1]) btns[1].classList.add('active');
            buildHomeTable();
        }}

        function filterHomeTable(val) {{
            homeFilterText = val.trim();
            buildHomeTable();
        }}

        function showHomePanel() {{
            var hp = document.getElementById('home-panel');
            if (hp) hp.style.display = '';
        }}

        function hideHomePanel() {{
            var hp = document.getElementById('home-panel');
            if (hp) hp.style.display = 'none';
        }}

        // ===================== STRUCTURE TOOLTIP =====================
        const structCache = {{}};
        const tooltip = {{ el: null, img: null, nameEl: null }};

        function showStructure(event, encodedName) {{
            const name = decodeURIComponent(encodedName);
            if (!tooltip.el) {{
                tooltip.el = document.getElementById('struct-tooltip');
                tooltip.img = document.getElementById('struct-img');
                tooltip.nameEl = document.getElementById('struct-name');
            }}
            tooltip.nameEl.textContent = name;
            tooltip.el.style.display = 'block';
            positionTooltip(event);
            if (structCache[name] === 'error') {{ tooltip.el.style.display = 'none'; return; }}
            const solvent = SOLVENTS.find(s => s.name === name);
            const casNum = (solvent && solvent.cas) ? solvent.cas : null;
            let url = casNum
                ? 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/' + encodeURIComponent(casNum) + '/PNG?image_size=200x200'
                : 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/' + encodeURIComponent(name) + '/PNG?image_size=200x200';
            if (structCache[name]) {{
                tooltip.img.src = structCache[name];
                tooltip.el.classList.remove('loading');
            }} else {{
                tooltip.el.classList.add('loading');
                tooltip.img.src = url;
                tooltip.img.onload = function() {{ structCache[name] = url; tooltip.el.classList.remove('loading'); }};
                tooltip.img.onerror = function() {{ structCache[name] = 'error'; tooltip.el.style.display = 'none'; }};
            }}
        }}

        function hideStructure() {{
            if (tooltip.el) tooltip.el.style.display = 'none';
        }}

        function positionTooltip(event) {{
            if (!tooltip.el) return;
            let x = event.clientX + 15;
            let y = event.clientY - 100;
            if (x + 220 > window.innerWidth) x = event.clientX - 225;
            if (y < 10) y = 10;
            tooltip.el.style.left = x + 'px';
            tooltip.el.style.top = y + 'px';
        }}

        var _mmRaf = 0;
        document.addEventListener('mousemove', function(e) {{
            if (tooltip.el && tooltip.el.style.display === 'block') {{
                if (_mmRaf) return;
                _mmRaf = requestAnimationFrame(function() {{ _mmRaf = 0; positionTooltip(e); }});
            }}
        }});

        // ===================== UI GLUE =====================
        function runSearch() {{
            const input = document.getElementById('nl-search');
            const q = input.value.trim();
            if (!q) return;
            lastSearchQuery = q;
            input.value = '';
            const parsed = parseQuery(q);
            const result = executeSearch(parsed);
            const html = renderResultsHTML(result);
            showResults(html);
            // Defer the expensive Plotly update to the next frame so the table
            // paints immediately and the UI feels responsive.
            if (!result.error) requestAnimationFrame(function() {{ updatePlotWithResults(result); }});
        }}

        function exampleSearch(text) {{
            document.getElementById('nl-search').value = text;
            runSearch();
        }}

        function clearChat() {{
            chatContext = null;
            chatMessages = [];
            const panel = document.getElementById('chat-panel');
            panel.innerHTML = '';
            panel.classList.remove('visible');
            showHomePanel();
            resetPlot();
        }}

        function goHome() {{
            clearChat();
            document.getElementById('nl-search').value = '';
            document.querySelectorAll('.panel').forEach(function(p) {{ p.classList.remove('active'); }});
            document.querySelectorAll('.tab').forEach(function(t) {{ t.classList.remove('active'); }});
            window.dispatchEvent(new Event('resize'));
        }}


        // ===================== INIT =====================
        document.addEventListener('DOMContentLoaded', function() {{
            loadLockedWidths();
            buildFullPlot();
            buildHomeTable();
            plotDiv.on('plotly_click', function(data) {{
                if (!data || !data.points || !data.points.length) return;
                var pt = data.points[0];
                var name = '';
                if (pt.text) {{
                    name = pt.text.replace(/^★\s*/, '').replace(/<br>.*/, '').replace(/^\d+\.\s*/, '');
                }}
                if (name) {{
                    highlightInPlot(encodeURIComponent(name));
                    selectInTable(name);
                }}
            }});
        }});
    </script>
</body>
</html>"""

output_path = os.path.join(os.path.dirname(__file__), "materialism.html")
with open(output_path, "w") as f:
    f.write(full_html)

print(f"Generated: {output_path}")
print(f"File size: {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")
print(f"Contains: {len(solvents)} solvents, {len(poly_data)} polymers")

# ===================== DATABASE PAGE =====================
# Load full data for database page (all CSV columns)
db_solvents = []
with open(CHEM_CSV) as f:
    for row in csv.DictReader(f):
        dd = row.get("delta_d", "").strip()
        dp = row.get("delta_p", "").strip()
        dh = row.get("delta_h", "").strip()
        if not (dd and dp and dh):
            continue
        if row.get("hidden", "").strip().lower() in ("1", "true", "yes"):
            continue
        src_key = row.get("source", "").strip()
        db_solvents.append({
            "name": row["name"].strip(),
            "cas": row.get("cas_number", "").strip(),
            "smiles": row.get("smiles", "").strip(),
            "formula": row.get("molecular_formula", "").strip(),
            "dd": dd, "dp": dp, "dh": dh,
            "mw": row.get("molecular_weight", "").strip(),
            "bp": row.get("boiling_point", "").strip(),
            "density": row.get("density", "").strip(),
            "mv": row.get("molar_volume", "").strip(),
            "cat": row.get("category", "other").strip() or "other",
            "ghs": row.get("ghs_hazard", "").strip(),
            "src": SOURCE_NAMES.get(src_key, src_key),
            "srcUrl": row.get("source_url", "").strip(),
        })
db_polymers = []
with open(POLY_CSV) as f:
    for row in csv.DictReader(f):
        dd = row.get("delta_d", "").strip()
        dp = row.get("delta_p", "").strip()
        dh = row.get("delta_h", "").strip()
        if not (dd and dp and dh):
            continue
        if row.get("hidden", "").strip().lower() in ("1", "true", "yes"):
            continue
        src_key = row.get("source", "").strip()
        db_polymers.append({
            "name": row["name"].strip(),
            "cas": row.get("cas_number", "").strip(),
            "dd": dd, "dp": dp, "dh": dh,
            "r": row.get("radius", "").strip(),
            "type": row.get("type", "").strip(),
            "src": SOURCE_NAMES.get(src_key, src_key),
            "srcUrl": row.get("source_url", "").strip(),
        })

db_solvents_json = json.dumps(db_solvents)
db_polymers_json = json.dumps(db_polymers)

database_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Materialism — Database</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: #f5f6fa; color: #2d3436; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
.header {{ background: #fff; padding: 15px 30px; display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #dfe6e9; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
.header h1 {{ font-size: 1.5rem; color: #e94560; }}
.header h1 a {{ color: #e94560; text-decoration: none; }}
.header .nav-links {{ color: #636e72; font-size: 0.9rem; display: flex; align-items: center; gap: 12px; }}
.header .nav-links a {{ color: #636e72; text-decoration: none; border-bottom: 1px dotted #b2bec3; cursor: pointer; }}
.toolbar {{ background: #fff; padding: 10px 30px; display: flex; align-items: center; gap: 16px; border-bottom: 1px solid #dfe6e9; }}
.toolbar input {{ padding: 8px 12px; border: 1px solid #dfe6e9; border-radius: 4px; font-size: 0.85rem; width: 220px; }}
.toolbar input:focus {{ outline: none; border-color: #e94560; }}
.db-tabs {{ display: flex; gap: 0; }}
.db-tab {{ padding: 8px 18px; cursor: pointer; border: none; background: transparent; color: #636e72; font-size: 0.85rem; transition: all 0.2s; }}
.db-tab:hover {{ color: #2d3436; background: #f5f6fa; }}
.db-tab.active {{ color: #e94560; border-bottom: 2px solid #e94560; background: #fff; }}
.lock-btn {{
    margin-left: auto; cursor: pointer; background: none; border: 1px solid #dfe6e9;
    border-radius: 4px; padding: 5px 12px; display: flex; align-items: center; gap: 6px;
    color: #636e72; font-size: 0.8rem; transition: all 0.2s;
}}
.lock-btn:hover {{ background: #f5f6fa; border-color: #b2bec3; }}
.lock-btn.unlocked {{ color: #e94560; border-color: #e94560; background: #fff5f7; }}
.lock-btn svg {{ width: 16px; height: 16px; fill: currentColor; }}
.table-wrap {{ overflow: auto; height: calc(100vh - 130px); }}
table {{ width: max-content; min-width: 100%; border-collapse: collapse; font-size: 0.8rem; }}
th {{
    background: #f0f2f5; color: #e94560; padding: 8px 10px; text-align: left;
    font-weight: 600; position: sticky; top: 0; z-index: 1;
    border-bottom: 2px solid #dfe6e9; white-space: nowrap; cursor: pointer;
}}
th:hover {{ background: #e8eaed; }}
th.sort-asc::after {{ content: ' ▲'; font-size: 0.7em; color: #e94560; }}
th.sort-desc::after {{ content: ' ▼'; font-size: 0.7em; color: #e94560; }}
td {{ padding: 6px 10px; border-bottom: 1px solid #eee; white-space: nowrap; max-width: 300px; overflow: hidden; text-overflow: ellipsis; }}
tr:hover {{ background: #f8f9fa; }}
td a {{ color: #0984e3; text-decoration: none; }}
td a:hover {{ text-decoration: underline; }}
td input {{
    width: 100%; border: none; background: transparent; font: inherit; color: inherit;
    padding: 2px 4px; outline: none;
}}
td input:focus {{ background: #fff3cd; border-radius: 2px; }}
td.editing {{ padding: 2px 4px; background: #fffcf0; }}
.edit-count {{ font-size: 0.8rem; color: #e94560; font-weight: 600; }}
.cas-link {{ color: #0984e3; text-decoration: none; }}
.cas-link:hover {{ text-decoration: underline; }}
.save-indicator {{ display: none; color: #00b894; font-size: 0.8rem; font-weight: 600; }}
.save-indicator.visible {{ display: inline; }}
</style>
</head>
<body>
<div class="header">
    <h1><a href="materialism.html">Materialism</a> — Database</h1>
    <div class="nav-links">
        <a href="cas_review.html">Crosslink</a>
        <a href="materialism.html">Search</a>
    </div>
</div>
<div class="toolbar">
    <div class="db-tabs">
        <button id="tab-solv" class="db-tab active" onclick="switchTab('solvents')">Solvents ({len(db_solvents)})</button>
        <button id="tab-poly" class="db-tab" onclick="switchTab('polymers')">Polymers ({len(db_polymers)})</button>
    </div>
    <input type="text" id="db-filter" placeholder="Filter by name or CAS..." oninput="renderTable()">
    <button id="lock-btn" class="lock-btn" onclick="toggleLock()" title="Click to unlock editing">
        <svg id="icon-locked" viewBox="0 0 24 24"><path d="M12 17a2 2 0 0 0 2-2 2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2m6-9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2h1V6a5 5 0 0 1 5-5 5 5 0 0 1 5 5v2h1m-6-5a3 3 0 0 0-3 3v2h6V6a3 3 0 0 0-3-3z"/></svg>
        <svg id="icon-unlocked" viewBox="0 0 24 24" style="display:none"><path d="M12 17a2 2 0 0 0 2-2 2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2m6-9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2h9V6a3 3 0 0 0-3-3 3 3 0 0 0-3 3H7a5 5 0 0 1 5-5 5 5 0 0 1 5 5v2h1z"/></svg>
        <span id="lock-text">Locked</span>
    </button>
    <span class="edit-count" id="edit-count"></span>
    <span class="save-indicator" id="save-ind">Saved</span>
</div>
<div class="table-wrap">
    <table id="db-table">
        <thead id="db-thead"></thead>
        <tbody id="db-tbody"></tbody>
    </table>
</div>
<script>
var SOLVENTS = {db_solvents_json};
var POLYMERS = {db_polymers_json};

var SOLV_COLS = [
    {{key:'name', label:'Name', w:'200px'}},
    {{key:'cas', label:'CAS #', w:'110px'}},
    {{key:'formula', label:'Formula', w:'110px'}},
    {{key:'smiles', label:'SMILES', w:'160px'}},
    {{key:'dd', label:'\\u03b4D (MPa\\u00bd)', w:'78px', tip:'Dispersion parameter'}},
    {{key:'dp', label:'\\u03b4P (MPa\\u00bd)', w:'78px', tip:'Polarity parameter'}},
    {{key:'dh', label:'\\u03b4H (MPa\\u00bd)', w:'78px', tip:'Hydrogen bonding parameter'}},
    {{key:'mw', label:'MW (g/mol)', w:'80px', tip:'Molecular weight'}},
    {{key:'bp', label:'BP (\\u00b0C)', w:'70px', tip:'Boiling point'}},
    {{key:'density', label:'Density', w:'70px', tip:'Density (g/mL)'}},
    {{key:'mv', label:'V\\u2098 (cm\\u00b3/mol)', w:'90px', tip:'Molar volume'}},
    {{key:'cat', label:'Category', w:'100px'}},
    {{key:'ghs', label:'GHS Hazard', w:'120px'}},
    {{key:'src', label:'Source', w:'140px'}},
];
var POLY_COLS = [
    {{key:'name', label:'Name', w:'250px'}},
    {{key:'cas', label:'CAS #', w:'110px'}},
    {{key:'dd', label:'\\u03b4D (MPa\\u00bd)', w:'78px', tip:'Dispersion parameter'}},
    {{key:'dp', label:'\\u03b4P (MPa\\u00bd)', w:'78px', tip:'Polarity parameter'}},
    {{key:'dh', label:'\\u03b4H (MPa\\u00bd)', w:'78px', tip:'Hydrogen bonding parameter'}},
    {{key:'r', label:'R\\u2080 (MPa\\u00bd)', w:'70px', tip:'Interaction radius'}},
    {{key:'type', label:'Type', w:'120px'}},
    {{key:'src', label:'Source', w:'140px'}},
];

var activeTab = 'solvents';
var editing = false;
var edits = {{}};  // key: "type:index:field" -> value
var sortCol = null, sortAsc = true;

function loadEdits() {{
    try {{
        var saved = localStorage.getItem('materialism_db_edits');
        if (saved) edits = JSON.parse(saved);
    }} catch(e) {{}}
    updateEditCount();
}}

function saveEdits() {{
    try {{
        localStorage.setItem('materialism_db_edits', JSON.stringify(edits));
    }} catch(e) {{}}
    updateEditCount();
    var ind = document.getElementById('save-ind');
    ind.classList.add('visible');
    setTimeout(function() {{ ind.classList.remove('visible'); }}, 1500);
}}

function updateEditCount() {{
    var n = Object.keys(edits).length;
    var el = document.getElementById('edit-count');
    el.textContent = n ? n + ' edit' + (n > 1 ? 's' : '') : '';
}}

function getVal(type, idx, field) {{
    var k = type + ':' + idx + ':' + field;
    if (edits.hasOwnProperty(k)) return edits[k];
    var arr = type === 'solvents' ? SOLVENTS : POLYMERS;
    return arr[idx][field] || '';
}}

function setVal(type, idx, field, val) {{
    var k = type + ':' + idx + ':' + field;
    var arr = type === 'solvents' ? SOLVENTS : POLYMERS;
    var orig = arr[idx][field] || '';
    if (val === orig) {{
        delete edits[k];
    }} else {{
        edits[k] = val;
    }}
    saveEdits();
}}

function toggleLock() {{
    editing = !editing;
    var btn = document.getElementById('lock-btn');
    var iconLocked = document.getElementById('icon-locked');
    var iconUnlocked = document.getElementById('icon-unlocked');
    var lockText = document.getElementById('lock-text');
    if (editing) {{
        btn.classList.add('unlocked');
        btn.title = 'Click to lock and save';
        iconLocked.style.display = 'none';
        iconUnlocked.style.display = '';
        lockText.textContent = 'Editing';
    }} else {{
        btn.classList.remove('unlocked');
        btn.title = 'Click to unlock editing';
        iconLocked.style.display = '';
        iconUnlocked.style.display = 'none';
        lockText.textContent = 'Locked';
    }}
    renderTable();
}}

function switchTab(tab) {{
    activeTab = tab;
    sortCol = null;
    document.querySelectorAll('.db-tab').forEach(function(t) {{ t.classList.remove('active'); }});
    if (tab === 'solvents') document.getElementById('tab-solv').classList.add('active');
    else document.getElementById('tab-poly').classList.add('active');
    renderTable();
}}

function sortBy(col) {{
    if (sortCol === col) sortAsc = !sortAsc;
    else {{ sortCol = col; sortAsc = true; }}
    renderTable();
}}

function renderTable() {{
    var cols = activeTab === 'solvents' ? SOLV_COLS : POLY_COLS;
    var data = activeTab === 'solvents' ? SOLVENTS : POLYMERS;
    var filter = document.getElementById('db-filter').value.toLowerCase().trim();

    // Build index array for filtering
    var indices = [];
    for (var i = 0; i < data.length; i++) {{
        if (filter) {{
            var row = data[i];
            var name = getVal(activeTab, i, 'name').toLowerCase();
            var cas = getVal(activeTab, i, 'cas').toLowerCase();
            if (name.indexOf(filter) === -1 && cas.indexOf(filter) === -1) continue;
        }}
        indices.push(i);
    }}

    // Sort
    if (sortCol !== null) {{
        var key = cols[sortCol].key;
        indices.sort(function(a, b) {{
            var va = getVal(activeTab, a, key);
            var vb = getVal(activeTab, b, key);
            var na = parseFloat(va), nb = parseFloat(vb);
            if (!isNaN(na) && !isNaN(nb)) return sortAsc ? na - nb : nb - na;
            return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
        }});
    }}

    // Header
    var hdr = '<tr>';
    for (var ci = 0; ci < cols.length; ci++) {{
        var c = cols[ci];
        var cls = '';
        if (sortCol === ci) cls = sortAsc ? ' class="sort-asc"' : ' class="sort-desc"';
        hdr += '<th' + cls + ' style="width:' + c.w + '"' + (c.tip ? ' title="' + c.tip + '"' : '') + ' onclick="sortBy(' + ci + ')">' + c.label + '</th>';
    }}
    hdr += '</tr>';
    document.getElementById('db-thead').innerHTML = hdr;

    // Body
    var html = '';
    for (var ri = 0; ri < indices.length; ri++) {{
        var idx = indices[ri];
        html += '<tr>';
        for (var ci = 0; ci < cols.length; ci++) {{
            var c = cols[ci];
            var val = getVal(activeTab, idx, c.key);
            var editKey = activeTab + ':' + idx + ':' + c.key;
            var isEdited = edits.hasOwnProperty(editKey);

            if (editing) {{
                html += '<td class="editing"' + (isEdited ? ' style="background:#e8f8f0"' : '') + '>';
                html += '<input type="text" value="' + String(val).replace(/"/g, '&quot;') + '" onchange="setVal(\\x27' + activeTab + '\\x27,' + idx + ',\\x27' + c.key + '\\x27,this.value)">';
                html += '</td>';
            }} else {{
                var display = val;
                // CAS link
                if (c.key === 'cas' && val) {{
                    display = '<a class="cas-link" href="https://commonchemistry.cas.org/detail?cas_rn=' + encodeURIComponent(val) + '" target="_blank" rel="noopener">' + val + '</a>';
                }}
                // Source link
                if (c.key === 'src') {{
                    var srcUrl = activeTab === 'solvents' ? SOLVENTS[idx].srcUrl : POLYMERS[idx].srcUrl;
                    if (srcUrl) display = '<a href="' + srcUrl + '" target="_blank" rel="noopener">' + val + '</a>';
                }}
                html += '<td' + (isEdited ? ' style="background:#e8f8f0"' : '') + '>' + display + '</td>';
            }}
        }}
        html += '</tr>';
    }}
    document.getElementById('db-tbody').innerHTML = html;
}}

loadEdits();
renderTable();
</script>
</body>
</html>"""

db_output_path = os.path.join(os.path.dirname(__file__), "database.html")
with open(db_output_path, "w") as f:
    f.write(database_html)
print(f"Generated: {db_output_path}")
print(f"Database page: {len(db_solvents)} solvents, {len(db_polymers)} polymers")
