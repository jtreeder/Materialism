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

solvents = []
for c in chemicals:
    if c.has_hsp:
        solvents.append({
            "name": c.name, "cas": c.cas_number or "",
            "dd": c.delta_d, "dp": c.delta_p, "dh": c.delta_h,
            "mw": c.molecular_weight, "bp": c.boiling_point,
            "cat": c.category or "other",
        })

poly_data = []
for p in polymers:
    poly_data.append({
        "name": p.name, "dd": p.delta_d, "dp": p.delta_p,
        "dh": p.delta_h, "r": p.radius, "type": p.type or "",
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

# --- Also build a data table as HTML ---
table_rows = ""
for s in sorted(solvents, key=lambda x: x["name"]):
    table_rows += f"""<tr>
        <td>{s['name']}</td><td>{s['cas']}</td>
        <td>{s['dd']}</td><td>{s['dp']}</td><td>{s['dh']}</td>
        <td>{s['mw'] or ''}</td><td>{s['bp'] or ''}</td>
        <td>{s['cat']}</td>
    </tr>"""

polymer_rows = ""
for p in sorted(poly_data, key=lambda x: x["name"]):
    polymer_rows += f"""<tr>
        <td>{p['name']}</td>
        <td>{p['dd']}</td><td>{p['dp']}</td><td>{p['dh']}</td>
        <td>{p['r']}</td><td>{p['type']}</td>
    </tr>"""

# Serialize data for JS embedding
solvents_json = json.dumps(solvents)
polymers_json = json.dumps(poly_data)
cat_colors_json = json.dumps(CATEGORY_COLORS)

# Generate full HTML — plot is now built client-side so we can dynamically update it
full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Materialism — Hansen Solubility Parameters</title>
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
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

        /* --- Search UI --- */
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
        .search-examples {{
            padding: 4px 20px 10px; background: #16213e; font-size: 0.8rem; color: #666;
            border-bottom: 2px solid #0f3460;
        }}
        .search-examples span {{
            cursor: pointer; color: #557; margin-right: 14px;
            transition: color 0.2s;
        }}
        .search-examples span:hover {{ color: #e94560; }}

        /* --- Results Panel --- */
        .results-panel {{
            display: none; margin: 10px 20px; padding: 16px; background: #16213e;
            border-radius: 8px; border: 1px solid #0f3460;
        }}
        .results-panel.visible {{ display: block; }}
        .results-header {{
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 12px;
        }}
        .results-header h3 {{ color: #e94560; font-size: 1rem; }}
        .results-close {{
            cursor: pointer; color: #888; font-size: 1.2rem; padding: 4px 8px;
            border-radius: 4px; transition: all 0.2s;
        }}
        .results-close:hover {{ color: #e94560; background: #1a1a2e; }}
        .results-description {{ color: #aaa; font-size: 0.85rem; margin-bottom: 12px; }}
        .results-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
        .results-table th {{
            background: #0f3460; color: #e94560; padding: 8px 10px;
            text-align: left; font-weight: 600;
        }}
        .results-table td {{ padding: 8px 10px; border-bottom: 1px solid #333; }}
        .results-table tr:hover {{ background: #1a1a2e; }}
        .results-table .rank {{ color: #e94560; font-weight: bold; }}
        .red-good {{ color: #00CC96; font-weight: bold; }}
        .red-boundary {{ color: #FFA15A; font-weight: bold; }}
        .red-bad {{ color: #EF553B; font-weight: bold; }}
        .target-chip {{
            display: inline-block; background: #e94560; color: white; padding: 2px 10px;
            border-radius: 12px; font-size: 0.8rem; font-weight: 600; margin-left: 8px;
        }}
        .results-reset {{
            margin-top: 10px; padding: 8px 16px; background: #333; color: #e0e0e0;
            border: 1px solid #555; border-radius: 6px; cursor: pointer; font-size: 0.85rem;
        }}
        .results-reset:hover {{ background: #444; border-color: #e94560; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Materialism</h1>
        <div class="stats">{len(solvents)} solvents &middot; {len(poly_data)} polymers &middot; Hansen Solubility Parameters</div>
    </div>

    <div class="search-bar">
        <input type="text" id="nl-search" placeholder="Ask anything — e.g. &quot;good solvents for polystyrene&quot; or &quot;solvents similar to toluene&quot;"
               onkeydown="if(event.key==='Enter')runSearch()">
        <button onclick="runSearch()">Search</button>
    </div>
    <div class="search-examples">
        Try:
        <span onclick="exampleSearch('good solvents for polystyrene')">good solvents for polystyrene</span>
        <span onclick="exampleSearch('bad solvents for PVC')">bad solvents for PVC</span>
        <span onclick="exampleSearch('solvents similar to toluene')">solvents similar to toluene</span>
        <span onclick="exampleSearch('polymers similar to epoxy')">polymers similar to epoxy</span>
        <span onclick="exampleSearch('what dissolves nylon')">what dissolves nylon</span>
    </div>

    <div id="results-panel" class="results-panel">
        <div class="results-header">
            <h3 id="results-title">Results</h3>
            <span class="results-close" onclick="closeResults()">&times; Close</span>
        </div>
        <div id="results-description" class="results-description"></div>
        <div id="results-body"></div>
        <button class="results-reset" onclick="closeResults()">Reset to full view</button>
    </div>

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
                    <th onclick="sortTable('solvent-table',2)">δD</th>
                    <th onclick="sortTable('solvent-table',3)">δP</th>
                    <th onclick="sortTable('solvent-table',4)">δH</th>
                    <th onclick="sortTable('solvent-table',5)">MW</th>
                    <th onclick="sortTable('solvent-table',6)">BP °C</th>
                    <th onclick="sortTable('solvent-table',7)">Category</th>
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
                    <th onclick="sortTable('polymer-table',1)">δD</th>
                    <th onclick="sortTable('polymer-table',2)">δP</th>
                    <th onclick="sortTable('polymer-table',3)">δH</th>
                    <th onclick="sortTable('polymer-table',4)">R₀</th>
                    <th onclick="sortTable('polymer-table',5)">Type</th>
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
                <li><strong>δD</strong> — Dispersion forces (van der Waals)</li>
                <li><strong>δP</strong> — Polar forces (dipole-dipole)</li>
                <li><strong>δH</strong> — Hydrogen bonding forces</li>
            </ul>
            <p>All measured in <strong>MPa½</strong>.</p>

            <h3 style="margin-top:20px;">The Distance Formula</h3>
            <p>Compatibility is predicted by the distance in Hansen space:</p>
            <p style="text-align:center; font-size:1.1em; margin:15px 0;">
                <code>Ra² = 4(δD₁ - δD₂)² + (δP₁ - δP₂)² + (δH₁ - δH₂)²</code>
            </p>
            <p>The factor of <strong>4</strong> on the dispersion term is empirical — it makes the 3D
            Hansen space approximately spherical for real solubility data.</p>

            <h3 style="margin-top:20px;">RED Number</h3>
            <p><code>RED = Ra / R₀</code> where R₀ is the solubility sphere radius.</p>
            <ul style="margin: 10px 0 10px 20px;">
                <li><span class="compatible">RED &lt; 1</span> — solvent is inside the sphere → <strong>compatible</strong></li>
                <li>RED = 1 — on the boundary</li>
                <li><span class="incompatible">RED &gt; 1</span> — outside the sphere → <strong>not compatible</strong></li>
            </ul>

            <h3 style="margin-top:20px;">Natural Language Search</h3>
            <p>Use the search bar at the top to ask questions in plain English. Examples:</p>
            <ul style="margin: 10px 0 10px 20px;">
                <li><strong>"good solvents for polystyrene"</strong> — finds solvents with low RED (inside solubility sphere)</li>
                <li><strong>"bad solvents for PVC"</strong> — finds solvents with high RED (outside sphere)</li>
                <li><strong>"solvents similar to toluene"</strong> — finds solvents closest in Hansen space</li>
                <li><strong>"polymers similar to epoxy"</strong> — finds polymers closest in Hansen space</li>
                <li><strong>"what dissolves nylon"</strong> — same as finding good solvents</li>
            </ul>
            <p>The 3D plot updates to show only the matched materials, highlighted in context.</p>

            <h3 style="margin-top:20px;">The 3D Plot</h3>
            <p>Each dot is a solvent positioned at its (δD, δP, δH) coordinates. Select a polymer
            from the dropdown to see its <strong>solubility sphere</strong> — any solvent inside the
            sphere should dissolve that polymer. The sphere appears as an ellipsoid because
            of the 4× weighting on the δD axis.</p>
        </div>
    </div>

    <script>
        // ===================== DATA =====================
        const SOLVENTS = {solvents_json};
        const POLYMERS = {polymers_json};
        const CAT_COLORS = {cat_colors_json};

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

        function fuzzyMatch(query, items, key) {{
            const q = normalize(query);
            if (!q) return null;
            let best = null, bestScore = 0;
            for (const item of items) {{
                const name = normalize(item[key || 'name']);
                let score = 0;
                // Exact match
                if (name === q) score = 1000;
                // Starts with
                else if (name.startsWith(q)) score = 500 + q.length;
                // Contains
                else if (name.includes(q)) score = 200 + q.length;
                // Query contains name
                else if (q.includes(name) && name.length > 2) score = 100 + name.length;
                // Word overlap
                else {{
                    const qWords = q.match(/.{{2,}}/g) || [];
                    for (const w of qWords) {{
                        if (name.includes(w)) score += 30 + w.length;
                    }}
                }}
                if (score > bestScore) {{ bestScore = score; best = item; }}
            }}
            return bestScore > 0 ? best : null;
        }}

        // ===================== NLP QUERY PARSER =====================
        function parseQuery(raw) {{
            const q = raw.toLowerCase().trim();
            // Detect intent
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
            const badPatterns = [
                /bad\s+solvents?\s+for/i,
                /(?:poor|worst|incompatible)\s+solvents?\s+for/i,
                /solvents?\s+(?:that\s+)?(?:won'?t|will\s+not|cannot|can'?t)\s+dissolve/i,
                /(?:resist|resistant|insoluble)/i,
                /non[- ]?solvents?\s+for/i,
            ];
            const similarSolventPatterns = [
                /solvents?\s+(?:similar|close|near)\s+to/i,
                /(?:similar|close|near)\s+(?:to\s+)?(?:the\s+)?solvents?/i,
                /(?:like|alternatives?\s+to)\s+/i,
                /replace(?:ment)?\s+for\s+/i,
            ];
            const similarPolymerPatterns = [
                /polymers?\s+(?:similar|close|near)\s+to/i,
                /(?:similar|close|near)\s+(?:to\s+)?(?:the\s+)?polymers?/i,
                /materials?\s+(?:similar|close|near)\s+to/i,
            ];

            // Try bad solvents first (more specific than good)
            for (const p of badPatterns) {{
                if (p.test(q)) {{
                    const material = q.replace(p, '').replace(/[?.!]/g, '').trim();
                    return {{ intent: 'bad_solvents', material }};
                }}
            }}
            for (const p of goodPatterns) {{
                if (p.test(q)) {{
                    const material = q.replace(p, '').replace(/[?.!]/g, '').trim();
                    return {{ intent: 'good_solvents', material }};
                }}
            }}
            for (const p of similarPolymerPatterns) {{
                if (p.test(q)) {{
                    const material = q.replace(p, '').replace(/[?.!]/g, '').trim();
                    return {{ intent: 'similar_polymers', material }};
                }}
            }}
            for (const p of similarSolventPatterns) {{
                if (p.test(q)) {{
                    const material = q.replace(p, '').replace(/[?.!]/g, '').trim();
                    return {{ intent: 'similar_solvents', material }};
                }}
            }}

            // Fallback: check if query mentions a polymer name → good solvents
            const polyMatch = fuzzyMatch(q.replace(/[?.!]/g, ''), POLYMERS, 'name');
            if (polyMatch) return {{ intent: 'good_solvents', material: q.replace(/[?.!]/g, '').trim() }};

            // Fallback: check if query mentions a solvent name → similar solvents
            const solvMatch = fuzzyMatch(q.replace(/[?.!]/g, ''), SOLVENTS, 'name');
            if (solvMatch) return {{ intent: 'similar_solvents', material: q.replace(/[?.!]/g, '').trim() }};

            return {{ intent: 'unknown', material: q }};
        }}

        // ===================== SEARCH ENGINE =====================
        function executeSearch(parsed) {{
            const {{ intent, material }} = parsed;
            let results = [];
            let target = null;
            let description = '';

            if (intent === 'good_solvents' || intent === 'bad_solvents') {{
                target = fuzzyMatch(material, POLYMERS, 'name');
                if (!target) {{
                    // Maybe they typed a solvent name and mean "for what polymer?"
                    // Try polymers harder with individual words
                    const words = material.split(/\s+/);
                    for (const w of words) {{
                        target = fuzzyMatch(w, POLYMERS, 'name');
                        if (target) break;
                    }}
                }}
                if (!target) return {{ error: 'Could not find a matching polymer for "' + material + '". Try a polymer name like "polystyrene", "PVC", or "nylon".' }};

                const scored = SOLVENTS.map(s => ({{
                    ...s, ra: hspDistance(s, target), red: redNumber(s, target)
                }}));

                if (intent === 'good_solvents') {{
                    scored.sort((a, b) => a.ra - b.ra);
                    results = scored.slice(0, 10);
                    description = 'Solvents ranked by HSP distance (Ra) — lowest = best compatibility. RED < 1 means inside the solubility sphere.';
                }} else {{
                    scored.sort((a, b) => b.ra - a.ra);
                    results = scored.slice(0, 10);
                    description = 'Solvents ranked by HSP distance (Ra) — highest = most incompatible. RED > 1 means outside the solubility sphere.';
                }}
                return {{ intent, target, results, description, targetType: 'polymer' }};
            }}

            if (intent === 'similar_solvents') {{
                target = fuzzyMatch(material, SOLVENTS, 'name');
                if (!target) {{
                    const words = material.split(/\s+/);
                    for (const w of words) {{
                        target = fuzzyMatch(w, SOLVENTS, 'name');
                        if (target) break;
                    }}
                }}
                if (!target) return {{ error: 'Could not find a matching solvent for "' + material + '". Try a solvent name like "toluene", "acetone", or "ethanol".' }};

                const scored = SOLVENTS.filter(s => s.name !== target.name).map(s => ({{
                    ...s, ra: hspDistance(s, target)
                }}));
                scored.sort((a, b) => a.ra - b.ra);
                results = scored.slice(0, 10);
                description = 'Solvents closest to ' + target.name + ' in Hansen space (lowest Ra = most similar).';
                return {{ intent, target, results, description, targetType: 'solvent' }};
            }}

            if (intent === 'similar_polymers') {{
                target = fuzzyMatch(material, POLYMERS, 'name');
                if (!target) {{
                    const words = material.split(/\s+/);
                    for (const w of words) {{
                        target = fuzzyMatch(w, POLYMERS, 'name');
                        if (target) break;
                    }}
                }}
                if (!target) return {{ error: 'Could not find a matching polymer for "' + material + '". Try "polystyrene", "epoxy", or "nylon".' }};

                const scored = POLYMERS.filter(p => p.name !== target.name).map(p => ({{
                    ...p, ra: hspDistance(p, target)
                }}));
                scored.sort((a, b) => a.ra - b.ra);
                results = scored.slice(0, 10);
                description = 'Polymers closest to ' + target.name + ' in Hansen space (lowest Ra = most similar).';
                return {{ intent, target, results, description, targetType: 'polymer' }};
            }}

            return {{ error: 'Could not understand the query. Try something like "good solvents for polystyrene" or "solvents similar to toluene".' }};
        }}

        // ===================== RESULTS DISPLAY =====================
        function displayResults(result) {{
            const panel = document.getElementById('results-panel');
            const title = document.getElementById('results-title');
            const desc = document.getElementById('results-description');
            const body = document.getElementById('results-body');

            if (result.error) {{
                title.innerHTML = 'No Results';
                desc.textContent = result.error;
                body.innerHTML = '';
                panel.classList.add('visible');
                return;
            }}

            const {{ intent, target, results, description }} = result;
            let titleText = '';
            if (intent === 'good_solvents') titleText = 'Best Solvents for';
            else if (intent === 'bad_solvents') titleText = 'Worst Solvents for';
            else if (intent === 'similar_solvents') titleText = 'Solvents Similar to';
            else if (intent === 'similar_polymers') titleText = 'Polymers Similar to';
            title.innerHTML = titleText + ' <span class="target-chip">' + target.name + '</span>';
            desc.textContent = description;

            let html = '<table class="results-table"><thead><tr>';
            html += '<th>#</th><th>Name</th><th>δD</th><th>δP</th><th>δH</th>';
            if (intent === 'good_solvents' || intent === 'bad_solvents') {{
                html += '<th>Ra</th><th>RED</th><th>Category</th>';
            }} else if (intent === 'similar_solvents') {{
                html += '<th>Ra</th><th>Category</th>';
            }} else {{
                html += '<th>Ra</th><th>R₀</th><th>Type</th>';
            }}
            html += '</tr></thead><tbody>';

            results.forEach((r, i) => {{
                html += '<tr>';
                html += '<td class="rank">' + (i + 1) + '</td>';
                html += '<td>' + r.name + '</td>';
                html += '<td>' + (r.dd != null ? r.dd.toFixed(1) : '') + '</td>';
                html += '<td>' + (r.dp != null ? r.dp.toFixed(1) : '') + '</td>';
                html += '<td>' + (r.dh != null ? r.dh.toFixed(1) : '') + '</td>';
                html += '<td>' + r.ra.toFixed(2) + '</td>';
                if (intent === 'good_solvents' || intent === 'bad_solvents') {{
                    const red = r.red;
                    let cls = 'red-bad';
                    if (red !== null) {{
                        if (red < 1) cls = 'red-good';
                        else if (red < 1.2) cls = 'red-boundary';
                    }}
                    html += '<td class="' + cls + '">' + (red !== null ? red.toFixed(2) : 'N/A') + '</td>';
                    html += '<td>' + (r.cat || '') + '</td>';
                }} else if (intent === 'similar_solvents') {{
                    html += '<td>' + (r.cat || '') + '</td>';
                }} else {{
                    html += '<td>' + (r.r || '') + '</td>';
                    html += '<td>' + (r.type || '') + '</td>';
                }}
                html += '</tr>';
            }});

            html += '</tbody></table>';
            body.innerHTML = html;
            panel.classList.add('visible');

            // Update 3D plot
            updatePlotWithResults(result);
        }}

        // ===================== 3D PLOT =====================
        let plotDiv;
        let fullTraces = [];  // stored once at init

        function buildFullPlot() {{
            plotDiv = document.getElementById('plotly-div');
            const traces = [];

            // Group solvents by category
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

            // Polymer points
            traces.push({{
                type: 'scatter3d', mode: 'markers',
                name: 'Polymers',
                x: POLYMERS.map(p => p.dd), y: POLYMERS.map(p => p.dp), z: POLYMERS.map(p => p.dh),
                text: POLYMERS.map(p => p.name + '<br>R₀=' + p.r),
                hovertemplate: '<b>%{{text}}</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>',
                marker: {{ size: 7, color: 'gold', symbol: 'diamond', opacity: 0.95 }},
            }});

            fullTraces = traces;

            const layout = {{
                scene: {{
                    xaxis: {{ title: 'δD (Dispersion) MPa½', range: [12, 22] }},
                    yaxis: {{ title: 'δP (Polar) MPa½', range: [0, 28] }},
                    zaxis: {{ title: 'δH (H-bonding) MPa½', range: [0, 45] }},
                }},
                template: 'plotly_dark',
                paper_bgcolor: '#1a1a2e',
                plot_bgcolor: '#1a1a2e',
                margin: {{ l: 0, r: 0, t: 40, b: 0 }},
                legend: {{ x: 0.01, y: 0.99, bgcolor: 'rgba(0,0,0,0.5)' }},
                title: {{ text: 'Materialism — Hansen Solubility Parameter Space', x: 0.5, font: {{ size: 18 }} }},
            }};

            Plotly.newPlot(plotDiv, traces, layout, {{ responsive: true }});
        }}

        function updatePlotWithResults(result) {{
            if (!result || result.error) return;
            const {{ intent, target, results, targetType }} = result;

            // Switch to plot tab
            showTab('plot');

            const traces = [];

            // Dimmed background: all solvents in grey
            traces.push({{
                type: 'scatter3d', mode: 'markers',
                name: 'All Solvents',
                x: SOLVENTS.map(s => s.dd), y: SOLVENTS.map(s => s.dp), z: SOLVENTS.map(s => s.dh),
                text: SOLVENTS.map(s => s.name),
                hovertemplate: '<b>%{{text}}</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>',
                marker: {{ size: 3, color: '#444', opacity: 0.2 }},
                showlegend: true,
            }});

            // Dimmed polymers
            traces.push({{
                type: 'scatter3d', mode: 'markers',
                name: 'All Polymers',
                x: POLYMERS.map(p => p.dd), y: POLYMERS.map(p => p.dp), z: POLYMERS.map(p => p.dh),
                text: POLYMERS.map(p => p.name),
                hovertemplate: '<b>%{{text}}</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>',
                marker: {{ size: 4, color: '#665500', symbol: 'diamond', opacity: 0.2 }},
                showlegend: true,
            }});

            // Highlighted results
            const colors = ['#FF006E', '#FB5607', '#FF006E', '#FFBE0B', '#3A86FF',
                            '#8338EC', '#06D6A0', '#118AB2', '#EF476F', '#FFD166'];
            if (intent === 'good_solvents' || intent === 'bad_solvents') {{
                // Color by RED
                const resultColors = results.map(r => {{
                    if (r.red === null) return '#888';
                    if (r.red < 1) return '#00CC96';
                    if (r.red < 1.2) return '#FFA15A';
                    return '#EF553B';
                }});
                traces.push({{
                    type: 'scatter3d', mode: 'markers+text',
                    name: 'Matched Solvents',
                    x: results.map(r => r.dd), y: results.map(r => r.dp), z: results.map(r => r.dh),
                    text: results.map((r, i) => (i + 1) + '. ' + r.name),
                    textposition: 'top center',
                    textfont: {{ size: 9, color: '#fff' }},
                    hovertemplate: results.map((r, i) =>
                        '<b>' + (i+1) + '. ' + r.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<br>Ra=' + r.ra.toFixed(2) +
                        (r.red !== null ? '<br>RED=' + r.red.toFixed(2) : '') + '<extra></extra>'
                    ),
                    marker: {{ size: 10, color: resultColors, opacity: 1, line: {{ color: '#fff', width: 1 }} }},
                }});

                // Target polymer as big star
                traces.push({{
                    type: 'scatter3d', mode: 'markers+text',
                    name: 'Target: ' + target.name,
                    x: [target.dd], y: [target.dp], z: [target.dh],
                    text: [target.name],
                    textposition: 'top center',
                    textfont: {{ size: 12, color: '#e94560' }},
                    hovertemplate: '<b>' + target.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<br>R₀=' + target.r + '<extra></extra>',
                    marker: {{ size: 14, color: '#e94560', symbol: 'diamond', opacity: 1, line: {{ color: '#fff', width: 2 }} }},
                }});

                // Solubility sphere for the target polymer
                if (target.r && target.r > 0) {{
                    const N = 30, M = 20;
                    const x = [], y = [], z = [];
                    for (let i = 0; i <= N; i++) {{
                        const xr = [], yr = [], zr = [];
                        const u = (i / N) * 2 * Math.PI;
                        for (let j = 0; j <= M; j++) {{
                            const v = (j / M) * Math.PI;
                            xr.push(target.dd + (target.r / 2) * Math.cos(u) * Math.sin(v));
                            yr.push(target.dp + target.r * Math.sin(u) * Math.sin(v));
                            zr.push(target.dh + target.r * Math.cos(v));
                        }}
                        x.push(xr); y.push(yr); z.push(zr);
                    }}
                    traces.push({{
                        type: 'surface', x, y, z,
                        opacity: 0.12,
                        colorscale: [[0, 'rgba(233,69,96,0.2)'], [1, 'rgba(233,69,96,0.2)']],
                        showscale: false,
                        name: 'Sphere: ' + target.name,
                        hoverinfo: 'name',
                    }});
                }}

            }} else if (intent === 'similar_solvents') {{
                traces.push({{
                    type: 'scatter3d', mode: 'markers+text',
                    name: 'Similar Solvents',
                    x: results.map(r => r.dd), y: results.map(r => r.dp), z: results.map(r => r.dh),
                    text: results.map((r, i) => (i + 1) + '. ' + r.name),
                    textposition: 'top center',
                    textfont: {{ size: 9, color: '#fff' }},
                    hovertemplate: results.map((r, i) =>
                        '<b>' + (i+1) + '. ' + r.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<br>Ra=' + r.ra.toFixed(2) + '<extra></extra>'
                    ),
                    marker: {{ size: 10, color: colors, opacity: 1, line: {{ color: '#fff', width: 1 }} }},
                }});
                // Target solvent
                traces.push({{
                    type: 'scatter3d', mode: 'markers+text',
                    name: 'Target: ' + target.name,
                    x: [target.dd], y: [target.dp], z: [target.dh],
                    text: [target.name],
                    textposition: 'top center',
                    textfont: {{ size: 12, color: '#e94560' }},
                    hovertemplate: '<b>' + target.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>',
                    marker: {{ size: 14, color: '#e94560', opacity: 1, line: {{ color: '#fff', width: 2 }} }},
                }});

            }} else if (intent === 'similar_polymers') {{
                traces.push({{
                    type: 'scatter3d', mode: 'markers+text',
                    name: 'Similar Polymers',
                    x: results.map(r => r.dd), y: results.map(r => r.dp), z: results.map(r => r.dh),
                    text: results.map((r, i) => (i + 1) + '. ' + r.name),
                    textposition: 'top center',
                    textfont: {{ size: 9, color: '#fff' }},
                    hovertemplate: results.map((r, i) =>
                        '<b>' + (i+1) + '. ' + r.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<br>Ra=' + r.ra.toFixed(2) + '<extra></extra>'
                    ),
                    marker: {{ size: 10, color: colors, symbol: 'diamond', opacity: 1, line: {{ color: '#fff', width: 1 }} }},
                }});
                // Target polymer
                traces.push({{
                    type: 'scatter3d', mode: 'markers+text',
                    name: 'Target: ' + target.name,
                    x: [target.dd], y: [target.dp], z: [target.dh],
                    text: [target.name],
                    textposition: 'top center',
                    textfont: {{ size: 12, color: '#e94560' }},
                    hovertemplate: '<b>' + target.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>',
                    marker: {{ size: 14, color: '#e94560', symbol: 'diamond', opacity: 1, line: {{ color: '#fff', width: 2 }} }},
                }});
            }}

            const layout = {{
                scene: {{
                    xaxis: {{ title: 'δD (Dispersion) MPa½' }},
                    yaxis: {{ title: 'δP (Polar) MPa½' }},
                    zaxis: {{ title: 'δH (H-bonding) MPa½' }},
                }},
                template: 'plotly_dark',
                paper_bgcolor: '#1a1a2e',
                plot_bgcolor: '#1a1a2e',
                margin: {{ l: 0, r: 0, t: 40, b: 0 }},
                legend: {{ x: 0.01, y: 0.99, bgcolor: 'rgba(0,0,0,0.5)' }},
                title: {{ text: 'Search Results — ' + target.name, x: 0.5, font: {{ size: 18 }} }},
            }};

            Plotly.react(plotDiv, traces, layout);
        }}

        function resetPlot() {{
            const layout = {{
                scene: {{
                    xaxis: {{ title: 'δD (Dispersion) MPa½', range: [12, 22] }},
                    yaxis: {{ title: 'δP (Polar) MPa½', range: [0, 28] }},
                    zaxis: {{ title: 'δH (H-bonding) MPa½', range: [0, 45] }},
                }},
                template: 'plotly_dark',
                paper_bgcolor: '#1a1a2e',
                plot_bgcolor: '#1a1a2e',
                margin: {{ l: 0, r: 0, t: 40, b: 0 }},
                legend: {{ x: 0.01, y: 0.99, bgcolor: 'rgba(0,0,0,0.5)' }},
                title: {{ text: 'Materialism — Hansen Solubility Parameter Space', x: 0.5, font: {{ size: 18 }} }},
            }};
            Plotly.react(plotDiv, fullTraces, layout);
        }}

        // ===================== UI GLUE =====================
        function runSearch() {{
            const input = document.getElementById('nl-search');
            const q = input.value.trim();
            if (!q) return;
            const parsed = parseQuery(q);
            const result = executeSearch(parsed);
            displayResults(result);
        }}

        function exampleSearch(text) {{
            document.getElementById('nl-search').value = text;
            runSearch();
        }}

        function closeResults() {{
            document.getElementById('results-panel').classList.remove('visible');
            resetPlot();
        }}

        function showTab(name) {{
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById('panel-' + name).classList.add('active');
            // Find the correct tab button
            const tabs = document.querySelectorAll('.tab');
            const tabNames = ['plot', 'solvents', 'polymers', 'about'];
            const idx = tabNames.indexOf(name);
            if (idx >= 0 && tabs[idx]) tabs[idx].classList.add('active');
            if (name === 'plot') {{ window.dispatchEvent(new Event('resize')); }}
        }}

        function filterTable(tableId, query) {{
            const rows = document.querySelectorAll('#' + tableId + ' tbody tr');
            const q = query.toLowerCase();
            rows.forEach(row => {{
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(q) ? '' : 'none';
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
