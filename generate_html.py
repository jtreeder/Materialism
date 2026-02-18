"""Generate a standalone interactive HTML file with the full HSP visualization."""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import numpy as np
import plotly.graph_objects as go

from backend.app.models.database import init_db, get_engine, get_session, Chemical, Polymer
from backend.app.data.seed_data import seed_database
from backend.app.services.hsp_calculator import hsp_distance, red_number

DB_PATH = os.path.join(os.path.dirname(__file__), "materialism.db")
engine = init_db(get_engine(DB_PATH))
session = get_session(engine)
seed_database(session)

# Load data
chemicals = session.query(Chemical).all()
polymers = session.query(Polymer).all()

# Also read polymer CAS from CSV if available
polymer_cas = {}
try:
    import csv
    with open(os.path.join(os.path.dirname(__file__), "data", "processed", "hsp_polymers.csv")) as f:
        for row in csv.DictReader(f):
            cas = row.get("cas_number", "").strip()
            if cas:
                polymer_cas[row["name"].strip()] = cas
except Exception:
    pass

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
for c in chemicals:
    if c.has_hsp:
        solvents.append({
            "name": c.name, "cas": c.cas_number or "",
            "dd": c.delta_d, "dp": c.delta_p, "dh": c.delta_h,
            "mw": c.molecular_weight, "bp": c.boiling_point,
            "cat": c.category or "other",
            "smiles": c.smiles or "",
            "src": SOURCE_NAMES.get(c.data_source, c.data_source or ""),
            "srcUrl": c.source_url or "",
        })

poly_data = []
for p in polymers:
    poly_data.append({
        "name": p.name, "dd": p.delta_d, "dp": p.delta_p,
        "dh": p.delta_h, "r": p.radius, "type": p.type or "",
        "cas": polymer_cas.get(p.name, ""),
        "src": SOURCE_NAMES.get(p.data_source, p.data_source or ""),
        "srcUrl": p.source_url or "",
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

# --- Build HTML data tables ---
table_rows = ""
for s in sorted(solvents, key=lambda x: x["name"]):
    src_link = f'<a href="{s["srcUrl"]}" target="_blank" style="color:#6ea8fe;text-decoration:none">{s["src"]}</a>' if s["srcUrl"] else s["src"]
    table_rows += f"""<tr>
        <td>{s['name']}</td><td>{s['cas']}</td>
        <td>{s['dd']}</td><td>{s['dp']}</td><td>{s['dh']}</td>
        <td>{s['mw'] or ''}</td><td>{s['bp'] or ''}</td>
        <td>{s['cat']}</td><td>{src_link}</td>
    </tr>"""

polymer_rows = ""
for p in sorted(poly_data, key=lambda x: x["name"]):
    src_link = f'<a href="{p["srcUrl"]}" target="_blank" style="color:#6ea8fe;text-decoration:none">{p["src"]}</a>' if p["srcUrl"] else p["src"]
    polymer_rows += f"""<tr>
        <td>{p['name']}</td><td>{p['cas']}</td>
        <td>{p['dd']}</td><td>{p['dp']}</td><td>{p['dh']}</td>
        <td>{p['r']}</td><td>{p['type']}</td><td>{src_link}</td>
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
        body {{ background: #1a1a2e; color: #e0e0e0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
        .header {{ background: #16213e; padding: 15px 30px; display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #0f3460; }}
        .header h1 {{ font-size: 1.5rem; color: #e94560; }}
        .header .stats {{ color: #888; font-size: 0.9rem; }}
        .tabs {{ display: flex; gap: 0; background: #16213e; border-bottom: 2px solid #0f3460; }}
        .tab {{ padding: 12px 24px; cursor: pointer; border: none; background: transparent; color: #888; font-size: 0.95rem; transition: all 0.2s; }}
        .tab:hover {{ color: #e0e0e0; background: #1a1a2e; }}
        .tab.active {{ color: #e94560; border-bottom: 2px solid #e94560; background: #1a1a2e; }}
        .panel {{ display: none; padding: 20px; }}
        .panel.active {{ display: block; }}
        .plot-container {{ width: 100%; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.85rem; }}
        th {{ background: #16213e; color: #e94560; padding: 10px; text-align: left; position: sticky; top: 0; cursor: pointer; }}
        th:hover {{ background: #0f3460; }}
        td {{ padding: 8px 10px; border-bottom: 1px solid #333; }}
        tr:hover {{ background: #16213e; }}
        .table-wrapper {{ max-height: 500px; overflow-y: auto; border: 1px solid #333; border-radius: 4px; }}
        input[type="text"] {{ background: #16213e; border: 1px solid #333; color: #e0e0e0; padding: 8px 12px; border-radius: 4px; width: 300px; margin: 10px 0; }}
        input[type="text"]:focus {{ outline: none; border-color: #e94560; }}
        .info {{ background: #16213e; padding: 20px; border-radius: 8px; margin: 10px 0; line-height: 1.7; }}
        .info h3 {{ color: #e94560; margin-bottom: 10px; }}
        .info code {{ background: #0f3460; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }}
        .compatible {{ color: #00CC96; font-weight: bold; }}
        .incompatible {{ color: #EF553B; }}

        /* --- Chat / Search UI --- */
        .search-bar {{
            display: flex; align-items: center; gap: 10px; padding: 16px 20px;
            background: #16213e; border-bottom: 1px solid #0f3460;
        }}
        .search-bar input {{
            flex: 1; max-width: 700px; padding: 12px 18px; font-size: 1rem;
            background: #1a1a2e; border: 2px solid #0f3460; color: #e0e0e0;
            border-radius: 8px; outline: none; transition: border-color 0.2s;
        }}
        .search-bar input:focus {{ border-color: #e94560; }}
        .search-bar input::placeholder {{ color: #666; }}
        .search-bar button {{
            padding: 12px 24px; font-size: 1rem; background: #e94560; color: white;
            border: none; border-radius: 8px; cursor: pointer; font-weight: 600;
            transition: background 0.2s;
        }}
        .search-bar button:hover {{ background: #c73652; }}
        .search-bar .clear-btn {{
            padding: 12px 16px; font-size: 1rem; background: #333; color: #aaa;
            border: 1px solid #555; border-radius: 8px; cursor: pointer;
        }}
        .search-bar .clear-btn:hover {{ background: #444; color: #fff; }}
        .search-options {{
            display: flex; align-items: center; justify-content: space-between;
            padding: 4px 20px 10px; background: #16213e;
            border-bottom: 2px solid #0f3460;
        }}
        .search-examples {{
            font-size: 0.8rem; color: #666;
        }}
        .search-examples span {{
            cursor: pointer; color: #557; margin-right: 14px;
            transition: color 0.2s;
        }}
        .search-examples span:hover {{ color: #e94560; }}
        .result-count-selector {{
            font-size: 0.8rem; color: #666; display: flex; align-items: center; gap: 4px;
            white-space: nowrap;
        }}
        .rc-btn {{
            background: #1a1a2e; border: 1px solid #333; color: #888;
            padding: 3px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8rem;
            transition: all 0.2s;
        }}
        .rc-btn:hover {{ border-color: #e94560; color: #e0e0e0; }}
        .rc-btn.active {{ background: #e94560; color: white; border-color: #e94560; }}

        /* --- Chat Panel --- */
        .chat-panel {{
            display: none; max-height: 500px; overflow-y: auto; margin: 0 20px;
            padding: 12px 0; border-bottom: 1px solid #0f3460;
        }}
        .chat-panel.visible {{ display: block; }}
        .chat-msg {{
            margin: 8px 0; padding: 10px 14px; border-radius: 8px;
            max-width: 95%; font-size: 0.9rem; line-height: 1.5;
        }}
        .chat-msg.user {{
            background: #0f3460; color: #e0e0e0; margin-left: auto;
            max-width: 60%; text-align: right; border-bottom-right-radius: 2px;
        }}
        .chat-msg.system {{
            background: #16213e; border: 1px solid #0f3460;
            border-bottom-left-radius: 2px;
        }}
        .chat-msg .msg-label {{
            font-size: 0.7rem; color: #888; margin-bottom: 4px;
            text-transform: uppercase; letter-spacing: 0.5px;
        }}
        .chat-context {{
            display: inline-block; background: #0f3460; color: #aaa; padding: 2px 8px;
            border-radius: 4px; font-size: 0.75rem; margin-bottom: 8px;
        }}

        /* --- Results Table in Chat --- */
        .results-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 8px; }}
        .results-table th {{
            background: #0f3460; color: #e94560; padding: 8px 10px;
            text-align: left; font-weight: 600; position: static;
        }}
        .results-table td {{ padding: 8px 10px; border-bottom: 1px solid #333; position: relative; }}
        .results-table tr:hover {{ background: #1a1a2e; }}
        .results-table .rank {{ color: #e94560; font-weight: bold; }}
        .red-good {{ color: #00CC96; font-weight: bold; }}
        .red-boundary {{ color: #FFA15A; font-weight: bold; }}
        .red-bad {{ color: #EF553B; font-weight: bold; }}
        .target-chip {{
            display: inline-block; background: #e94560; color: white; padding: 2px 10px;
            border-radius: 12px; font-size: 0.8rem; font-weight: 600; margin-left: 8px;
        }}
        .chat-reset {{
            margin-top: 10px; padding: 6px 14px; background: #333; color: #aaa;
            border: 1px solid #555; border-radius: 6px; cursor: pointer; font-size: 0.8rem;
        }}
        .chat-reset:hover {{ background: #444; color: #fff; border-color: #e94560; }}

        /* --- Structure Tooltip --- */
        .struct-tooltip {{
            display: none; position: fixed; z-index: 9999;
            background: #fff; border: 2px solid #e94560; border-radius: 8px;
            padding: 4px; box-shadow: 0 4px 20px rgba(0,0,0,0.5);
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
        .hoverable-name {{ cursor: help; border-bottom: 1px dotted #888; }}
        th.sort-asc::after {{ content: ' ▲'; font-size: 0.7em; color: #e94560; }}
        th.sort-desc::after {{ content: ' ▼'; font-size: 0.7em; color: #e94560; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Materialism</h1>
        <div class="stats">{len(solvents)} solvents &middot; {len(poly_data)} polymers &middot; Hansen Solubility Parameters</div>
    </div>

    <div class="search-bar">
        <input type="text" id="nl-search" placeholder="Ask anything — e.g. &quot;good solvents for polystyrene&quot; then follow up with &quot;what about NMP?&quot;"
               onkeydown="if(event.key==='Enter')runSearch()">
        <button onclick="runSearch()">Search</button>
        <button class="clear-btn" onclick="clearChat()">New Chat</button>
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

    <div id="chat-panel" class="chat-panel"></div>

    <div class="tabs">
        <div class="tab active" onclick="showTab('plot')">3D Hansen Space</div>
        <div class="tab" onclick="showTab('solvents')">Solvent Database</div>
        <div class="tab" onclick="showTab('polymers')">Polymer Database</div>
        <div class="tab" onclick="showTab('about')">How It Works</div>
    </div>

    <div id="panel-plot" class="panel active">
        <div class="plot-container">
            <div id="plotly-div" style="width:100%; height:800px;"></div>
        </div>
        <p style="color:#888; padding:10px; font-size:0.85rem;">
            Drag to rotate &middot; Scroll to zoom &middot;
            Gold diamonds = polymers, colored dots = solvents by category
        </p>
    </div>

    <div id="panel-solvents" class="panel">
        <input type="text" id="solvent-search" placeholder="Search solvents by name or CAS..." oninput="filterTable('solvent-table', this.value)">
        <div class="table-wrapper">
            <table id="solvent-table">
                <thead><tr>
                    <th onclick="sortTable('solvent-table',0)">Name</th>
                    <th onclick="sortTable('solvent-table',1)">CAS</th>
                    <th onclick="sortTable('solvent-table',2)">&delta;D</th>
                    <th onclick="sortTable('solvent-table',3)">&delta;P</th>
                    <th onclick="sortTable('solvent-table',4)">&delta;H</th>
                    <th onclick="sortTable('solvent-table',5)">MW</th>
                    <th onclick="sortTable('solvent-table',6)">BP &deg;C</th>
                    <th onclick="sortTable('solvent-table',7)">Category</th>
                    <th>Source</th>
                </tr></thead>
                <tbody>{table_rows}</tbody>
            </table>
        </div>
    </div>

    <div id="panel-polymers" class="panel">
        <input type="text" id="polymer-search" placeholder="Search polymers..." oninput="filterTable('polymer-table', this.value)">
        <div class="table-wrapper">
            <table id="polymer-table">
                <thead><tr>
                    <th onclick="sortTable('polymer-table',0)">Name</th>
                    <th onclick="sortTable('polymer-table',1)">CAS</th>
                    <th onclick="sortTable('polymer-table',2)">&delta;D</th>
                    <th onclick="sortTable('polymer-table',3)">&delta;P</th>
                    <th onclick="sortTable('polymer-table',4)">&delta;H</th>
                    <th onclick="sortTable('polymer-table',5)">R&#8320;</th>
                    <th onclick="sortTable('polymer-table',6)">Type</th>
                    <th>Source</th>
                </tr></thead>
                <tbody>{polymer_rows}</tbody>
            </table>
        </div>
    </div>

    <div id="panel-about" class="panel">
        <div class="info">
            <h3>Hansen Solubility Parameters (HSP)</h3>
            <p>Every material gets three numbers that describe its molecular interactions:</p>
            <ul style="margin: 10px 0 10px 20px;">
                <li><strong>&delta;D</strong> — Dispersion forces (van der Waals)</li>
                <li><strong>&delta;P</strong> — Polar forces (dipole-dipole)</li>
                <li><strong>&delta;H</strong> — Hydrogen bonding forces</li>
            </ul>
            <p>All measured in <strong>MPa&frac12;</strong>.</p>

            <h3 style="margin-top:20px;">The Distance Formula</h3>
            <p>Compatibility is predicted by the distance in Hansen space:</p>
            <p style="text-align:center; font-size:1.1em; margin:15px 0;">
                <code>Ra&sup2; = 4(&delta;D&#8321; - &delta;D&#8322;)&sup2; + (&delta;P&#8321; - &delta;P&#8322;)&sup2; + (&delta;H&#8321; - &delta;H&#8322;)&sup2;</code>
            </p>
            <p>The factor of <strong>4</strong> on the dispersion term is empirical — it makes the 3D
            Hansen space approximately spherical for real solubility data.</p>

            <h3 style="margin-top:20px;">RED Number</h3>
            <p><code>RED = Ra / R&#8320;</code> where R&#8320; is the solubility sphere radius.</p>
            <ul style="margin: 10px 0 10px 20px;">
                <li><span class="compatible">RED &lt; 1</span> — inside the sphere &rarr; <strong>compatible</strong></li>
                <li>RED = 1 — on the boundary</li>
                <li><span class="incompatible">RED &gt; 1</span> — outside the sphere &rarr; <strong>not compatible</strong></li>
            </ul>

            <h3 style="margin-top:20px;">Chat-Style Search</h3>
            <p>Use the search bar to ask questions in plain English. You can have a <strong>conversation</strong>:</p>
            <ul style="margin: 10px 0 10px 20px;">
                <li><strong>"good solvents for polystyrene"</strong> — finds the best solvents (configurable: 10, 25, or 50 results)</li>
                <li><strong>"what about NMP or DMSO?"</strong> — follow-up evaluates specific solvents against the same polymer</li>
                <li><strong>"bad solvents for PVC"</strong> — starts a new search for incompatible solvents</li>
                <li><strong>"solvents similar to toluene"</strong> — finds the nearest neighbors</li>
            </ul>
            <p>Common acronyms are supported: NMP, DMSO, DMF, THF, MEK, DCM, PVC, PMMA, PTFE, etc.</p>
            <p>Hover over material names in results to see molecular structures (loaded from PubChem).</p>

            <h3 style="margin-top:20px;">The 3D Plot</h3>
            <p>Each dot is a solvent positioned at its (&delta;D, &delta;P, &delta;H) coordinates.
            Search results highlight matched materials and show the polymer's solubility sphere.</p>
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
            'nmp': '1Methyl2Pyrrolidinone',
            'n-methyl-2-pyrrolidone': '1Methyl2Pyrrolidinone',
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
            'etoh': 'Ethanol',
            'formamide': 'Formamide',
            'dmpu': 'DMPU (1,3-Dimethyl-3,4,5,6-Tetrahydro-2(1H)-Pyrimidinone)',
            'pgmea': 'Propylene Glycol Methyl Ether Acetate',
            'nma': 'N-Methyl Acetamide',
            'gbl': 'gamma-Butyrolactone',
            'butyrolactone': 'gamma-Butyrolactone',
            'dioxane': '1,4-Dioxane',
            'pyridine': 'Pyridine',
            'dmpu': 'DMPU (1,3-Dimethyl-3,4,5,6-Tetrahydro-2(1H)-Pyrimidinone)',
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

        // ===================== FUZZY MATCH =====================
        function normalize(s) {{ return s.toLowerCase().replace(/[^a-z0-9]/g, ''); }}

        function resolveAlias(query, aliases) {{
            const q = query.toLowerCase().trim();
            if (aliases[q]) return aliases[q];
            // Try normalized
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
            // Try polymer first (for good/bad solvents context), then solvent
            const p = findPolymer(query);
            const s = findSolvent(query);
            return {{ polymer: p, solvent: s }};
        }}

        // ===================== RESULT COUNT =====================
        let resultCount = 25;

        function setResultCount(n) {{
            resultCount = n;
            document.querySelectorAll('.rc-btn').forEach(btn => {{
                btn.classList.toggle('active', parseInt(btn.textContent) === n);
            }});
        }}

        // ===================== CHAT STATE =====================
        let chatContext = null; // {{ intent, target, targetType }}
        let chatMessages = [];

        // ===================== NLP QUERY PARSER =====================
        function parseQuery(raw) {{
            const q = raw.toLowerCase().trim();

            // --- Multi-material detection ---
            // "good solvent for both cellulose and PVC"
            // "good solvent for silicone and bad solvent for epoxy"
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
            // "good solvent for both X and Y" or "good solvent for X and Y"
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
            // "dissolves both X and Y"
            const dissolvesBoth = q.match(/(?:dissolves?|dissolve)\s+(?:both\s+)?(.+?)\s+and\s+(.+)/i);
            if (dissolvesBoth) {{
                return {{ intent: 'multi_material', materials: [
                    {{ name: dissolvesBoth[1].replace(/[?.!]/g, '').trim(), requirement: 'good' }},
                    {{ name: dissolvesBoth[2].replace(/[?.!]/g, '').trim(), requirement: 'good' }},
                ]}};
            }}

            // --- Standard intent detection FIRST (takes priority over follow-ups) ---
            // This ensures "is NMP a good solvent for silicone" is parsed as a new
            // good_solvents query rather than a follow-up even when context exists.
            const hasStandardIntent = /good\s+solvent|bad\s+solvent|best\s+solvent|worst\s+solvent|poor\s+solvent|dissolve|compatible\s+with|incompatible|similar\s+to|close\s+to|solvents?\s+for|polymers?\s+for|polymers?\s+similar|solvents?\s+similar/i.test(q);

            // --- Follow-up detection (only if no standard intent detected) ---
            if (!hasStandardIntent && chatContext) {{
                const followUpPatterns = [
                    /^(?:what|how)\s+about\s+(.+)/i,
                    /^(?:and|also|try|check|test|evaluate)\s+(.+)/i,
                    /^(?:would)\s+(.+?)\s+(?:work)/i,
                ];
                for (const p of followUpPatterns) {{
                    const m = q.match(p);
                    if (m) {{
                        return {{ intent: 'followup', material: m[1].replace(/[?.!]/g, '').trim() }};
                    }}
                }}

                // If query is just material names (no intent keywords at all)
                const anyIntentWord = /good|bad|best|worst|similar|close|near|dissolve|compatible|incompatible|find|search|show|list|solvent|polymer/i;
                if (!anyIntentWord.test(q)) {{
                    return {{ intent: 'followup', material: q.replace(/[?.!]/g, '').trim() }};
                }}
            }}

            // --- Standard intent detection ---
            const badPatterns = [
                /bad\s+solvents?\s+for/i,
                /(?:poor|worst|incompatible)\s+solvents?\s+for/i,
                /solvents?\s+(?:that\s+)?(?:won'?t|will\s+not|cannot|can'?t)\s+dissolve/i,
                /(?:resist|resistant|insoluble)/i,
                /non[- ]?solvents?\s+for/i,
            ];
            const goodPatterns = [
                /good\s+solvents?\s+(for|to\s+dissolve)/i,
                /best\s+solvents?\s+for/i,
                /(?:what|which)\s+(?:solvents?\s+)?(?:dissolves?|will\s+dissolve|can\s+dissolve)/i,
                /solvents?\s+(?:that\s+)?(?:dissolves?|for|compatible\s+with)/i,
                /dissolve\s+/i,
                /compatible\s+solvents?\s+for/i,
                /soluble\s+in/i,
                /find\s+(?:me\s+)?(?:a\s+)?solvents?\s+for/i,
            ];
            const similarSolventPatterns = [
                /solvents?\s+(?:similar|close|near)\s+to/i,
                /(?:similar|close|near)\s+(?:to\s+)?(?:the\s+)?solvents?/i,
                /(?:alternatives?\s+to)\s+/i,
                /replace(?:ment)?\s+for\s+/i,
            ];
            const similarPolymerPatterns = [
                /polymers?\s+(?:similar|close|near)\s+to/i,
                /(?:similar|close|near)\s+(?:to\s+)?(?:the\s+)?polymers?/i,
                /materials?\s+(?:similar|close|near)\s+to/i,
            ];

            for (const p of badPatterns) {{
                if (p.test(q)) {{
                    return {{ intent: 'bad_solvents', material: q.replace(p, '').replace(/[?.!]/g, '').trim() }};
                }}
            }}
            for (const p of goodPatterns) {{
                if (p.test(q)) {{
                    return {{ intent: 'good_solvents', material: q.replace(p, '').replace(/[?.!]/g, '').trim() }};
                }}
            }}
            for (const p of similarPolymerPatterns) {{
                if (p.test(q)) {{
                    return {{ intent: 'similar_polymers', material: q.replace(p, '').replace(/[?.!]/g, '').trim() }};
                }}
            }}
            for (const p of similarSolventPatterns) {{
                if (p.test(q)) {{
                    return {{ intent: 'similar_solvents', material: q.replace(p, '').replace(/[?.!]/g, '').trim() }};
                }}
            }}

            // Fallback: check if query mentions a polymer name
            const polyMatch = findPolymer(q.replace(/[?.!]/g, ''));
            if (polyMatch) return {{ intent: 'good_solvents', material: q.replace(/[?.!]/g, '').trim() }};

            const solvMatch = findSolvent(q.replace(/[?.!]/g, ''));
            if (solvMatch) return {{ intent: 'similar_solvents', material: q.replace(/[?.!]/g, '').trim() }};

            return {{ intent: 'unknown', material: q }};
        }}

        // ===================== SEARCH ENGINE =====================
        function executeSearch(parsed) {{
            const {{ intent, material }} = parsed;

            // --- Follow-up: evaluate specific materials in current context ---
            if (intent === 'followup' && chatContext) {{
                // Split on "or", "and", commas, "/"
                const names = material.split(/\s+(?:or|and|,|\/)\s*|\s*[,\/]\s*/i).map(s => s.trim()).filter(Boolean);
                const results = [];

                for (const name of names) {{
                    if (chatContext.intent === 'good_solvents' || chatContext.intent === 'bad_solvents') {{
                        // Evaluate solvent(s) against the polymer target
                        const s = findSolvent(name);
                        if (s) {{
                            const ra = hspDistance(s, chatContext.target);
                            const red = redNumber(s, chatContext.target);
                            results.push({{ ...s, ra, red, queryName: name }});
                        }} else {{
                            // Maybe it's a polymer they want to compare
                            const p = findPolymer(name);
                            if (p) {{
                                const ra = hspDistance(p, chatContext.target);
                                results.push({{ ...p, ra, red: null, queryName: name, isPolymer: true }});
                            }} else {{
                                results.push({{ name: name, queryName: name, notFound: true }});
                            }}
                        }}
                    }} else if (chatContext.intent === 'similar_solvents') {{
                        const s = findSolvent(name);
                        if (s) {{
                            const ra = hspDistance(s, chatContext.target);
                            results.push({{ ...s, ra, queryName: name }});
                        }} else {{
                            results.push({{ name: name, queryName: name, notFound: true }});
                        }}
                    }} else if (chatContext.intent === 'similar_polymers') {{
                        const p = findPolymer(name);
                        if (p) {{
                            const ra = hspDistance(p, chatContext.target);
                            results.push({{ ...p, ra, queryName: name }});
                        }} else {{
                            results.push({{ name: name, queryName: name, notFound: true }});
                        }}
                    }}
                }}
                return {{ intent: 'followup', target: chatContext.target, results, description: 'Evaluating specific materials against ' + chatContext.target.name, targetType: chatContext.targetType, parentIntent: chatContext.intent }};
            }}

            // --- Multi-material search ---
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
                        if (t.requirement === 'good') {{
                            combinedScore += ra; // lower is better for good
                        }} else {{
                            combinedScore -= ra; // higher is better for bad
                        }}
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

            // --- Standard searches ---
            if (intent === 'good_solvents' || intent === 'bad_solvents') {{
                let target = findPolymer(material);
                if (!target) {{
                    const words = material.split(/\s+/);
                    for (const w of words) {{ target = findPolymer(w); if (target) break; }}
                }}
                if (!target) return {{ error: 'Could not find a matching polymer for "' + material + '". Try names like "polystyrene", "PVC", "PMMA", or "nylon".' }};

                const scored = SOLVENTS.map(s => ({{ ...s, ra: hspDistance(s, target), red: redNumber(s, target) }}));
                if (intent === 'good_solvents') {{
                    scored.sort((a, b) => a.ra - b.ra);
                    const results = scored.slice(0, resultCount);
                    chatContext = {{ intent, target, targetType: 'polymer' }};
                    return {{ intent, target, results, description: 'Top ' + resultCount + ' solvents by HSP distance (Ra). RED < 1 = inside solubility sphere = compatible.', targetType: 'polymer' }};
                }} else {{
                    scored.sort((a, b) => b.ra - a.ra);
                    const results = scored.slice(0, resultCount);
                    chatContext = {{ intent, target, targetType: 'polymer' }};
                    return {{ intent, target, results, description: 'Top ' + resultCount + ' most incompatible solvents by HSP distance (Ra). RED > 1 = outside sphere.', targetType: 'polymer' }};
                }}
            }}

            if (intent === 'similar_solvents') {{
                let target = findSolvent(material);
                if (!target) {{
                    const words = material.split(/\s+/);
                    for (const w of words) {{ target = findSolvent(w); if (target) break; }}
                }}
                if (!target) return {{ error: 'Could not find solvent "' + material + '". Try "toluene", "acetone", "NMP", "DMSO", etc.' }};

                const scored = SOLVENTS.filter(s => s.name !== target.name).map(s => ({{ ...s, ra: hspDistance(s, target) }}));
                scored.sort((a, b) => a.ra - b.ra);
                chatContext = {{ intent, target, targetType: 'solvent' }};
                return {{ intent, target, results: scored.slice(0, resultCount), description: 'Solvents closest to ' + target.name + ' in Hansen space.', targetType: 'solvent' }};
            }}

            if (intent === 'similar_polymers') {{
                let target = findPolymer(material);
                if (!target) {{
                    const words = material.split(/\s+/);
                    for (const w of words) {{ target = findPolymer(w); if (target) break; }}
                }}
                if (!target) return {{ error: 'Could not find polymer "' + material + '". Try "polystyrene", "epoxy", "PMMA", etc.' }};

                const scored = POLYMERS.filter(p => p.name !== target.name).map(p => ({{ ...p, ra: hspDistance(p, target) }}));
                scored.sort((a, b) => a.ra - b.ra);
                chatContext = {{ intent, target, targetType: 'polymer' }};
                return {{ intent, target, results: scored.slice(0, resultCount), description: 'Polymers closest to ' + target.name + ' in Hansen space.', targetType: 'polymer' }};
            }}

            return {{ error: 'Could not understand the query. Try "good solvents for polystyrene", "bad solvents for PVC", or "solvents similar to toluene".' }};
        }}

        // ===================== CHAT DISPLAY =====================
        function addChatMessage(type, html) {{
            const panel = document.getElementById('chat-panel');
            panel.classList.add('visible');
            const div = document.createElement('div');
            div.className = 'chat-msg ' + type;
            div.innerHTML = html;
            panel.appendChild(div);
            panel.scrollTop = panel.scrollHeight;
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
            // Update sort indicators
            tableEl.querySelectorAll('th').forEach((th, i) => {{
                th.classList.remove('sort-asc', 'sort-desc');
                if (i === colIdx) th.classList.add(dir === 1 ? 'sort-asc' : 'sort-desc');
            }});
        }}

        function renderResultsHTML(result) {{
            if (result.error) return '<span style="color:#EF553B">' + result.error + '</span>';

            const {{ intent, results, description }} = result;
            const target = result.target || (result.targets ? result.targets[0] : null);
            let titleText = '';
            const parentIntent = result.parentIntent || intent;
            if (intent === 'followup') titleText = 'Evaluating against';
            else if (intent === 'good_solvents') titleText = 'Best Solvents for';
            else if (intent === 'bad_solvents') titleText = 'Worst Solvents for';
            else if (intent === 'similar_solvents') titleText = 'Solvents Similar to';
            else if (intent === 'similar_polymers') titleText = 'Polymers Similar to';
            else if (intent === 'multi_material') titleText = 'Multi-Material Search';

            let html = '<strong>' + titleText + '</strong>';
            html += '<br><span style="color:#aaa;font-size:0.8rem">' + description + '</span>';

            // Context indicator
            if (chatContext && chatContext.target) {{
                html += '<br><span class="chat-context">Context: ' + chatContext.intent.replace(/_/g, ' ') + ' for ' + chatContext.target.name + '</span>';
            }}

            const isMulti = intent === 'multi_material';
            const showRed = parentIntent === 'good_solvents' || parentIntent === 'bad_solvents';

            // --- Target material table (with headers) ---
            const targetList = isMulti ? (result.targets || []) : (target ? [target] : []);
            if (targetList.length > 0 && intent !== 'followup') {{
                html += '<div style="margin-top:10px"><span style="color:#e94560;font-size:0.8rem;font-weight:600;text-transform:uppercase;letter-spacing:0.5px">Target Material' + (targetList.length > 1 ? 's' : '') + '</span></div>';
                html += '<table class="results-table" style="margin-bottom:16px"><thead><tr>';
                html += '<th>Name</th><th>CAS</th><th>&delta;D</th><th>&delta;P</th><th>&delta;H</th>';
                if (showRed || isMulti) {{
                    html += '<th>R&#8320;</th>';
                }}
                if (parentIntent === 'similar_solvents') {{
                    html += '<th>Category</th>';
                }} else if (parentIntent === 'similar_polymers') {{
                    html += '<th>R&#8320;</th><th>Type</th>';
                }}
                if (isMulti) {{
                    html += '<th>Requirement</th>';
                }}
                html += '</tr></thead><tbody>';
                targetList.forEach(t => {{
                    const chipColor = (isMulti && t.requirement === 'bad') ? '#EF553B' : '#00CC96';
                    html += '<tr style="background:#0f3460">';
                    html += '<td><strong style="color:#e94560">' + t.name + '</strong></td>';
                    html += '<td>' + (t.cas || '') + '</td>';
                    html += '<td>' + (t.dd != null ? t.dd.toFixed(1) : '') + '</td>';
                    html += '<td>' + (t.dp != null ? t.dp.toFixed(1) : '') + '</td>';
                    html += '<td>' + (t.dh != null ? t.dh.toFixed(1) : '') + '</td>';
                    if (showRed || isMulti) {{
                        html += '<td>' + (t.r || '') + '</td>';
                    }}
                    if (parentIntent === 'similar_solvents') {{
                        html += '<td>' + (t.cat || '') + '</td>';
                    }} else if (parentIntent === 'similar_polymers') {{
                        html += '<td>' + (t.r || '') + '</td>';
                        html += '<td>' + (t.type || '') + '</td>';
                    }}
                    if (isMulti) {{
                        html += '<td><span style="display:inline-block;background:' + chipColor + ';color:white;padding:2px 10px;border-radius:12px;font-size:0.8rem;font-weight:600">' + t.requirement + '</span></td>';
                    }}
                    html += '</tr>';
                }});
                html += '</tbody></table>';
            }}

            // --- Candidate results table (with headers) ---
            const tableId = 'rt-' + Date.now();
            html += '<div><span style="color:#e94560;font-size:0.8rem;font-weight:600;text-transform:uppercase;letter-spacing:0.5px">Candidate ' + (parentIntent === 'similar_polymers' ? 'Polymers' : 'Solvents') + ' (' + results.length + ')</span></div>';
            html += '<table class="results-table" id="' + tableId + '"><thead><tr>';

            // Build sortable headers
            let colNum = 0;
            const th = (label) => '<th onclick="sortResultsTable(this.closest(\\x27table\\x27),' + (colNum++) + ')" style="cursor:pointer">' + label + '</th>';
            html += th('#') + th('Name') + th('CAS') + th('&delta;D') + th('&delta;P') + th('&delta;H');

            if (isMulti) {{
                result.targets.forEach(t => {{
                    html += th('Ra(' + t.name.slice(0, 15) + ')');
                    html += th('RED(' + t.name.slice(0, 15) + ')');
                }});
            }} else if (showRed) {{
                html += th('Ra') + th('RED');
            }} else if (parentIntent === 'similar_solvents') {{
                html += th('Ra') + th('Category');
            }} else {{
                html += th('Ra') + th('R&#8320;') + th('Type');
            }}
            html += '</tr></thead><tbody>';

            results.forEach((r, i) => {{
                if (r.notFound) {{
                    html += '<tr><td class="rank">' + (i + 1) + '</td><td colspan="8" style="color:#EF553B">Could not find "' + r.queryName + '" in the database</td></tr>';
                    return;
                }}
                const nameHtml = '<span class="hoverable-name" onclick="highlightInPlot(\\x27' + encodeURIComponent(r.name) + '\\x27)" onmouseenter="showStructure(event,\\x27' + encodeURIComponent(r.name) + '\\x27)" onmouseleave="hideStructure()">' + r.name + '</span>';
                html += '<tr>';
                html += '<td class="rank">' + (i + 1) + '</td>';
                html += '<td>' + nameHtml + '</td>';
                html += '<td>' + (r.cas || '') + '</td>';
                html += '<td>' + (r.dd != null ? r.dd.toFixed(1) : '') + '</td>';
                html += '<td>' + (r.dp != null ? r.dp.toFixed(1) : '') + '</td>';
                html += '<td>' + (r.dh != null ? r.dh.toFixed(1) : '') + '</td>';

                if (isMulti) {{
                    result.targets.forEach(t => {{
                        const ra = r.ras[t.name];
                        const red = r.reds[t.name];
                        html += '<td>' + (ra != null ? ra.toFixed(2) : '') + '</td>';
                        let cls = 'red-bad';
                        if (red !== null && red !== undefined) {{
                            if (red < 1) cls = 'red-good';
                            else if (red < 1.2) cls = 'red-boundary';
                        }}
                        html += '<td class="' + cls + '">' + (red != null ? red.toFixed(2) : 'N/A') + '</td>';
                    }});
                }} else {{
                    html += '<td>' + (r.ra != null ? r.ra.toFixed(2) : '') + '</td>';
                    if (showRed) {{
                        const red = r.red;
                        let cls = 'red-bad';
                        if (red !== null) {{
                            if (red < 1) cls = 'red-good';
                            else if (red < 1.2) cls = 'red-boundary';
                        }}
                        html += '<td class="' + cls + '">' + (red !== null ? red.toFixed(2) : 'N/A') + '</td>';
                    }} else if (parentIntent === 'similar_solvents') {{
                        html += '<td>' + (r.cat || '') + '</td>';
                    }} else {{
                        html += '<td>' + (r.r || '') + '</td>';
                        html += '<td>' + (r.type || '') + '</td>';
                    }}
                }}
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
            return {{
                scene: {{
                    xaxis: {{ title: 'δD (Dispersion) MPa½', range: [12, 22] }},
                    yaxis: {{ title: 'δP (Polar) MPa½', range: [0, 28] }},
                    zaxis: {{ title: 'δH (H-bonding) MPa½', range: [0, 45] }},
                }},
                template: 'plotly_dark',
                paper_bgcolor: '#1a1a2e', plot_bgcolor: '#1a1a2e',
                margin: {{ l: 0, r: 0, t: 40, b: 0 }},
                legend: {{ x: 0.01, y: 0.99, bgcolor: 'rgba(0,0,0,0.5)' }},
                title: {{ text: title || 'Materialism — Hansen Solubility Parameter Space', x: 0.5, font: {{ size: 18 }} }},
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

            showTab('plot');
            const traces = [];

            // Dimmed background
            traces.push({{
                type: 'scatter3d', mode: 'markers', name: 'All Solvents',
                x: SOLVENTS.map(s => s.dd), y: SOLVENTS.map(s => s.dp), z: SOLVENTS.map(s => s.dh),
                text: SOLVENTS.map(s => s.name),
                hovertemplate: '<b>%{{text}}</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>',
                marker: {{ size: 3, color: '#444', opacity: 0.15 }},
            }});
            traces.push({{
                type: 'scatter3d', mode: 'markers', name: 'All Polymers',
                x: POLYMERS.map(p => p.dd), y: POLYMERS.map(p => p.dp), z: POLYMERS.map(p => p.dh),
                text: POLYMERS.map(p => p.name),
                hovertemplate: '<b>%{{text}}</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>',
                marker: {{ size: 4, color: '#665500', symbol: 'diamond', opacity: 0.15 }},
            }});

            // Valid results only
            const valid = results.filter(r => !r.notFound);

            if (isMulti) {{
                // Multi-material: color by best combined RED
                const resultColors = valid.map(r => {{
                    const reds = result.targets.map(t => r.reds[t.name]).filter(v => v != null);
                    const allGood = result.targets.every(t => {{
                        const red = r.reds[t.name];
                        return t.requirement === 'good' ? (red != null && red < 1) : (red != null && red > 1);
                    }});
                    if (allGood) return '#00CC96';
                    const anyBoundary = result.targets.some(t => {{
                        const red = r.reds[t.name];
                        return t.requirement === 'good' ? (red != null && red < 1.2) : (red != null && red > 0.8);
                    }});
                    if (anyBoundary) return '#FFA15A';
                    return '#EF553B';
                }});
                traces.push({{
                    type: 'scatter3d', mode: 'markers+text', name: 'Results',
                    x: valid.map(r => r.dd), y: valid.map(r => r.dp), z: valid.map(r => r.dh),
                    text: valid.map((r, i) => (i + 1) + '. ' + r.name),
                    textposition: 'top center', textfont: {{ size: 9, color: '#fff' }},
                    hovertemplate: valid.map((r, i) => {{
                        let h = '<b>' + (i+1) + '. ' + r.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}';
                        result.targets.forEach(t => {{
                            const red = r.reds[t.name];
                            h += '<br>' + t.name.slice(0, 20) + ': RED=' + (red != null ? red.toFixed(2) : 'N/A');
                        }});
                        return h + '<extra></extra>';
                    }}),
                    marker: {{ size: 10, color: resultColors, opacity: 1, line: {{ color: '#fff', width: 1 }} }},
                }});
                // Multiple target polymers with different colored spheres
                const tgtColors = ['#e94560', '#3A86FF', '#06D6A0', '#FFBE0B'];
                const sphereColors = [
                    'rgba(233,69,96,0.2)', 'rgba(58,134,255,0.2)',
                    'rgba(6,214,160,0.2)', 'rgba(255,190,11,0.2)',
                ];
                result.targets.forEach((tgt, ti) => {{
                    const c = tgtColors[ti % tgtColors.length];
                    traces.push({{
                        type: 'scatter3d', mode: 'markers+text',
                        name: (tgt.requirement === 'good' ? '✓ ' : '✗ ') + tgt.name,
                        x: [tgt.dd], y: [tgt.dp], z: [tgt.dh],
                        text: [tgt.name], textposition: 'top center',
                        textfont: {{ size: 12, color: c }},
                        hovertemplate: '<b>' + tgt.name + '</b> (' + tgt.requirement + ')<br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<br>R₀=' + tgt.r + '<extra></extra>',
                        marker: {{ size: 14, color: c, symbol: 'diamond', opacity: 1, line: {{ color: '#fff', width: 2 }} }},
                    }});
                    addSphere(traces, tgt, sphereColors[ti % sphereColors.length]);
                }});
            }} else if (parentIntent === 'good_solvents' || parentIntent === 'bad_solvents') {{
                const resultColors = valid.map(r => {{
                    if (r.red === null) return '#888';
                    if (r.red < 1) return '#00CC96';
                    if (r.red < 1.2) return '#FFA15A';
                    return '#EF553B';
                }});
                traces.push({{
                    type: 'scatter3d', mode: 'markers+text', name: 'Results',
                    x: valid.map(r => r.dd), y: valid.map(r => r.dp), z: valid.map(r => r.dh),
                    text: valid.map((r, i) => (i + 1) + '. ' + r.name),
                    textposition: 'top center', textfont: {{ size: 9, color: '#fff' }},
                    hovertemplate: valid.map((r, i) =>
                        '<b>' + (i+1) + '. ' + r.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<br>Ra=' + r.ra.toFixed(2) +
                        (r.red !== null ? '<br>RED=' + r.red.toFixed(2) : '') + '<extra></extra>'),
                    marker: {{ size: 10, color: resultColors, opacity: 1, line: {{ color: '#fff', width: 1 }} }},
                }});
                // Target polymer
                traces.push({{
                    type: 'scatter3d', mode: 'markers+text', name: 'Target: ' + target.name,
                    x: [target.dd], y: [target.dp], z: [target.dh],
                    text: [target.name], textposition: 'top center', textfont: {{ size: 12, color: '#e94560' }},
                    hovertemplate: '<b>' + target.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<br>R₀=' + target.r + '<extra></extra>',
                    marker: {{ size: 14, color: '#e94560', symbol: 'diamond', opacity: 1, line: {{ color: '#fff', width: 2 }} }},
                }});
                addSphere(traces, target, 'rgba(233,69,96,0.2)');
            }} else {{
                const colors = ['#FF006E', '#FB5607', '#FF006E', '#FFBE0B', '#3A86FF',
                                '#8338EC', '#06D6A0', '#118AB2', '#EF476F', '#FFD166'];
                const sym = (parentIntent === 'similar_polymers') ? 'diamond' : 'circle';
                traces.push({{
                    type: 'scatter3d', mode: 'markers+text', name: 'Results',
                    x: valid.map(r => r.dd), y: valid.map(r => r.dp), z: valid.map(r => r.dh),
                    text: valid.map((r, i) => (i + 1) + '. ' + r.name),
                    textposition: 'top center', textfont: {{ size: 9, color: '#fff' }},
                    hovertemplate: valid.map((r, i) =>
                        '<b>' + (i+1) + '. ' + r.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<br>Ra=' + r.ra.toFixed(2) + '<extra></extra>'),
                    marker: {{ size: 10, color: colors.slice(0, valid.length), symbol: sym, opacity: 1, line: {{ color: '#fff', width: 1 }} }},
                }});
                const tsym = (parentIntent === 'similar_polymers') ? 'diamond' : 'circle';
                traces.push({{
                    type: 'scatter3d', mode: 'markers+text', name: 'Target: ' + target.name,
                    x: [target.dd], y: [target.dp], z: [target.dh],
                    text: [target.name], textposition: 'top center', textfont: {{ size: 12, color: '#e94560' }},
                    hovertemplate: '<b>' + target.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>',
                    marker: {{ size: 14, color: '#e94560', symbol: tsym, opacity: 1, line: {{ color: '#fff', width: 2 }} }},
                }});
            }}

            const plotTitle = isMulti
                ? 'Multi-Material Search'
                : 'Search Results — ' + target.name;
            Plotly.react(plotDiv, traces, defaultLayout(plotTitle));
        }}

        function resetPlot() {{
            Plotly.react(plotDiv, fullTraces, defaultLayout());
        }}

        // ===================== HIGHLIGHT IN PLOT =====================
        let highlightTrace = null;
        function highlightInPlot(encodedName) {{
            const name = decodeURIComponent(encodedName);
            // Find the material in solvents or polymers
            let mat = SOLVENTS.find(s => s.name === name);
            let sym = 'circle';
            if (!mat) {{
                mat = POLYMERS.find(p => p.name === name);
                sym = 'diamond';
            }}
            if (!mat) return;

            showTab('plot');

            // Get current traces and remove any previous highlight trace
            const currentData = plotDiv.data.filter(t => t.name !== '★ Highlighted');
            const trace = {{
                type: 'scatter3d', mode: 'markers+text',
                name: '★ Highlighted',
                x: [mat.dd], y: [mat.dp], z: [mat.dh],
                text: ['★ ' + mat.name],
                textposition: 'top center',
                textfont: {{ size: 13, color: '#FFD700' }},
                hovertemplate: '<b>' + mat.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>',
                marker: {{ size: 18, color: '#FFD700', symbol: sym, opacity: 1,
                           line: {{ color: '#fff', width: 2 }} }},
            }};
            currentData.push(trace);
            const currentLayout = plotDiv.layout;
            Plotly.react(plotDiv, currentData, currentLayout);
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

            if (structCache[name] === 'error') {{
                tooltip.el.style.display = 'none';
                return;
            }}

            // Try to find the solvent's SMILES for lookup
            const solvent = SOLVENTS.find(s => s.name === name);
            const casNum = (solvent && solvent.cas) ? solvent.cas : null;

            // Build PubChem URL — prefer CAS for accuracy, fall back to name
            let url;
            if (casNum) {{
                url = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/' + encodeURIComponent(casNum) + '/PNG?image_size=200x200';
            }} else {{
                url = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/' + encodeURIComponent(name) + '/PNG?image_size=200x200';
            }}

            if (structCache[name]) {{
                tooltip.img.src = structCache[name];
                tooltip.el.classList.remove('loading');
            }} else {{
                tooltip.el.classList.add('loading');
                tooltip.img.src = url;
                tooltip.img.onload = function() {{
                    structCache[name] = url;
                    tooltip.el.classList.remove('loading');
                }};
                tooltip.img.onerror = function() {{
                    structCache[name] = 'error';
                    tooltip.el.style.display = 'none';
                }};
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
            input.value = '';

            addChatMessage('user', q);
            const parsed = parseQuery(q);
            const result = executeSearch(parsed);
            const html = renderResultsHTML(result);
            addChatMessage('system', html);

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
            resetPlot();
        }}

        function showTab(name) {{
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById('panel-' + name).classList.add('active');
            const tabs = document.querySelectorAll('.tab');
            const tabNames = ['plot', 'solvents', 'polymers', 'about'];
            const idx = tabNames.indexOf(name);
            if (idx >= 0 && tabs[idx]) tabs[idx].classList.add('active');
            if (name === 'plot') window.dispatchEvent(new Event('resize'));
        }}

        function filterTable(tableId, query) {{
            const rows = document.querySelectorAll('#' + tableId + ' tbody tr');
            const q = query.toLowerCase();
            rows.forEach(row => {{
                row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
            }});
        }}

        let sortDir = {{}};
        function sortTable(tableId, colIdx) {{
            const table = document.getElementById(tableId);
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.rows);
            const key = tableId + '-' + colIdx;
            sortDir[key] = !sortDir[key];
            const dir = sortDir[key] ? 1 : -1;
            rows.sort((a, b) => {{
                let va = a.cells[colIdx].textContent.trim();
                let vb = b.cells[colIdx].textContent.trim();
                const na = parseFloat(va), nb = parseFloat(vb);
                if (!isNaN(na) && !isNaN(nb)) return (na - nb) * dir;
                return va.localeCompare(vb) * dir;
            }});
            rows.forEach(row => tbody.appendChild(row));
        }}

        // ===================== INIT =====================
        document.addEventListener('DOMContentLoaded', buildFullPlot);
    </script>
</body>
</html>"""

output_path = os.path.join(os.path.dirname(__file__), "materialism.html")
with open(output_path, "w") as f:
    f.write(full_html)

print(f"Generated: {output_path}")
print(f"File size: {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")
print(f"Contains: {len(solvents)} solvents, {len(poly_data)} polymers")
