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
        solvents.append({
            "name": row["name"].strip(),
            "cas": row.get("cas_number", "").strip(),
            "dd": float(dd), "dp": float(dp), "dh": float(dh),
            "mw": float(mw_val) if mw_val else None,
            "bp": float(bp_val) if bp_val else None,
            "cat": row.get("category", "other").strip() or "other",
            "smiles": row.get("smiles", "").strip(),
            "src": SOURCE_NAMES.get(src_key, src_key),
            "srcUrl": src_url,
            "mwSrc": mw_src if mw_val else "",
            "bpSrc": bp_src if bp_val else "",
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
        poly_data.append({
            "name": row["name"].strip(),
            "dd": float(dd), "dp": float(dp), "dh": float(dh),
            "r": float(r_val) if r_val else None,
            "type": row.get("type", "").strip(),
            "cas": row.get("cas_number", "").strip(),
            "src": SOURCE_NAMES.get(src_key, src_key),
            "srcUrl": src_url,
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

# Build static HTML data tables (for Solvent/Polymer Database tabs)
table_rows = ""
for s in sorted(solvents, key=lambda x: x["name"]):
    def _link(val, url):
        if val is None or val == "":
            return ""
        v = str(val)
        if url:
            return f'<a href="{url}" target="_blank" rel="noopener" style="color:#0984e3;text-decoration:none" title="Source">{v}</a>'
        return v
    table_rows += f"""<tr>
        <td>{s['name']}</td><td>{s['cas']}</td>
        <td>{_link(s['dd'], s['srcUrl'])}</td><td>{_link(s['dp'], s['srcUrl'])}</td><td>{_link(s['dh'], s['srcUrl'])}</td>
        <td>{_link(s['mw'], s['mwSrc'])}</td><td>{_link(s['bp'], s['bpSrc'])}</td>
        <td>{s['cat']}</td>
    </tr>"""

polymer_rows = ""
for p in sorted(poly_data, key=lambda x: x["name"]):
    def _link(val, url):
        if val is None or val == "":
            return ""
        v = str(val)
        if url:
            return f'<a href="{url}" target="_blank" rel="noopener" style="color:#0984e3;text-decoration:none" title="Source">{v}</a>'
        return v
    polymer_rows += f"""<tr>
        <td>{p['name']}</td><td>{p['cas']}</td>
        <td>{_link(p['dd'], p['srcUrl'])}</td><td>{_link(p['dp'], p['srcUrl'])}</td><td>{_link(p['dh'], p['srcUrl'])}</td>
        <td>{_link(p['r'], p['srcUrl'])}</td><td>{p['type']}</td>
    </tr>"""

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

        .chat-context {{
            display: inline-block; background: #f0f2f5; color: #636e72; padding: 2px 8px;
            border-radius: 4px; font-size: 0.75rem; margin-bottom: 8px;
        }}

        /* --- Results Table --- */
        .results-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 8px; }}
        .results-table th {{
            background: #f0f2f5; color: #e94560; padding: 8px 10px;
            text-align: left; font-weight: 600; position: static; border-bottom: 2px solid #dfe6e9;
        }}
        .results-table td {{ padding: 8px 10px; border-bottom: 1px solid #eee; position: relative; }}
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
        <div class="stats"><a href="solvents.html" style="color:#636e72;text-decoration:none;border-bottom:1px dotted #b2bec3">{len(solvents)} solvents</a> &middot; <a href="polymers.html" style="color:#636e72;text-decoration:none;border-bottom:1px dotted #b2bec3">{len(poly_data)} polymers</a> &middot; Hansen Solubility Parameters</div>
    </div>

    <div class="search-bar">
        <input type="text" id="nl-search" placeholder="Ask anything — e.g. &quot;good solvents for polystyrene&quot; then follow up with &quot;what about NMP?&quot;"
               onkeydown="if(event.key==='Enter')runSearch()">
        <button onclick="runSearch()">Search</button>
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
            <span onclick="exampleSearch('good solvent for silicone and bad solvent for epoxy')">good for silicone, bad for epoxy</span>
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
                Drag to rotate &middot; Scroll to zoom &middot;
                Gold diamonds = polymers, colored dots = solvents by category
            </p>
        </div>
        <div id="chat-panel" class="chat-panel"></div>
        <div id="home-panel" class="home-panel">
            <div class="home-panel-header">
                <strong style="color:#e94560">All Materials</strong>
                <span style="color:#636e72;font-size:0.8rem;margin-left:8px" id="home-count"></span>
                <input type="text" id="home-filter" placeholder="Filter by name..." oninput="filterHomeTable(this.value)" style="margin-left:auto;width:180px;font-size:0.8rem;">
            </div>
            <div class="home-tabs">
                <button class="home-tab active" onclick="switchHomeTab('solvents')">Solvents</button>
                <button class="home-tab" onclick="switchHomeTab('polymers')">Polymers</button>
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

        // ===================== HSP MATH =====================
        function hspDistance(a, b) {{
            return Math.sqrt(4 * Math.pow(a.dd - b.dd, 2) + Math.pow(a.dp - b.dp, 2) + Math.pow(a.dh - b.dh, 2));
        }}
        function redNumber(solvent, polymer) {{
            if (!polymer.r || polymer.r <= 0) return null;
            return hspDistance(solvent, polymer) / polymer.r;
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
            const distances = validResults.map(r => r.ra != null ? r.ra : 0);
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
            const multiGoodBad = q.match(/good\s+solvents?\s+for\s+(.+?)\s+and\s+(?:a\s+)?bad\s+solvents?\s+for\s+(.+)/i);
            if (multiGoodBad) {{
                return {{ intent: 'multi_material', materials: [
                    {{ name: multiGoodBad[1].replace(/[?.!]/g, '').trim(), requirement: 'good' }},
                    {{ name: multiGoodBad[2].replace(/[?.!]/g, '').trim(), requirement: 'bad' }},
                ]}};
            }}
            const multiBadGood = q.match(/bad\s+solvents?\s+for\s+(.+?)\s+and\s+(?:a\s+)?good\s+solvents?\s+for\s+(.+)/i);
            if (multiBadGood) {{
                return {{ intent: 'multi_material', materials: [
                    {{ name: multiBadGood[1].replace(/[?.!]/g, '').trim(), requirement: 'bad' }},
                    {{ name: multiBadGood[2].replace(/[?.!]/g, '').trim(), requirement: 'good' }},
                ]}};
            }}
            const multiBoth = q.match(/good\s+solvents?\s+for\s+(?:both\s+)?(.+?)\s+and\s+(.+)/i);
            if (multiBoth) {{
                return {{ intent: 'multi_material', materials: [
                    {{ name: multiBoth[1].replace(/[?.!]/g, '').trim(), requirement: 'good' }},
                    {{ name: multiBoth[2].replace(/[?.!]/g, '').trim(), requirement: 'good' }},
                ]}};
            }}
            const multiBothBad = q.match(/bad\s+solvents?\s+for\s+(?:both\s+)?(.+?)\s+and\s+(.+)/i);
            if (multiBothBad) {{
                return {{ intent: 'multi_material', materials: [
                    {{ name: multiBothBad[1].replace(/[?.!]/g, '').trim(), requirement: 'bad' }},
                    {{ name: multiBothBad[2].replace(/[?.!]/g, '').trim(), requirement: 'bad' }},
                ]}};
            }}
            const dissolvesBoth = q.match(/(?:dissolves?|dissolve)\s+(?:both\s+)?(.+?)\s+and\s+(.+)/i);
            if (dissolvesBoth) {{
                return {{ intent: 'multi_material', materials: [
                    {{ name: dissolvesBoth[1].replace(/[?.!]/g, '').trim(), requirement: 'good' }},
                    {{ name: dissolvesBoth[2].replace(/[?.!]/g, '').trim(), requirement: 'good' }},
                ]}};
            }}

            const hasStandardIntent = /good\s+solvent|bad\s+solvent|best\s+solvent|worst\s+solvent|poor\s+solvent|dissolve|compatible\s+with|incompatible|similar\s+to|close\s+to|solvents?\s+for|polymers?\s+for|polymers?\s+similar|solvents?\s+similar/i.test(q);

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
                /bad\s+solvents?\s+for/i, /(?:poor|worst|incompatible)\s+solvents?\s+for/i,
                /solvents?\s+(?:that\s+)?(?:won'?t|will\s+not|cannot|can'?t)\s+dissolve/i,
                /(?:resist|resistant|insoluble)/i, /non[- ]?solvents?\s+for/i,
            ];
            const goodPatterns = [
                /good\s+solvents?\s+(for|to\s+dissolve)/i, /best\s+solvents?\s+for/i,
                /(?:what|which)\s+(?:solvents?\s+)?(?:dissolves?|will\s+dissolve|can\s+dissolve)/i,
                /solvents?\s+(?:that\s+)?(?:dissolves?|for|compatible\s+with)/i,
                /dissolve\s+/i, /compatible\s+solvents?\s+for/i, /soluble\s+in/i,
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
                const scored = SOLVENTS.map(s => {{
                    const info = {{ ...s, reds: {{}}, ras: {{}} }};
                    let combinedScore = 0;
                    for (const t of targets) {{
                        const ra = hspDistance(s, t);
                        const red = (t.r && t.r > 0) ? ra / t.r : null;
                        info.reds[t.name] = red;
                        info.ras[t.name] = ra;
                        combinedScore += t.requirement === 'good' ? ra : -ra;
                    }}
                    info.combinedScore = combinedScore;
                    return info;
                }});
                scored.sort((a, b) => a.combinedScore - b.combinedScore);
                const results = scored.slice(0, resultCount);
                const desc = targets.map(t => (t.requirement === 'good' ? 'compatible with' : 'incompatible with') + ' ' + t.name).join(' AND ');
                chatContext = {{ intent: 'multi_material', targets, targetType: 'polymer' }};
                return {{ intent: 'multi_material', targets, results, description: 'Top ' + resultCount + ' solvents: ' + desc + '.', targetType: 'polymer' }};
            }}

            if (intent === 'good_solvents' || intent === 'bad_solvents') {{
                let target = findPolymer(material);
                if (!target) {{ const words = material.split(/\s+/); for (const w of words) {{ target = findPolymer(w); if (target) break; }} }}
                if (!target) return {{ error: 'Could not find a matching polymer for "' + material + '". Try names like "polystyrene", "PVC", "PMMA", or "nylon".' }};
                const scored = SOLVENTS.map(s => ({{ ...s, ra: hspDistance(s, target), red: redNumber(s, target) }}));
                if (intent === 'good_solvents') {{
                    scored.sort((a, b) => a.ra - b.ra);
                    chatContext = {{ intent, target, targetType: 'polymer' }};
                    return {{ intent, target, results: scored.slice(0, resultCount), description: 'Top ' + resultCount + ' solvents by HSP distance (Ra). RED < 1 = inside solubility sphere = compatible.', targetType: 'polymer' }};
                }} else {{
                    scored.sort((a, b) => b.ra - a.ra);
                    chatContext = {{ intent, target, targetType: 'polymer' }};
                    return {{ intent, target, results: scored.slice(0, resultCount), description: 'Top ' + resultCount + ' most incompatible solvents by HSP distance (Ra). RED > 1 = outside sphere.', targetType: 'polymer' }};
                }}
            }}

            if (intent === 'similar_solvents') {{
                let target = findSolvent(material);
                if (!target) {{ const words = material.split(/\s+/); for (const w of words) {{ target = findSolvent(w); if (target) break; }} }}
                if (!target) return {{ error: 'Could not find solvent "' + material + '". Try "toluene", "acetone", "NMP", "DMSO", etc.' }};
                const scored = SOLVENTS.filter(s => s.name !== target.name).map(s => ({{ ...s, ra: hspDistance(s, target) }}));
                scored.sort((a, b) => a.ra - b.ra);
                chatContext = {{ intent, target, targetType: 'solvent' }};
                return {{ intent, target, results: scored.slice(0, resultCount), description: 'Solvents closest to ' + target.name + ' in Hansen space.', targetType: 'solvent' }};
            }}

            if (intent === 'similar_polymers') {{
                let target = findPolymer(material);
                if (!target) {{ const words = material.split(/\s+/); for (const w of words) {{ target = findPolymer(w); if (target) break; }} }}
                if (!target) return {{ error: 'Could not find polymer "' + material + '". Try "polystyrene", "epoxy", "PMMA", etc.' }};
                const scored = POLYMERS.filter(p => p.name !== target.name).map(p => ({{ ...p, ra: hspDistance(p, target) }}));
                scored.sort((a, b) => a.ra - b.ra);
                chatContext = {{ intent, target, targetType: 'polymer' }};
                return {{ intent, target, results: scored.slice(0, resultCount), description: 'Polymers closest to ' + target.name + ' in Hansen space.', targetType: 'polymer' }};
            }}

            return {{ error: 'Could not understand the query. Try "good solvents for polystyrene", "bad solvents for PVC", or "solvents similar to toluene".' }};
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
            const rows = Array.from(tbody.rows);
            const key = 'rt-' + colIdx;
            resultSortDir[key] = !resultSortDir[key];
            const dir = resultSortDir[key] ? 1 : -1;
            rows.sort((a, b) => {{
                let va = a.cells[colIdx].textContent.trim();
                let vb = b.cells[colIdx].textContent.trim();
                const na = parseFloat(va), nb = parseFloat(vb);
                if (!isNaN(na) && !isNaN(nb)) return (na - nb) * dir;
                return va.localeCompare(vb) * dir;
            }});
            rows.forEach(row => tbody.appendChild(row));
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

            let html = '';

            const isMulti = intent === 'multi_material';
            const showRed = parentIntent === 'good_solvents' || parentIntent === 'bad_solvents';
            const targetList = isMulti ? (result.targets || []) : (target ? [target] : []);
            const showTarget = targetList.length > 0 && intent !== 'followup';

            // --- Single unified table with shared columns ---
            const tableId = 'rt-' + Date.now();
            html += '<table class="results-table" id="' + tableId + '" style="margin-top:10px"><thead><tr>';
            let colNum = 0;
            const th = (label) => '<th onclick="sortResultsTable(this.closest(\\x27table\\x27),' + (colNum++) + ')" style="cursor:pointer">' + label + '</th>';
            html += th('#') + th('Name') + th('CAS') + th('Source') + th('&delta;D') + th('&delta;P') + th('&delta;H');
            if (isMulti) {{ result.targets.forEach(t => {{ html += th('Ra(' + t.name.slice(0, 15) + ')') + th('RED(' + t.name.slice(0, 15) + ')'); }}); }}
            else if (showRed) {{ html += th('Ra') + th('RED'); }}
            else if (parentIntent === 'similar_solvents') {{ html += th('Ra') + th('Category'); }}
            else {{ html += th('Ra') + th('R&#8320;') + th('Type'); }}
            html += '</tr></thead><tbody>';

            // --- Target material rows ---
            if (showTarget) {{
                targetList.forEach(t => {{
                    html += '<tr style="background:#eef1f6;border-bottom:2px solid #dfe6e9">';
                    html += '<td style="color:#e94560;font-weight:bold">★</td>';
                    html += '<td><strong style="color:#e94560">' + t.name + '</strong></td>';
                    html += '<td>' + (t.cas || '') + '</td>';
                    html += '<td>' + (t.src || '') + '</td>';
                    html += '<td>' + (t.dd != null ? t.dd.toFixed(1) : '') + '</td>';
                    html += '<td>' + (t.dp != null ? t.dp.toFixed(1) : '') + '</td>';
                    html += '<td>' + (t.dh != null ? t.dh.toFixed(1) : '') + '</td>';
                    if (isMulti) {{
                        result.targets.forEach(tt => {{
                            html += '<td></td>';
                            if (tt.name === t.name) {{
                                const chipColor = t.requirement === 'bad' ? '#EF553B' : '#00CC96';
                                html += '<td><span style="display:inline-block;background:' + chipColor + ';color:white;padding:2px 10px;border-radius:12px;font-size:0.8rem;font-weight:600">' + t.requirement + '</span></td>';
                            }} else {{ html += '<td></td>'; }}
                        }});
                    }} else if (showRed) {{
                        html += '<td></td><td style="color:#636e72">R&#8320;=' + (t.r || 'N/A') + '</td>';
                    }} else if (parentIntent === 'similar_solvents') {{
                        html += '<td></td><td>' + (t.cat || '') + '</td>';
                    }} else {{
                        html += '<td></td><td>' + (t.r || '') + '</td><td>' + (t.type || '') + '</td>';
                    }}
                    html += '</tr>';
                }});
            }}

            // --- Candidate result rows ---
            results.forEach((r, i) => {{
                if (r.notFound) {{ html += '<tr><td class="rank">' + (i + 1) + '</td><td colspan="9" style="color:#EF553B">Could not find "' + r.queryName + '" in the database</td></tr>'; return; }}
                const nameHtml = '<span class="hoverable-name" onclick="highlightInPlot(\\x27' + encodeURIComponent(r.name) + '\\x27)" onmouseenter="showStructure(event,\\x27' + encodeURIComponent(r.name) + '\\x27)" onmouseleave="hideStructure()">' + r.name + '</span>';
                html += '<tr><td class="rank">' + (i + 1) + '</td><td>' + nameHtml + '</td><td>' + (r.cas || '') + '</td><td>' + (r.src || '') + '</td>';
                html += '<td>' + (r.dd != null ? r.dd.toFixed(1) : '') + '</td><td>' + (r.dp != null ? r.dp.toFixed(1) : '') + '</td><td>' + (r.dh != null ? r.dh.toFixed(1) : '') + '</td>';
                if (isMulti) {{ result.targets.forEach(t => {{ const ra = r.ras[t.name]; const red = r.reds[t.name]; html += '<td>' + (ra != null ? ra.toFixed(2) : '') + '</td>'; let cls = 'red-bad'; if (red != null) {{ if (red < 1) cls = 'red-good'; else if (red < 1.2) cls = 'red-boundary'; }} html += '<td class="' + cls + '">' + (red != null ? red.toFixed(2) : 'N/A') + '</td>'; }}); }}
                else {{ html += '<td>' + (r.ra != null ? r.ra.toFixed(2) : '') + '</td>'; if (showRed) {{ const red = r.red; let cls = 'red-bad'; if (red !== null) {{ if (red < 1) cls = 'red-good'; else if (red < 1.2) cls = 'red-boundary'; }} html += '<td class="' + cls + '">' + (red !== null ? red.toFixed(2) : 'N/A') + '</td>'; }} else if (parentIntent === 'similar_solvents') {{ html += '<td>' + (r.cat || '') + '</td>'; }} else {{ html += '<td>' + (r.r || '') + '</td><td>' + (r.type || '') + '</td>'; }} }}
                html += '</tr>';
            }});
            html += '</tbody></table>';
            return html;
        }}

        // ===================== 3D PLOT =====================
        let plotDiv;
        let fullTraces = [];

        function buildFullPlot() {{
            plotDiv = document.getElementById('plotly-div');
            const traces = [];
            const cats = [...new Set(SOLVENTS.map(s => s.cat))].sort();
            for (const cat of cats) {{
                const cs = SOLVENTS.filter(s => s.cat === cat);
                const color = CAT_COLORS[cat] || '#888';
                traces.push({{
                    type: 'scatter3d', mode: 'markers',
                    name: cat.charAt(0).toUpperCase() + cat.slice(1),
                    x: cs.map(s => s.dd), y: cs.map(s => s.dp), z: cs.map(s => s.dh),
                    text: cs.map(s => s.name + '<br>CAS: ' + s.cas + '<br>MW: ' + s.mw + '<br>BP: ' + s.bp + '°C'),
                    hovertemplate: '<b>%{{text}}</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>',
                    marker: {{ size: 5, color: color, opacity: 0.85 }},
                }});
            }}
            traces.push({{
                type: 'scatter3d', mode: 'markers',
                name: 'Polymers',
                x: POLYMERS.map(p => p.dd), y: POLYMERS.map(p => p.dp), z: POLYMERS.map(p => p.dh),
                text: POLYMERS.map(p => p.name + '<br>R₀=' + p.r),
                hovertemplate: '<b>%{{text}}</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>',
                marker: {{ size: 7, color: 'gold', symbol: 'diamond', opacity: 0.95 }},
            }});
            fullTraces = traces;
            Plotly.newPlot(plotDiv, traces, defaultLayout(), {{ responsive: true }});
        }}

        function defaultLayout(title) {{
            var axisStyle = {{
                gridcolor: '#dfe6e9',
                zerolinecolor: '#b2bec3',
                backgroundcolor: '#f8f9fa',
                showbackground: true,
                tickfont: {{ size: 11, color: '#636e72' }},
            }};
            return {{
                scene: {{
                    xaxis: Object.assign({{ title: {{ text: 'δD (Dispersion) MPa½', font: {{ size: 14, color: '#2d3436' }} }}, range: [12, 22] }}, axisStyle),
                    yaxis: Object.assign({{ title: {{ text: 'δP (Polar) MPa½', font: {{ size: 14, color: '#2d3436' }} }}, range: [0, 28] }}, axisStyle),
                    zaxis: Object.assign({{ title: {{ text: 'δH (H-bonding) MPa½', font: {{ size: 14, color: '#2d3436' }} }}, range: [0, 45] }}, axisStyle),
                }},
                paper_bgcolor: '#fff', plot_bgcolor: '#fff',
                margin: {{ l: 0, r: 0, t: 40, b: 0 }},
                legend: {{ x: 0.01, y: 0.99, bgcolor: 'rgba(255,255,255,0.85)', bordercolor: '#dfe6e9', borderwidth: 1, font: {{ color: '#2d3436' }} }},
                title: {{ text: title || 'Materialism — Hansen Solubility Parameter Space', x: 0.5, font: {{ size: 18, color: '#2d3436' }} }},
            }};
        }}

        function addSphere(traces, tgt, sphereColor) {{
            if (!tgt.r || tgt.r <= 0) return;
            const N = 30, M = 20, x = [], y = [], z = [];
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

        function updatePlotWithResults(result) {{
            if (!result || result.error) return;
            const {{ results }} = result;
            const target = result.target || (result.targets ? result.targets[0] : null);
            const parentIntent = result.parentIntent || result.intent;
            const isMulti = result.intent === 'multi_material';

            // Deactivate any open tab panel
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            window.dispatchEvent(new Event('resize'));
            const traces = [];

            traces.push({{ type: 'scatter3d', mode: 'markers', name: 'All Solvents',
                x: SOLVENTS.map(s => s.dd), y: SOLVENTS.map(s => s.dp), z: SOLVENTS.map(s => s.dh),
                text: SOLVENTS.map(s => s.name),
                hovertemplate: '<b>%{{text}}</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>',
                marker: {{ size: 3, color: '#444', opacity: 0.15 }},
            }});
            traces.push({{ type: 'scatter3d', mode: 'markers', name: 'All Polymers',
                x: POLYMERS.map(p => p.dd), y: POLYMERS.map(p => p.dp), z: POLYMERS.map(p => p.dh),
                text: POLYMERS.map(p => p.name),
                hovertemplate: '<b>%{{text}}</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>',
                marker: {{ size: 4, color: '#665500', symbol: 'diamond', opacity: 0.15 }},
            }});

            const valid = results.filter(r => !r.notFound);
            const resultColors = computeResultColors(valid);

            if (isMulti) {{
                traces.push({{
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
                    traces.push({{ type: 'scatter3d', mode: 'markers+text',
                        name: (tgt.requirement === 'good' ? '✓ ' : '✗ ') + tgt.name,
                        x: [tgt.dd], y: [tgt.dp], z: [tgt.dh], text: [tgt.name],
                        textposition: 'top center', textfont: {{ size: 12, color: c }},
                        hovertemplate: '<b>' + tgt.name + '</b> (' + tgt.requirement + ')<br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<br>R₀=' + tgt.r + '<extra></extra>',
                        marker: {{ size: 14, color: c, symbol: 'diamond', opacity: 1, line: {{ color: '#2d3436', width: 2 }} }},
                    }});
                    addSphere(traces, tgt, sphereColors[ti % sphereColors.length]);
                }});
            }} else if (parentIntent === 'good_solvents' || parentIntent === 'bad_solvents') {{
                traces.push({{
                    type: 'scatter3d', mode: 'markers+text', name: 'Results',
                    x: valid.map(r => r.dd), y: valid.map(r => r.dp), z: valid.map(r => r.dh),
                    text: valid.map((r, i) => (i + 1) + '. ' + r.name),
                    textposition: 'top center', textfont: {{ size: 9, color: '#2d3436' }},
                    hovertemplate: valid.map((r, i) =>
                        '<b>' + (i+1) + '. ' + r.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<br>Ra=' + r.ra.toFixed(2) +
                        (r.red !== null ? '<br>RED=' + r.red.toFixed(2) : '') + '<extra></extra>'),
                    marker: {{ size: 10, color: resultColors, opacity: 1, line: {{ color: '#2d3436', width: 1 }} }},
                }});
                traces.push({{ type: 'scatter3d', mode: 'markers+text', name: '★ Target: ' + target.name,
                    x: [target.dd], y: [target.dp], z: [target.dh], text: ['★ ' + target.name],
                    textposition: 'top center', textfont: {{ size: 13, color: '#e94560' }},
                    hovertemplate: '<b>★ ' + target.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<br>R₀=' + target.r + '<extra></extra>',
                    marker: {{ size: 16, color: '#e94560', symbol: 'diamond', opacity: 1, line: {{ color: '#2d3436', width: 2 }} }},
                }});
                addSphere(traces, target, 'rgba(233,69,96,0.2)');
            }} else {{
                const sym = (parentIntent === 'similar_polymers') ? 'diamond' : 'circle';
                traces.push({{
                    type: 'scatter3d', mode: 'markers+text', name: 'Results',
                    x: valid.map(r => r.dd), y: valid.map(r => r.dp), z: valid.map(r => r.dh),
                    text: valid.map((r, i) => (i + 1) + '. ' + r.name),
                    textposition: 'top center', textfont: {{ size: 9, color: '#2d3436' }},
                    hovertemplate: valid.map((r, i) =>
                        '<b>' + (i+1) + '. ' + r.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<br>Ra=' + r.ra.toFixed(2) + '<extra></extra>'),
                    marker: {{ size: 10, color: resultColors, symbol: sym, opacity: 1, line: {{ color: '#2d3436', width: 1 }} }},
                }});
                const tsym = (parentIntent === 'similar_polymers') ? 'diamond' : 'circle';
                traces.push({{ type: 'scatter3d', mode: 'markers+text', name: '★ Target: ' + target.name,
                    x: [target.dd], y: [target.dp], z: [target.dh], text: ['★ ' + target.name],
                    textposition: 'top center', textfont: {{ size: 13, color: '#e94560' }},
                    hovertemplate: '<b>★ ' + target.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>',
                    marker: {{ size: 16, color: '#e94560', symbol: tsym, opacity: 1, line: {{ color: '#2d3436', width: 2 }} }},
                }});
            }}

            var layout = defaultLayout(isMulti ? 'Multi-Material Search' : 'Search Results — ' + target.name);
            if (plotDiv.layout && plotDiv.layout.scene && plotDiv.layout.scene.camera) {{
                layout.scene.camera = plotDiv.layout.scene.camera;
            }}
            Plotly.react(plotDiv, traces, layout);
        }}

        function resetPlot() {{
            var layout = defaultLayout();
            if (plotDiv.layout && plotDiv.layout.scene && plotDiv.layout.scene.camera) {{
                layout.scene.camera = plotDiv.layout.scene.camera;
            }}
            Plotly.react(plotDiv, fullTraces, layout);
        }}

        // ===================== HIGHLIGHT IN PLOT =====================
        function highlightInPlot(encodedName) {{
            const name = decodeURIComponent(encodedName);
            let mat = SOLVENTS.find(s => s.name === name);
            let sym = 'circle';
            if (!mat) {{ mat = POLYMERS.find(p => p.name === name); sym = 'diamond'; }}
            if (!mat) return;
            const currentData = plotDiv.data.filter(t => t.name !== '★ Highlighted');
            currentData.push({{
                type: 'scatter3d', mode: 'markers+text', name: '★ Highlighted',
                x: [mat.dd], y: [mat.dp], z: [mat.dh], text: ['★ ' + mat.name],
                textposition: 'top center', textfont: {{ size: 13, color: '#FFD700' }},
                hovertemplate: '<b>' + mat.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>',
                marker: {{ size: 18, color: '#FFD700', symbol: sym, opacity: 1, line: {{ color: '#2d3436', width: 2 }} }},
            }});
            Plotly.react(plotDiv, currentData, plotDiv.layout);
        }}

        // ===================== HOME PANEL (all materials) =====================
        var homeTab = 'solvents';
        var homeFilterText = '';

        function buildHomeTable() {{
            var thead = document.getElementById('home-thead');
            var tbody = document.getElementById('home-tbody');
            var countEl = document.getElementById('home-count');
            var headerHtml, rowsHtml;

            if (homeTab === 'solvents') {{
                headerHtml = '<tr><th>Name</th><th>CAS</th><th>&delta;D</th><th>&delta;P</th><th>&delta;H</th><th>MW</th><th>BP &deg;C</th><th>Category</th></tr>';
                var filtered = SOLVENTS;
                if (homeFilterText) {{
                    var q = homeFilterText.toLowerCase();
                    filtered = SOLVENTS.filter(function(s) {{ return s.name.toLowerCase().indexOf(q) !== -1 || (s.cas && s.cas.indexOf(q) !== -1); }});
                }}
                countEl.textContent = filtered.length + ' solvents';
                rowsHtml = '';
                for (var i = 0; i < filtered.length; i++) {{
                    var s = filtered[i];
                    var catColor = CAT_COLORS[s.cat] || '#888';
                    function lnk(val, url) {{ if (val == null || val === '') return ''; var v = (typeof val === 'number') ? val.toFixed(1) : val; return url ? '<a href="' + url + '" target="_blank" rel="noopener" style="color:#0984e3;text-decoration:none">' + v + '</a>' : v; }}
                    rowsHtml += '<tr style="border-left:3px solid ' + catColor + '">';
                    rowsHtml += '<td><span class="hoverable-name" onmouseenter="showStructure(event,\\x27' + encodeURIComponent(s.name) + '\\x27)" onmouseleave="hideStructure()">' + s.name + '</span></td>';
                    rowsHtml += '<td>' + (s.cas || '') + '</td>';
                    rowsHtml += '<td>' + lnk(s.dd, s.srcUrl) + '</td>';
                    rowsHtml += '<td>' + lnk(s.dp, s.srcUrl) + '</td>';
                    rowsHtml += '<td>' + lnk(s.dh, s.srcUrl) + '</td>';
                    rowsHtml += '<td>' + lnk(s.mw, s.mwSrc) + '</td>';
                    rowsHtml += '<td>' + (s.bp != null ? lnk(s.bp, s.bpSrc) : '') + '</td>';
                    rowsHtml += '<td style="color:' + catColor + '">' + (s.cat || '') + '</td>';
                    rowsHtml += '</tr>';
                }}
            }} else {{
                headerHtml = '<tr><th>Name</th><th>CAS</th><th>&delta;D</th><th>&delta;P</th><th>&delta;H</th><th>R&#8320;</th><th>Type</th></tr>';
                var filtered = POLYMERS;
                if (homeFilterText) {{
                    var q = homeFilterText.toLowerCase();
                    filtered = POLYMERS.filter(function(p) {{ return p.name.toLowerCase().indexOf(q) !== -1 || (p.cas && p.cas.indexOf(q) !== -1); }});
                }}
                countEl.textContent = filtered.length + ' polymers';
                rowsHtml = '';
                for (var i = 0; i < filtered.length; i++) {{
                    var p = filtered[i];
                    function lnk(val, url) {{ if (val == null || val === '') return ''; var v = (typeof val === 'number') ? val.toFixed(1) : val; return url ? '<a href="' + url + '" target="_blank" rel="noopener" style="color:#0984e3;text-decoration:none">' + v + '</a>' : v; }}
                    rowsHtml += '<tr>';
                    rowsHtml += '<td>' + p.name + '</td>';
                    rowsHtml += '<td>' + (p.cas || '') + '</td>';
                    rowsHtml += '<td>' + lnk(p.dd, p.srcUrl) + '</td>';
                    rowsHtml += '<td>' + lnk(p.dp, p.srcUrl) + '</td>';
                    rowsHtml += '<td>' + lnk(p.dh, p.srcUrl) + '</td>';
                    rowsHtml += '<td>' + (p.r || '') + '</td>';
                    rowsHtml += '<td>' + (p.type || '') + '</td>';
                    rowsHtml += '</tr>';
                }}
            }}

            thead.innerHTML = headerHtml;
            tbody.innerHTML = rowsHtml;
        }}

        function switchHomeTab(tab) {{
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

        document.addEventListener('mousemove', function(e) {{
            if (tooltip.el && tooltip.el.style.display === 'block') positionTooltip(e);
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
            if (!result.error) updatePlotWithResults(result);
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
            buildFullPlot();
            buildHomeTable();
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

# ===================== Generate separate database pages =====================

db_page_css = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #f5f6fa; color: #2d3436; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
.header { background: #fff; padding: 15px 30px; display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #dfe6e9; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.header h1 { font-size: 1.5rem; color: #e94560; }
.header h1 a { color: #e94560; text-decoration: none; }
.header .stats { color: #636e72; font-size: 0.9rem; }
.content { padding: 20px 30px; }
.search-row { margin-bottom: 16px; }
.search-row input { background: #fff; border: 2px solid #dfe6e9; color: #2d3436; padding: 10px 16px; border-radius: 6px; width: 350px; font-size: 0.95rem; outline: none; }
.search-row input:focus { border-color: #e94560; }
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th { background: #f0f2f5; color: #e94560; padding: 10px; text-align: left; position: sticky; top: 0; cursor: pointer; z-index: 1; border-bottom: 2px solid #dfe6e9; }
th:hover { background: #e8eaed; }
td { padding: 8px 10px; border-bottom: 1px solid #eee; color: #2d3436; }
tr:hover { background: #f8f9fa; }
.table-wrapper { border: 1px solid #dfe6e9; border-radius: 6px; overflow: auto; max-height: calc(100vh - 160px); }
th.sort-asc::after { content: ' ▲'; font-size: 0.7em; color: #e94560; }
th.sort-desc::after { content: ' ▼'; font-size: 0.7em; color: #e94560; }
"""

db_page_js = """
function filterTable(q) {
    var rows = document.querySelectorAll('#db-table tbody tr');
    var lq = q.toLowerCase();
    rows.forEach(function(row) { row.style.display = row.textContent.toLowerCase().includes(lq) ? '' : 'none'; });
}
var sortDir = {};
function sortTable(colIdx) {
    var table = document.getElementById('db-table');
    var tbody = table.querySelector('tbody');
    var rows = Array.from(tbody.rows);
    var key = 'c' + colIdx;
    sortDir[key] = !sortDir[key];
    var dir = sortDir[key] ? 1 : -1;
    var ths = table.querySelectorAll('th');
    ths.forEach(function(th) { th.classList.remove('sort-asc', 'sort-desc'); });
    ths[colIdx].classList.add(sortDir[key] ? 'sort-asc' : 'sort-desc');
    rows.sort(function(a, b) {
        var va = a.cells[colIdx].textContent.trim();
        var vb = b.cells[colIdx].textContent.trim();
        var na = parseFloat(va), nb = parseFloat(vb);
        if (!isNaN(na) && !isNaN(nb)) return (na - nb) * dir;
        return va.localeCompare(vb) * dir;
    });
    rows.forEach(function(row) { tbody.appendChild(row); });
}
"""

def gen_db_page(title, headers, rows_html, search_placeholder, filename):
    header_html = "".join(f'<th onclick="sortTable({i})">{h}</th>' for i, h in enumerate(headers))
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Materialism — {title}</title>
<style>{db_page_css}</style>
</head><body>
<div class="header">
    <h1><a href="materialism.html">Materialism</a> — {title}</h1>
    <div class="stats">{len(solvents)} solvents &middot; {len(poly_data)} polymers</div>
</div>
<div class="content">
    <div class="search-row"><input type="text" placeholder="{search_placeholder}" oninput="filterTable(this.value)"></div>
    <div class="table-wrapper">
        <table id="db-table">
            <thead><tr>{header_html}</tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
</div>
<script>{db_page_js}</script>
</body></html>"""
    out = os.path.join(os.path.dirname(__file__), filename)
    with open(out, "w") as f:
        f.write(page)
    print(f"Generated: {out} ({os.path.getsize(out) / 1024:.0f} KB)")

gen_db_page(
    "Solvent Database",
    ["Name", "CAS", "&delta;D", "&delta;P", "&delta;H", "MW", "BP &deg;C", "Category"],
    table_rows,
    "Search solvents by name or CAS...",
    "solvents.html"
)

gen_db_page(
    "Polymer Database",
    ["Name", "CAS", "&delta;D", "&delta;P", "&delta;H", "R\u2080", "Type"],
    polymer_rows,
    "Search polymers...",
    "polymers.html"
)
