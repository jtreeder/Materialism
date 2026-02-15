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

# Build the 3D figure
fig = go.Figure()

for cat in sorted(set(s["cat"] for s in solvents)):
    cat_solvents = [s for s in solvents if s["cat"] == cat]
    color = CATEGORY_COLORS.get(cat, "#888")
    fig.add_trace(go.Scatter3d(
        x=[s["dd"] for s in cat_solvents],
        y=[s["dp"] for s in cat_solvents],
        z=[s["dh"] for s in cat_solvents],
        mode="markers",
        name=cat.title(),
        text=[f"{s['name']}<br>CAS: {s['cas']}<br>MW: {s['mw']}<br>BP: {s['bp']}°C"
              for s in cat_solvents],
        hovertemplate="<b>%{text}</b><br>δD=%{x:.1f}, δP=%{y:.1f}, δH=%{z:.1f}<extra></extra>",
        marker=dict(size=5, color=color, opacity=0.85),
    ))

# Add polymer points
fig.add_trace(go.Scatter3d(
    x=[p["dd"] for p in poly_data],
    y=[p["dp"] for p in poly_data],
    z=[p["dh"] for p in poly_data],
    mode="markers",
    name="Polymers",
    text=[f"{p['name']}<br>R₀={p['r']}" for p in poly_data],
    hovertemplate="<b>%{text}</b><br>δD=%{x:.1f}, δP=%{y:.1f}, δH=%{z:.1f}<extra></extra>",
    marker=dict(size=7, color="gold", symbol="diamond", opacity=0.95),
    visible=True,
))

# Add spheres for a few key polymers (buttons will toggle visibility)
sphere_traces_start = len(fig.data)
for p in poly_data:
    u = np.linspace(0, 2 * np.pi, 30)
    v = np.linspace(0, np.pi, 20)
    r = p["r"]
    x = p["dd"] + (r / 2) * np.outer(np.cos(u), np.sin(v))
    y = p["dp"] + r * np.outer(np.sin(u), np.sin(v))
    z = p["dh"] + r * np.outer(np.ones_like(u), np.cos(v))
    fig.add_trace(go.Surface(
        x=x, y=y, z=z,
        opacity=0.12,
        colorscale=[[0, "rgba(255,215,0,0.15)"], [1, "rgba(255,215,0,0.15)"]],
        showscale=False,
        name=f"Sphere: {p['name']}",
        hoverinfo="name",
        visible=False,  # Hidden by default
    ))

# Create dropdown buttons for polymer spheres
buttons = [dict(
    label="No sphere",
    method="update",
    args=[{"visible": [True] * sphere_traces_start + [False] * len(poly_data)}],
)]
for i, p in enumerate(poly_data):
    vis = [True] * sphere_traces_start + [False] * len(poly_data)
    vis[sphere_traces_start + i] = True
    buttons.append(dict(
        label=p["name"][:40],
        method="update",
        args=[{"visible": vis}],
    ))

fig.update_layout(
    scene=dict(
        xaxis_title="δD (Dispersion) MPa½",
        yaxis_title="δP (Polar) MPa½",
        zaxis_title="δH (H-bonding) MPa½",
        xaxis=dict(range=[12, 22]),
        yaxis=dict(range=[0, 28]),
        zaxis=dict(range=[0, 45]),
    ),
    template="plotly_dark",
    margin=dict(l=0, r=0, t=80, b=0),
    legend=dict(x=0.01, y=0.99, bgcolor="rgba(0,0,0,0.5)"),
    title=dict(
        text="Materialism — Hansen Solubility Parameter Space",
        x=0.5, font=dict(size=20),
    ),
    updatemenus=[dict(
        type="dropdown",
        direction="down",
        x=0.01, y=0.95,
        xanchor="left",
        bgcolor="#333",
        font=dict(color="white"),
        buttons=buttons,
        showactive=True,
    )],
    width=1400,
    height=800,
)

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

# Generate full HTML
plot_html = fig.to_html(include_plotlyjs=True, full_html=False)

full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Materialism — Hansen Solubility Parameters</title>
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
    </style>
</head>
<body>
    <div class="header">
        <h1>Materialism</h1>
        <div class="stats">{len(solvents)} solvents &middot; {len(poly_data)} polymers &middot; Hansen Solubility Parameters</div>
    </div>

    <div class="tabs">
        <div class="tab active" onclick="showTab('plot')">3D Hansen Space</div>
        <div class="tab" onclick="showTab('solvents')">Solvent Database</div>
        <div class="tab" onclick="showTab('polymers')">Polymer Database</div>
        <div class="tab" onclick="showTab('about')">How It Works</div>
    </div>

    <div id="panel-plot" class="panel active">
        <div class="plot-container">
            {plot_html}
        </div>
        <p style="color:#888; padding:10px; font-size:0.85rem;">
            Drag to rotate &middot; Scroll to zoom &middot; Use dropdown (top-left of plot) to show polymer solubility spheres &middot;
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

            <h3 style="margin-top:20px;">The 3D Plot</h3>
            <p>Each dot is a solvent positioned at its (δD, δP, δH) coordinates. Select a polymer
            from the dropdown to see its <strong>solubility sphere</strong> — any solvent inside the
            sphere should dissolve that polymer. The sphere appears as an ellipsoid because
            of the 4× weighting on the δD axis.</p>
        </div>
    </div>

    <script>
        function showTab(name) {{
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById('panel-' + name).classList.add('active');
            event.target.classList.add('active');
            // Trigger plotly resize when showing plot tab
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
    </script>
</body>
</html>"""

output_path = os.path.join(os.path.dirname(__file__), "materialism.html")
with open(output_path, "w") as f:
    f.write(full_html)

print(f"Generated: {output_path}")
print(f"File size: {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")
print(f"Contains: {len(solvents)} solvents, {len(poly_data)} polymers")
