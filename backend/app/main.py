"""Materialism — Hansen Solubility Parameter Software

Main Dash application with:
- Interactive 3D Hansen space visualization
- Solvent search and filtering
- Mixture calculator
- Solubility sphere fitting
- Solvent blend optimizer
"""

import os
import sys

import dash
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, ctx, dash_table, dcc, html

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.models.database import (
    Chemical,
    Polymer,
    SolubilityTest,
    get_engine,
    get_session,
    init_db,
)
from backend.app.data.seed_data import seed_database
from backend.app.services.hsp_calculator import (
    fit_solubility_sphere,
    hsp_distance,
    mixture_hsp,
    optimize_blend,
    rank_solvents,
    red_number,
)

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "materialism.db")
engine = init_db(get_engine(DB_PATH))
session = get_session(engine)
seed_database(session)


def load_solvents_df():
    chemicals = session.query(Chemical).all()
    rows = []
    for c in chemicals:
        if c.has_hsp:
            rows.append({
                "id": c.id,
                "name": c.name,
                "cas_number": c.cas_number or "",
                "delta_d": c.delta_d,
                "delta_p": c.delta_p,
                "delta_h": c.delta_h,
                "molecular_weight": c.molecular_weight,
                "boiling_point": c.boiling_point,
                "density": c.density,
                "molar_volume": c.molar_volume,
                "category": c.category or "",
                "data_source": c.data_source or "",
            })
    return pd.DataFrame(rows)


def load_polymers_df():
    polymers = session.query(Polymer).all()
    rows = []
    for p in polymers:
        rows.append({
            "id": p.id,
            "name": p.name,
            "delta_d": p.delta_d,
            "delta_p": p.delta_p,
            "delta_h": p.delta_h,
            "radius": p.radius,
            "type": p.type or "",
        })
    return pd.DataFrame(rows)


SOLVENTS_DF = load_solvents_df()
POLYMERS_DF = load_polymers_df()

# Category color map
CATEGORY_COLORS = {
    "hydrocarbon": "#636EFA",
    "aromatic": "#EF553B",
    "halogenated": "#00CC96",
    "ether": "#AB63FA",
    "ketone": "#FFA15A",
    "ester": "#19D3F3",
    "alcohol": "#FF6692",
    "amide": "#B6E880",
    "sulfoxide": "#FF97FF",
    "acid": "#FECB52",
    "nitrile": "#1F77B4",
    "glycol ether": "#2CA02C",
    "amine": "#D62728",
    "terpene": "#9467BD",
    "inorganic": "#8C564B",
    "nitro": "#E377C2",
    "glycol": "#7F7F7F",
    "fluorinated": "#BCBD22",
    "heterocyclic": "#17BECF",
    "aldehyde": "#FF7F0E",
    "sulfur compound": "#AEC7E8",
    "other": "#888888",
}

# ---------------------------------------------------------------------------
# Dash App
# ---------------------------------------------------------------------------
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    suppress_callback_exceptions=True,
    title="Materialism — HSP Software",
)

# Register API blueprint for dataset management endpoints
try:
    from flask import request as flask_request
    from backend.app.routes.api import api_bp, manage_bp
    app.server.register_blueprint(api_bp)
    app.server.register_blueprint(manage_bp)

    # Dash registers _setup_server as a before_request hook on the Flask server.
    # This hook runs on EVERY request (including /api/*) and can return HTML errors
    # that break our JSON API endpoints. Patch it to skip API/manage routes.
    _original_setup = app._setup_server

    def _patched_setup():
        path = flask_request.path
        if path.startswith("/api/") or path in ("/manage", "/manage.html"):
            return None
        return _original_setup()

    # Replace in Flask's before_request list
    funcs = app.server.before_request_funcs.get(None, [])
    for i, fn in enumerate(funcs):
        if fn is _original_setup or getattr(fn, '__name__', '') == '_setup_server':
            funcs[i] = _patched_setup
            break
except ImportError:
    pass  # API routes not available (optional)

# ---- Sidebar ----
sidebar = dbc.Card(
    [
        dbc.CardHeader(html.H4("Materialism", className="mb-0")),
        dbc.CardBody([
            # Tabs for different modes
            dbc.Tabs(id="sidebar-tabs", active_tab="tab-explore", children=[
                dbc.Tab(label="Explore", tab_id="tab-explore"),
                dbc.Tab(label="Mixture", tab_id="tab-mixture"),
                dbc.Tab(label="Optimize", tab_id="tab-optimize"),
                dbc.Tab(label="Fit Sphere", tab_id="tab-fit"),
            ]),
            html.Div(id="sidebar-content", className="mt-3"),
        ]),
    ],
    className="h-100",
    style={"borderRadius": "0"},
)


def make_explore_sidebar():
    categories = sorted(SOLVENTS_DF["category"].unique())
    return html.Div([
        # Search
        dbc.Label("Search chemicals"),
        dbc.Input(id="search-input", placeholder="Name or CAS...", type="text",
                  className="mb-3"),

        # Category filter
        dbc.Label("Filter by category"),
        dbc.Checklist(
            id="category-filter",
            options=[{"label": c.title(), "value": c} for c in categories],
            value=categories,
            inline=False,
            className="mb-3",
            style={"maxHeight": "200px", "overflowY": "auto", "fontSize": "0.85rem"},
        ),

        html.Hr(),

        # Polymer overlay
        dbc.Label("Show polymer sphere"),
        dcc.Dropdown(
            id="polymer-dropdown",
            options=[{"label": row["name"], "value": row["id"]}
                     for _, row in POLYMERS_DF.iterrows()],
            placeholder="Select a polymer...",
            className="mb-3",
            style={"color": "#000"},
        ),

        # View controls
        dbc.Label("Projection"),
        dbc.RadioItems(
            id="projection-mode",
            options=[
                {"label": "3D", "value": "3d"},
                {"label": "δD vs δP", "value": "dp"},
                {"label": "δD vs δH", "value": "dh"},
                {"label": "δP vs δH", "value": "ph"},
            ],
            value="3d",
            inline=True,
            className="mb-3",
        ),

        # Stats
        html.Hr(),
        html.Div(id="stats-display"),
    ])


def make_mixture_sidebar():
    return html.Div([
        dbc.Label("Build a solvent mixture", className="fw-bold"),
        html.P("Select solvents and set volume fractions.", className="text-muted small"),

        # Solvent selectors (up to 5)
        *[html.Div([
            dbc.Row([
                dbc.Col(dcc.Dropdown(
                    id=f"mix-solvent-{i}",
                    options=[{"label": row["name"], "value": row["id"]}
                             for _, row in SOLVENTS_DF.iterrows()],
                    placeholder=f"Solvent {i+1}",
                    style={"color": "#000"},
                ), width=8),
                dbc.Col(dbc.Input(
                    id=f"mix-fraction-{i}",
                    type="number", min=0, max=100, step=1,
                    placeholder="%",
                ), width=4),
            ], className="mb-2")
        ]) for i in range(5)],

        dbc.Button("Calculate Mixture", id="calc-mixture-btn",
                    color="primary", className="mt-2 w-100"),
        html.Div(id="mixture-result", className="mt-3"),

        html.Hr(),
        # Compare against polymer
        dbc.Label("Compare mixture to polymer"),
        dcc.Dropdown(
            id="mixture-polymer-dropdown",
            options=[{"label": row["name"], "value": row["id"]}
                     for _, row in POLYMERS_DF.iterrows()],
            placeholder="Select a polymer...",
            style={"color": "#000"},
            className="mb-2",
        ),
        html.Div(id="mixture-comparison-result"),
    ])


def make_optimize_sidebar():
    return html.Div([
        dbc.Label("Solvent Blend Optimizer", className="fw-bold"),
        html.P("Find the best blend to match a target HSP.", className="text-muted small"),

        dbc.Label("Target (select a polymer or enter HSP)"),
        dcc.Dropdown(
            id="opt-target-dropdown",
            options=[{"label": row["name"], "value": row["id"]}
                     for _, row in POLYMERS_DF.iterrows()],
            placeholder="Select a polymer...",
            style={"color": "#000"},
            className="mb-2",
        ),
        html.Div("— or enter manually —", className="text-center text-muted small my-1"),
        dbc.Row([
            dbc.Col(dbc.Input(id="opt-dd", type="number", placeholder="δD", step=0.1), width=4),
            dbc.Col(dbc.Input(id="opt-dp", type="number", placeholder="δP", step=0.1), width=4),
            dbc.Col(dbc.Input(id="opt-dh", type="number", placeholder="δH", step=0.1), width=4),
        ], className="mb-2"),

        dbc.Label("Max components in blend"),
        dbc.Input(id="opt-n-components", type="number", value=3, min=1, max=8, step=1,
                  className="mb-2"),

        dbc.Label("Boiling point range (°C)"),
        dbc.Row([
            dbc.Col(dbc.Input(id="opt-min-bp", type="number", placeholder="Min"), width=6),
            dbc.Col(dbc.Input(id="opt-max-bp", type="number", placeholder="Max"), width=6),
        ], className="mb-2"),

        dbc.Button("Optimize", id="optimize-btn", color="success", className="mt-2 w-100"),
        html.Div(id="optimize-result", className="mt-3"),
    ])


def make_fit_sidebar():
    return html.Div([
        dbc.Label("Solubility Sphere Fitting", className="fw-bold"),
        html.P(
            "Enter solvents that dissolve (good) and don't dissolve (bad) your material. "
            "The algorithm will fit a sphere in Hansen space.",
            className="text-muted small",
        ),

        dbc.Label("Good solvents (dissolved)", className="text-success"),
        dcc.Dropdown(
            id="fit-good-solvents",
            options=[{"label": row["name"], "value": row["id"]}
                     for _, row in SOLVENTS_DF.iterrows()],
            multi=True,
            placeholder="Select good solvents...",
            style={"color": "#000"},
            className="mb-3",
        ),

        dbc.Label("Bad solvents (did not dissolve)", className="text-danger"),
        dcc.Dropdown(
            id="fit-bad-solvents",
            options=[{"label": row["name"], "value": row["id"]}
                     for _, row in SOLVENTS_DF.iterrows()],
            multi=True,
            placeholder="Select bad solvents...",
            style={"color": "#000"},
            className="mb-3",
        ),

        dbc.Button("Fit Sphere", id="fit-sphere-btn", color="warning", className="w-100"),
        html.Div(id="fit-result", className="mt-3"),
    ])


# ---- Main layout ----
app.layout = dbc.Container(
    fluid=True,
    className="p-0",
    style={"height": "100vh"},
    children=[
        dbc.Row(
            className="g-0 h-100",
            children=[
                # Sidebar
                dbc.Col(
                    sidebar,
                    width=3,
                    style={"height": "100vh", "overflowY": "auto"},
                ),
                # Main content
                dbc.Col(
                    [
                        # 3D plot
                        dcc.Graph(
                            id="hansen-plot",
                            style={"height": "60vh"},
                            config={"displayModeBar": True, "scrollZoom": True},
                        ),
                        # Data table
                        html.Div(
                            dash_table.DataTable(
                                id="chemicals-table",
                                columns=[
                                    {"name": "Name", "id": "name"},
                                    {"name": "CAS", "id": "cas_number"},
                                    {"name": "δD", "id": "delta_d", "type": "numeric"},
                                    {"name": "δP", "id": "delta_p", "type": "numeric"},
                                    {"name": "δH", "id": "delta_h", "type": "numeric"},
                                    {"name": "MW", "id": "molecular_weight", "type": "numeric"},
                                    {"name": "BP (°C)", "id": "boiling_point", "type": "numeric"},
                                    {"name": "Category", "id": "category"},
                                    {"name": "Ra", "id": "ra_distance", "type": "numeric"},
                                    {"name": "RED", "id": "red", "type": "numeric"},
                                ],
                                data=[],
                                page_size=15,
                                sort_action="native",
                                filter_action="native",
                                style_table={"overflowX": "auto"},
                                style_header={
                                    "backgroundColor": "#303030",
                                    "fontWeight": "bold",
                                    "color": "white",
                                },
                                style_cell={
                                    "backgroundColor": "#222",
                                    "color": "white",
                                    "border": "1px solid #444",
                                    "textAlign": "left",
                                    "padding": "8px",
                                    "fontSize": "13px",
                                },
                                style_data_conditional=[
                                    {
                                        "if": {"filter_query": "{red} < 1", "column_id": "red"},
                                        "color": "#00CC96",
                                        "fontWeight": "bold",
                                    },
                                    {
                                        "if": {"filter_query": "{red} >= 1", "column_id": "red"},
                                        "color": "#EF553B",
                                    },
                                ],
                            ),
                            style={"height": "40vh", "overflowY": "auto", "padding": "0 10px"},
                        ),
                    ],
                    width=9,
                ),
            ],
        ),

        # Hidden stores
        dcc.Store(id="fitted-sphere-store"),
        dcc.Store(id="mixture-hsp-store"),
    ],
)


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@callback(
    Output("sidebar-content", "children"),
    Input("sidebar-tabs", "active_tab"),
)
def render_sidebar_tab(tab):
    if tab == "tab-explore":
        return make_explore_sidebar()
    elif tab == "tab-mixture":
        return make_mixture_sidebar()
    elif tab == "tab-optimize":
        return make_optimize_sidebar()
    elif tab == "tab-fit":
        return make_fit_sidebar()
    return html.P("Select a tab")


@callback(
    Output("hansen-plot", "figure"),
    Output("chemicals-table", "data"),
    Output("stats-display", "children"),
    Input("search-input", "value"),
    Input("category-filter", "value"),
    Input("polymer-dropdown", "value"),
    Input("projection-mode", "value"),
    Input("fitted-sphere-store", "data"),
    Input("mixture-hsp-store", "data"),
    prevent_initial_call=False,
)
def update_main_view(search_text, categories, polymer_id, projection, fitted_sphere,
                     mixture_data):
    df = SOLVENTS_DF.copy()

    # Filter by category
    if categories:
        df = df[df["category"].isin(categories)]

    # Filter by search
    if search_text:
        mask = (
            df["name"].str.contains(search_text, case=False, na=False)
            | df["cas_number"].str.contains(search_text, case=False, na=False)
        )
        df = df[mask]

    # Get polymer data if selected
    poly_row = None
    if polymer_id:
        poly_row = POLYMERS_DF[POLYMERS_DF["id"] == polymer_id].iloc[0]

    # Compute distances and RED if polymer selected
    if poly_row is not None:
        target_hsp = (poly_row["delta_d"], poly_row["delta_p"], poly_row["delta_h"])
        radius = poly_row["radius"]
        df["ra_distance"] = df.apply(
            lambda r: round(hsp_distance(
                (r["delta_d"], r["delta_p"], r["delta_h"]), target_hsp
            ), 2), axis=1
        )
        df["red"] = df["ra_distance"].apply(lambda ra: round(ra / radius, 3) if radius else None)
    else:
        df["ra_distance"] = None
        df["red"] = None

    # Build figure
    if projection == "3d":
        fig = build_3d_figure(df, poly_row, fitted_sphere, mixture_data)
    else:
        fig = build_2d_figure(df, poly_row, projection, fitted_sphere, mixture_data)

    # Stats
    stats = html.Div([
        html.P(f"Showing {len(df)} chemicals", className="mb-1"),
        html.P(f"Database: {len(SOLVENTS_DF)} solvents, {len(POLYMERS_DF)} polymers",
               className="mb-1 text-muted small"),
    ])
    if poly_row is not None and len(df) > 0:
        n_inside = len(df[df["red"].notna() & (df["red"] < 1)])
        stats = html.Div([
            html.P(f"Showing {len(df)} chemicals", className="mb-1"),
            html.P([
                html.Span(f"{n_inside} compatible ", className="text-success"),
                html.Span(f"(RED < 1) with {poly_row['name']}"),
            ], className="mb-1"),
            html.P(f"Sphere: ({poly_row['delta_d']}, {poly_row['delta_p']}, "
                   f"{poly_row['delta_h']}), R₀={poly_row['radius']}",
                   className="mb-1 text-muted small"),
        ])

    return fig, df.to_dict("records"), stats


def build_3d_figure(df, poly_row=None, fitted_sphere=None, mixture_data=None):
    """Create the 3D Hansen space scatter plot."""
    fig = go.Figure()

    # Color by category
    for cat in df["category"].unique():
        cat_df = df[df["category"] == cat]
        color = CATEGORY_COLORS.get(cat, "#888")

        # Color by RED if polymer selected
        if poly_row is not None and "red" in cat_df.columns:
            marker_colors = []
            for _, row in cat_df.iterrows():
                red_val = row.get("red")
                if red_val is not None and red_val < 1:
                    marker_colors.append("#00CC96")  # Green = inside
                else:
                    marker_colors.append("#EF553B")  # Red = outside
        else:
            marker_colors = [color] * len(cat_df)

        fig.add_trace(go.Scatter3d(
            x=cat_df["delta_d"],
            y=cat_df["delta_p"],
            z=cat_df["delta_h"],
            mode="markers",
            name=cat.title(),
            text=cat_df["name"],
            hovertemplate=(
                "<b>%{text}</b><br>"
                "δD=%{x:.1f}, δP=%{y:.1f}, δH=%{z:.1f}"
                "<extra></extra>"
            ),
            marker=dict(size=5, color=marker_colors, opacity=0.85),
        ))

    # Polymer sphere
    if poly_row is not None:
        _add_sphere_to_fig(
            fig, poly_row["delta_d"], poly_row["delta_p"], poly_row["delta_h"],
            poly_row["radius"], poly_row["name"], color="rgba(255, 215, 0, 0.12)",
            line_color="rgba(255, 215, 0, 0.4)",
        )

    # Fitted sphere
    if fitted_sphere:
        c = fitted_sphere["center"]
        _add_sphere_to_fig(
            fig, c[0], c[1], c[2], fitted_sphere["radius"],
            f"Fitted (accuracy={fitted_sphere['fit_quality']})",
            color="rgba(0, 200, 255, 0.10)", line_color="rgba(0, 200, 255, 0.3)",
        )

    # Mixture point
    if mixture_data:
        fig.add_trace(go.Scatter3d(
            x=[mixture_data["delta_d"]],
            y=[mixture_data["delta_p"]],
            z=[mixture_data["delta_h"]],
            mode="markers",
            name="Mixture",
            marker=dict(size=12, color="#FF00FF", symbol="diamond"),
            hovertemplate=(
                f"<b>Mixture</b><br>"
                f"δD={mixture_data['delta_d']:.1f}, "
                f"δP={mixture_data['delta_p']:.1f}, "
                f"δH={mixture_data['delta_h']:.1f}"
                "<extra></extra>"
            ),
        ))

    fig.update_layout(
        scene=dict(
            xaxis_title="δD (Dispersion)",
            yaxis_title="δP (Polar)",
            zaxis_title="δH (H-bonding)",
            xaxis=dict(range=[12, 22]),
            yaxis=dict(range=[0, 28]),
            zaxis=dict(range=[0, 45]),
        ),
        template="plotly_dark",
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(0,0,0,0.5)"),
        title=dict(text="Hansen Solubility Parameter Space", x=0.5),
    )
    return fig


def _add_sphere_to_fig(fig, cx, cy, cz, r, name, color, line_color):
    """Add a transparent sphere to a 3D figure."""
    # Generate sphere mesh
    u = np.linspace(0, 2 * np.pi, 30)
    v = np.linspace(0, np.pi, 20)
    # The 4 in Ra² = 4(δD₁-δD₂)² means δD axis is scaled by 2
    # So the sphere is actually an ellipsoid in raw coordinates
    x = cx + (r / 2) * np.outer(np.cos(u), np.sin(v))
    y = cy + r * np.outer(np.sin(u), np.sin(v))
    z = cz + r * np.outer(np.ones_like(u), np.cos(v))

    fig.add_trace(go.Surface(
        x=x, y=y, z=z,
        opacity=0.15,
        colorscale=[[0, color], [1, color]],
        showscale=False,
        name=name,
        hoverinfo="name",
    ))


def build_2d_figure(df, poly_row=None, projection="dp", fitted_sphere=None,
                    mixture_data=None):
    """Create a 2D projection of Hansen space."""
    axis_map = {
        "dp": ("delta_d", "delta_p", "δD (Dispersion)", "δP (Polar)"),
        "dh": ("delta_d", "delta_h", "δD (Dispersion)", "δH (H-bonding)"),
        "ph": ("delta_p", "delta_h", "δP (Polar)", "δH (H-bonding)"),
    }
    x_col, y_col, x_label, y_label = axis_map[projection]

    fig = go.Figure()

    for cat in df["category"].unique():
        cat_df = df[df["category"] == cat]
        color = CATEGORY_COLORS.get(cat, "#888")

        if poly_row is not None and "red" in cat_df.columns:
            marker_colors = []
            for _, row in cat_df.iterrows():
                red_val = row.get("red")
                if red_val is not None and red_val < 1:
                    marker_colors.append("#00CC96")
                else:
                    marker_colors.append("#EF553B")
        else:
            marker_colors = [color] * len(cat_df)

        fig.add_trace(go.Scatter(
            x=cat_df[x_col],
            y=cat_df[y_col],
            mode="markers",
            name=cat.title(),
            text=cat_df["name"],
            hovertemplate="<b>%{text}</b><br>%{x:.1f}, %{y:.1f}<extra></extra>",
            marker=dict(size=8, color=marker_colors, opacity=0.85),
        ))

    # Draw circle for polymer sphere projection
    if poly_row is not None:
        theta = np.linspace(0, 2 * np.pi, 100)
        r = poly_row["radius"]
        if x_col == "delta_d":
            cx_vals = poly_row["delta_d"] + (r / 2) * np.cos(theta)
        else:
            cx_vals = poly_row[x_col] + r * np.cos(theta)
        if y_col == "delta_d":
            cy_vals = poly_row["delta_d"] + (r / 2) * np.sin(theta)
        else:
            cy_vals = poly_row[y_col] + r * np.sin(theta)

        fig.add_trace(go.Scatter(
            x=cx_vals, y=cy_vals, mode="lines",
            name=f"{poly_row['name']} sphere",
            line=dict(color="gold", width=2, dash="dash"),
        ))

    # Mixture point
    if mixture_data:
        fig.add_trace(go.Scatter(
            x=[mixture_data[x_col.replace("delta_", "delta_")]],
            y=[mixture_data[y_col.replace("delta_", "delta_")]],
            mode="markers",
            name="Mixture",
            marker=dict(size=15, color="#FF00FF", symbol="diamond"),
        ))

    fig.update_layout(
        xaxis_title=x_label,
        yaxis_title=y_label,
        template="plotly_dark",
        margin=dict(l=40, r=20, t=40, b=40),
        title=dict(text=f"Hansen Space — {x_label} vs {y_label}", x=0.5),
    )
    return fig


# --- Mixture calculator callback ---
@callback(
    Output("mixture-result", "children"),
    Output("mixture-comparison-result", "children"),
    Output("mixture-hsp-store", "data"),
    Input("calc-mixture-btn", "n_clicks"),
    State("mix-solvent-0", "value"),
    State("mix-fraction-0", "value"),
    State("mix-solvent-1", "value"),
    State("mix-fraction-1", "value"),
    State("mix-solvent-2", "value"),
    State("mix-fraction-2", "value"),
    State("mix-solvent-3", "value"),
    State("mix-fraction-3", "value"),
    State("mix-solvent-4", "value"),
    State("mix-fraction-4", "value"),
    State("mixture-polymer-dropdown", "value"),
    prevent_initial_call=True,
)
def calculate_mixture(n_clicks, s0, f0, s1, f1, s2, f2, s3, f3, s4, f4, polymer_id):
    components = []
    for sid, frac in [(s0, f0), (s1, f1), (s2, f2), (s3, f3), (s4, f4)]:
        if sid is not None and frac is not None and frac > 0:
            row = SOLVENTS_DF[SOLVENTS_DF["id"] == sid].iloc[0]
            hsp = (row["delta_d"], row["delta_p"], row["delta_h"])
            components.append((hsp, frac / 100.0))

    if not components:
        return html.P("Add at least one solvent.", className="text-warning"), "", None

    # Normalize fractions
    total = sum(f for _, f in components)
    components = [(hsp, f / total) for hsp, f in components]

    blend = mixture_hsp(components)

    result = dbc.Card([
        dbc.CardBody([
            html.H6("Mixture HSP"),
            html.P(f"δD = {blend[0]:.2f} MPa½"),
            html.P(f"δP = {blend[1]:.2f} MPa½"),
            html.P(f"δH = {blend[2]:.2f} MPa½"),
        ])
    ], color="info", outline=True)

    store_data = {"delta_d": blend[0], "delta_p": blend[1], "delta_h": blend[2]}

    # Compare with polymer
    comparison = ""
    if polymer_id:
        poly_row = POLYMERS_DF[POLYMERS_DF["id"] == polymer_id].iloc[0]
        target = (poly_row["delta_d"], poly_row["delta_p"], poly_row["delta_h"])
        ra = hsp_distance(blend, target)
        red = red_number(blend, target, poly_row["radius"])

        if red < 1:
            badge_color = "success"
            verdict = "COMPATIBLE"
        else:
            badge_color = "danger"
            verdict = "NOT COMPATIBLE"

        comparison = dbc.Card([
            dbc.CardBody([
                html.H6(f"vs {poly_row['name']}"),
                html.P(f"Ra = {ra:.2f} MPa½"),
                html.P(f"RED = {red:.3f}"),
                dbc.Badge(verdict, color=badge_color, className="fs-6"),
            ])
        ], color=badge_color, outline=True, className="mt-2")

    return result, comparison, store_data


# --- Optimizer callback ---
@callback(
    Output("optimize-result", "children"),
    Input("optimize-btn", "n_clicks"),
    State("opt-target-dropdown", "value"),
    State("opt-dd", "value"),
    State("opt-dp", "value"),
    State("opt-dh", "value"),
    State("opt-n-components", "value"),
    State("opt-min-bp", "value"),
    State("opt-max-bp", "value"),
    prevent_initial_call=True,
)
def run_optimizer(n_clicks, polymer_id, manual_dd, manual_dp, manual_dh,
                  n_components, min_bp, max_bp):
    # Determine target
    target_hsp = None
    target_radius = None
    if polymer_id:
        poly_row = POLYMERS_DF[POLYMERS_DF["id"] == polymer_id].iloc[0]
        target_hsp = (poly_row["delta_d"], poly_row["delta_p"], poly_row["delta_h"])
        target_radius = poly_row["radius"]
    elif manual_dd and manual_dp and manual_dh:
        target_hsp = (float(manual_dd), float(manual_dp), float(manual_dh))

    if target_hsp is None:
        return html.P("Select a polymer or enter target HSP values.", className="text-warning")

    constraints = {}
    if min_bp is not None:
        constraints["min_bp"] = float(min_bp)
    if max_bp is not None:
        constraints["max_bp"] = float(max_bp)

    solvents = SOLVENTS_DF.to_dict("records")
    result = optimize_blend(
        target_hsp, solvents,
        n_components=int(n_components or 3),
        target_radius=target_radius,
        constraints=constraints if constraints else None,
    )

    if not result or not result["components"]:
        return html.P("No feasible blend found.", className="text-danger")

    rows = []
    for comp in result["components"]:
        rows.append(html.Tr([
            html.Td(comp["name"]),
            html.Td(f"{comp['volume_fraction']*100:.1f}%"),
            html.Td(f"{comp['delta_d']:.1f}"),
            html.Td(f"{comp['delta_p']:.1f}"),
            html.Td(f"{comp['delta_h']:.1f}"),
        ]))

    return dbc.Card([
        dbc.CardBody([
            html.H6("Optimal Blend"),
            dbc.Table([
                html.Thead(html.Tr([
                    html.Th("Solvent"), html.Th("Vol%"), html.Th("δD"),
                    html.Th("δP"), html.Th("δH"),
                ])),
                html.Tbody(rows),
            ], bordered=True, dark=True, size="sm"),
            html.Hr(),
            html.P(f"Blend HSP: ({result['blend_hsp'][0]}, {result['blend_hsp'][1]}, "
                   f"{result['blend_hsp'][2]})"),
            html.P(f"Distance to target: {result['distance']:.3f} MPa½"),
            html.P(f"RED: {result.get('red', 'N/A')}", className=(
                "text-success" if result.get("red", 999) < 1 else "text-danger"
            )) if "red" in result else "",
        ])
    ], color="success", outline=True)


# --- Sphere fitting callback ---
@callback(
    Output("fit-result", "children"),
    Output("fitted-sphere-store", "data"),
    Input("fit-sphere-btn", "n_clicks"),
    State("fit-good-solvents", "value"),
    State("fit-bad-solvents", "value"),
    prevent_initial_call=True,
)
def run_sphere_fit(n_clicks, good_ids, bad_ids):
    if not good_ids or not bad_ids:
        return html.P("Select at least 1 good and 1 bad solvent.", className="text-warning"), None

    good_hsps = []
    for sid in good_ids:
        row = SOLVENTS_DF[SOLVENTS_DF["id"] == sid].iloc[0]
        good_hsps.append((row["delta_d"], row["delta_p"], row["delta_h"]))

    bad_hsps = []
    for sid in bad_ids:
        row = SOLVENTS_DF[SOLVENTS_DF["id"] == sid].iloc[0]
        bad_hsps.append((row["delta_d"], row["delta_p"], row["delta_h"]))

    result = fit_solubility_sphere(good_hsps, bad_hsps)

    card = dbc.Card([
        dbc.CardBody([
            html.H6("Fitted Solubility Sphere"),
            html.P(f"Center: δD={result['center'][0]}, δP={result['center'][1]}, "
                   f"δH={result['center'][2]}"),
            html.P(f"Radius R₀ = {result['radius']} MPa½"),
            html.P(f"Accuracy: {result['fit_quality']*100:.1f}%"),
            html.P(f"Misclassified: {result['misclassified_good']} good, "
                   f"{result['misclassified_bad']} bad "
                   f"(of {result['total_solvents']} total)"),
        ])
    ], color="warning", outline=True)

    return card, result


def main():
    print("\n  Materialism — Hansen Solubility Parameter Software")
    print(f"  Database: {len(SOLVENTS_DF)} solvents, {len(POLYMERS_DF)} polymers")
    print("  Starting server at http://localhost:8050\n")
    app.run(debug=True, host="0.0.0.0", port=8050)


if __name__ == "__main__":
    main()
