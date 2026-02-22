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

# Load data from CSV (unified output from build_unified.py)
CHEM_CSV = os.path.join(os.path.dirname(__file__), "data", "processed", "unified_chemicals.csv")
POLY_CSV = os.path.join(os.path.dirname(__file__), "data", "processed", "unified_polymers.csv")
MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "data", "manifest.json")

# Load manifest for dataset metadata
if os.path.exists(MANIFEST_PATH):
    with open(MANIFEST_PATH) as _mf:
        _manifest = json.load(_mf)
else:
    _manifest = {"version": 1, "datasets": {}}
DATASETS_META = _manifest.get("datasets", {})

# Source display name mapping
SOURCE_NAMES = {
    "handbook": "Hansen Handbook 2007",
    "hspip": "HSPiP Database",
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
        conf_val = row.get("confidence", "").strip()
        srcn_val = row.get("source_count", "").strip()
        solvents.append({
            "name": chem_name,
            "cas": chem_cas,
            "dd": float(dd), "dp": float(dp), "dh": float(dh),
            "mw": float(mw_val) if mw_val else None,
            "bp": float(bp_val) if bp_val else None,
            "cat": row.get("category", "other").strip() or "other",
            "smiles": row.get("smiles", "").strip(),
            "conf": float(conf_val) if conf_val else 0,
            "srcN": int(srcn_val) if srcn_val else 1,
            "src": SOURCE_NAMES.get(src_key, src_key),
            "srcUrl": src_url,
            "mwSrc": mw_src if mw_val else "",
            "bpSrc": bp_src if bp_val else "",
            "common": _is_common_solvent(chem_name, chem_cas),
            "dsId": row.get("dataset_id", "").strip(),
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
        pconf_val = row.get("confidence", "").strip()
        psrcn_val = row.get("source_count", "").strip()
        poly_data.append({
            "name": poly_name,
            "dd": float(dd), "dp": float(dp), "dh": float(dh),
            "r": float(r_val) if r_val else None,
            "type": row.get("type", "").strip(),
            "cas": row.get("cas_number", "").strip(),
            "conf": float(pconf_val) if pconf_val else 0,
            "srcN": int(psrcn_val) if psrcn_val else 1,
            "src": SOURCE_NAMES.get(src_key, src_key),
            "srcUrl": src_url,
            "common": _is_common_polymer(poly_name),
            "dsId": row.get("dataset_id", "").strip(),
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

# Broad polymer categories and their type-to-category mapping
POLYMER_TYPE_TO_CAT = {
    "Polyethylene": "Polyolefin", "Polypropylene": "Polyolefin",
    "Polyisobutylene": "Polyolefin", "Polybutadiene": "Polyolefin",
    "Polyisoprene": "Polyolefin", "Polyisoprene Swelling": "Polyolefin",
    "Permeation of LDPE by Organic Liquids": "Polyolefin",
    "Polyvinylchloride": "Vinyl & Styrene", "Polystyrene": "Vinyl & Styrene",
    "Polyvinylacetate": "Vinyl & Styrene", "Polyvinylbutyral": "Vinyl & Styrene",
    "Polyvinyl Alcohol": "Vinyl & Styrene", "Polyvinylpyrrolidone": "Vinyl & Styrene",
    "Vinyl Chloride Copolymers": "Vinyl & Styrene",
    "Vinyl Resins - Solvent Range": "Vinyl & Styrene",
    "Styrene-Butadiene (SBR)": "Vinyl & Styrene",
    "Styrene Polymers And Copolymers - Solvent Range": "Vinyl & Styrene",
    "Barex": "Vinyl & Styrene",
    "High Temperature Solubility of PVDC": "Vinyl & Styrene",
    "Ethylene Vinylacetate (EVA) Solubility": "Vinyl & Styrene",
    "Acrylate Resins": "Acrylic", "Acrylics": "Acrylic",
    "Acrylics - Solvent Range": "Acrylic", "Polyacrylate": "Acrylic",
    "Polyacrylonitrile": "Acrylic",
    "Solubility of Polyacrylonitirile": "Acrylic",
    "Acrylonitrile-Butadiene": "Acrylic", "Acrylic Modified Alkyd": "Acrylic",
    "Cellulose": "Cellulose", "Cellulose Acetate": "Cellulose",
    "Cellulose Acetobutyrate": "Cellulose", "Ethyl Cellulose": "Cellulose",
    "Nitrocellulose": "Cellulose",
    "Polyester": "Polyester & Alkyd",
    "Polyesters - Solvent Range": "Polyester & Alkyd",
    "Binders in Solution: Alkyds and Polyesters": "Polyester & Alkyd",
    "Epoxy": "Epoxy", "Epoxy Curing Agents": "Epoxy",
    "Polyamide": "Polyamide & Imide", "Polyimide": "Polyamide & Imide",
    "Polyetherimide": "Polyamide & Imide",
    "PEI - Polyethylene Imide - Environmental Stress Cracking (ESC)": "Polyamide & Imide",
    "Elastomer": "Rubber & Elastomer",
    "Chemical Resistance of Elastomers": "Rubber & Elastomer",
    "Bromobutyl Rubber Swelling": "Rubber & Elastomer",
    "Chlorinated Rubber": "Rubber & Elastomer",
    "Cyclized Rubber": "Rubber & Elastomer",
    "Chlorosulfonated PE": "Rubber & Elastomer",
    "Fluoropolymer": "Fluoropolymer",
    "Fluorinated Polyethers": "Fluoropolymer",
    "Poly(Ethylene/Chlorotrifluoroethylene)": "Fluoropolymer",
    "Polycarbonate": "Engineering", "Polyphenylene Oxide": "Engineering",
    "Polyphenylene Sulfide": "Engineering", "Polysulfone PSU": "Engineering",
    "Polyethersulfone": "Engineering", "COC Solubility": "Engineering",
    "Polyurethane": "Urethane", "Isocyanate": "Urethane",
    "Tolonate Solubility": "Urethane",
    "Natural": "Natural & Bio", "Rosin Derivatives": "Natural & Bio",
    "Biologically Interesting Systems": "Natural & Bio",
    "Polymers of Interest for Conservation of Paintings": "Natural & Bio",
    "Amino Resins": "Resin", "Phenolic Resins": "Resin",
    "Hydrocarbon Resins": "Resin", "Silicone Resins": "Resin",
    "Chlorinated Polypropylene": "Halogenated",
    "Chloroparaffin": "Halogenated",
}
# Everything not explicitly mapped falls to "Other"
POLYMER_CAT_COLORS = {
    "Polyolefin": "#4363d8", "Vinyl & Styrene": "#e6194B",
    "Acrylic": "#3cb44b", "Cellulose": "#ffe119",
    "Polyester & Alkyd": "#f58231", "Epoxy": "#911eb4",
    "Polyamide & Imide": "#42d4f4", "Rubber & Elastomer": "#f032e6",
    "Fluoropolymer": "#bfef45", "Engineering": "#fabed4",
    "Urethane": "#469990", "Natural & Bio": "#dcbeff",
    "Resin": "#9A6324", "Halogenated": "#aaffc3",
    "Other": "#a9a9a9",
}

# Assign category to each polymer
for p in poly_data:
    p["cat"] = POLYMER_TYPE_TO_CAT.get(p["type"], "Other")

# Serialize data for JS embedding
solvents_json = json.dumps(solvents)
polymers_json = json.dumps(poly_data)
cat_colors_json = json.dumps(CATEGORY_COLORS)
poly_cat_colors_json = json.dumps(POLYMER_CAT_COLORS)
datasets_meta_json = json.dumps(DATASETS_META)

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
        /* Hide native Plotly hover labels — all tooltips use scene annotations */
        .js-plotly-plot .hoverlayer .hovertext {{ display: none !important; visibility: hidden !important; }}
        th.sort-asc::after {{ content: ' ▲'; font-size: 0.7em; color: #e94560; }}
        th.sort-desc::after {{ content: ' ▼'; font-size: 0.7em; color: #e94560; }}
        .conf-tip {{
            display: none; position: fixed; z-index: 9999;
            background: #2d3436; color: #dfe6e9; border-radius: 6px; padding: 10px 14px;
            font-size: 0.75rem; line-height: 1.5; white-space: nowrap;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }}
        .conf-row {{ display: flex; justify-content: space-between; gap: 18px; }}
        .conf-row .conf-label {{ color: #b2bec3; }}
        .conf-row .conf-val {{ font-weight: 600; }}
        .conf-row .conf-val.pos {{ color: #00b894; }}
        .conf-row .conf-val.zero {{ color: #636e72; }}
        .conf-sep {{ border-top: 1px solid #636e72; margin: 4px 0; }}

        /* --- Custom Plot Legend --- */
        .plot-legend {{
            position: absolute; top: 8px; left: 8px; z-index: 10;
            background: rgba(255,255,255,0.92); border: 1px solid #dfe6e9;
            border-radius: 6px; padding: 6px 0; font-size: 0.75rem;
            max-height: calc(100% - 60px); overflow-y: auto;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08); min-width: 140px;
            scrollbar-width: thin;
        }}
        .plot-legend::-webkit-scrollbar {{ width: 4px; }}
        .plot-legend::-webkit-scrollbar-thumb {{ background: #dfe6e9; border-radius: 2px; }}
        .legend-group {{
            padding: 0;
        }}
        .legend-header {{
            display: flex; align-items: center; gap: 6px; padding: 4px 10px;
            cursor: pointer; user-select: none; font-weight: 600; color: #2d3436;
        }}
        .legend-header:hover {{ background: #f5f6fa; }}
        .legend-arrow {{
            display: inline-block; width: 10px; font-size: 0.6rem; color: #636e72;
            transition: transform 0.15s;
        }}
        .legend-arrow.open {{ transform: rotate(90deg); }}
        .legend-marker {{
            display: inline-block; width: 10px; height: 10px; border-radius: 50%;
            flex-shrink: 0;
        }}
        .legend-marker.diamond {{
            border-radius: 0; transform: rotate(45deg); width: 9px; height: 9px;
        }}
        .legend-items {{
            display: none; padding: 0;
        }}
        .legend-items.open {{
            display: block;
        }}
        .legend-item {{
            display: flex; align-items: center; gap: 6px;
            padding: 2px 10px 2px 26px; color: #636e72; font-size: 0.7rem;
        }}
        .legend-item:hover {{ background: #f5f6fa; }}
        .legend-swatch {{
            display: inline-block; width: 8px; height: 8px; border-radius: 50%;
            flex-shrink: 0;
        }}
        .legend-swatch.diamond {{
            border-radius: 0; transform: rotate(45deg); width: 7px; height: 7px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1 onclick="goHome()">Materialism</h1>
        <div class="stats"><a href="manage.html" style="color:#636e72;text-decoration:none;border-bottom:1px dotted #b2bec3;cursor:pointer;margin-right:12px">Manage</a><a href="database.html" style="color:#636e72;text-decoration:none;border-bottom:1px dotted #b2bec3;cursor:pointer">Database</a></div>
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
        <div id="ds-toggle-wrap" style="margin-left:auto;display:flex;align-items:center;gap:6px;font-size:0.8rem;color:#636e72;"></div>
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
            <div class="plot-container" style="position:relative;">
                <div id="plotly-div" style="width:100%; height:100%;"></div>
                <div id="plot-legend" class="plot-legend"></div>
            </div>
            <p style="color:#636e72; padding:6px 10px; font-size:0.8rem; margin:0;">
                Drag to rotate &middot; Scroll to zoom &middot; Diamonds = polymers, dots = solvents
            </p>
        </div>
        <div id="chat-panel" class="chat-panel"></div>
        <div id="home-panel" class="home-panel">
            <div class="home-panel-header">
                <input type="text" id="home-filter" placeholder="Filter by name..." oninput="filterHomeTable(this.value)" style="width:180px;font-size:0.8rem;">
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
        const DATASETS_META = {datasets_meta_json};
        // O(1) lookup maps for materials by name
        const _solventMap = new Map(SOLVENTS.map(s => [s.name, s]));
        const _polymerMap = new Map(POLYMERS.map(p => [p.name, p]));
        const CAT_COLORS = {cat_colors_json};
        const POLY_CAT_COLORS = {poly_cat_colors_json};

        // Dataset toggle state (shared via localStorage with database.html)
        const _LS_DS_KEY = 'materialism_active_datasets';
        function _loadActiveDsets() {{
            try {{ var v = localStorage.getItem(_LS_DS_KEY); return v ? JSON.parse(v) : null; }} catch(e) {{ return null; }}
        }}
        function _saveActiveDsets(obj) {{
            try {{ localStorage.setItem(_LS_DS_KEY, JSON.stringify(obj)); }} catch(e) {{}}
        }}
        function _getActiveDsets() {{
            var saved = _loadActiveDsets();
            if (saved) return saved;
            // Default: all datasets active
            var d = {{}};
            Object.keys(DATASETS_META).forEach(function(k) {{ d[k] = true; }});
            return d;
        }}
        function _isDsActive(dsId) {{
            if (!dsId) return true; // entries without dataset_id always shown
            var active = _getActiveDsets();
            return active[dsId] !== false;
        }}
        var _activeDsets = _getActiveDsets();

        // Build dataset toggle checkboxes
        (function() {{
            var wrap = document.getElementById('ds-toggle-wrap');
            if (!wrap) return;
            var dsKeys = Object.keys(DATASETS_META);
            if (dsKeys.length === 0) return;
            var lbl = document.createElement('span');
            lbl.textContent = 'Datasets:';
            lbl.style.fontWeight = '600';
            wrap.appendChild(lbl);
            dsKeys.forEach(function(k) {{
                var ds = DATASETS_META[k];
                var label = document.createElement('label');
                label.style.cssText = 'display:flex;align-items:center;gap:3px;cursor:pointer;';
                var cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.checked = _activeDsets[k] !== false;
                cb.onchange = function() {{
                    _activeDsets[k] = cb.checked;
                    _saveActiveDsets(_activeDsets);
                    if (typeof buildFullPlot === 'function') buildFullPlot();
                }};
                label.appendChild(cb);
                label.appendChild(document.createTextNode(ds.name || k));
                wrap.appendChild(label);
            }});
        }})();

        // Filter arrays by active datasets
        function _dsFilterSolvents() {{
            return SOLVENTS.filter(function(s) {{ return _isDsActive(s.dsId); }});
        }}
        function _dsFilterPolymers() {{
            return POLYMERS.filter(function(p) {{ return _isDsActive(p.dsId); }});
        }}

        // Source base confidence tiers
        var SRC_TIERS = {{
            'Hansen Handbook 2007': 50, 'Mendeley (Langner 2022)': 40,
            'SolvPred (Fang)': 35, 'Accudyne Test': 40, 'Wolfram Data Repo': 35,
            'Pang et al. 2024': 30, 'Hansen Handbook A.1': 30, 'Hansen Handbook A.2': 30,
        }};
        // Lightweight confidence badge — tooltip data stored in attributes, not inline HTML
        function confBadge(mat, isPoly) {{
            if (!mat || mat.conf == null) return '';
            var pct = Math.round(mat.conf * 100);
            var color;
            if (mat.conf >= 0.8) color = '#27ae60';
            else if (mat.conf >= 0.5) color = '#f39c12';
            else color = '#e74c3c';
            return '<span class="conf-badge" data-src="' + (mat.src || '').replace(/"/g, '&quot;') + '" data-cas="' + (mat.cas ? '1' : '0') + '" data-smi="' + (!isPoly && mat.smiles ? '1' : '0') + '" data-poly="' + (isPoly ? '1' : '0') + '" data-srcn="' + (mat.srcN || 1) + '" data-pct="' + pct + '" style="display:inline-block;padding:2px 6px;border-radius:4px;font-size:0.75rem;font-weight:600;color:#fff;background:' + color + ';cursor:help">' + pct + '%</span>';
        }}
        // Shared confidence tooltip element (created once, positioned on hover)
        var _confTip = null;
        var _confBadgeActive = null;
        function _showConfTip(badge) {{
            if (!_confTip) {{
                _confTip = document.createElement('div');
                _confTip.className = 'conf-tip';
                document.body.appendChild(_confTip);
            }}
            _confBadgeActive = badge;
            var src = badge.dataset.src || 'Unknown';
            var base = SRC_TIERS[src] || 25;
            var hasCas = badge.dataset.cas === '1';
            var hasSmi = badge.dataset.smi === '1';
            var isPoly = badge.dataset.poly === '1';
            var srcN = parseInt(badge.dataset.srcn) || 1;
            var crossBonus = srcN > 1 ? Math.min((srcN - 1) * 15, 30) : 0;
            var pct = badge.dataset.pct;
            function row(lbl, val) {{
                var cls = val > 0 ? 'pos' : 'zero';
                return '<div class="conf-row"><span class="conf-label">' + lbl + '</span><span class="conf-val ' + cls + '">' + (val > 0 ? '+' : '') + val + '%</span></div>';
            }}
            var h = '<div style="font-weight:700;margin-bottom:4px;color:#fff">Confidence Breakdown</div>';
            h += row('Source: ' + src, base);
            h += row('CAS verified', hasCas ? 15 : 0);
            if (!isPoly) h += row('SMILES confirmed', hasSmi ? 10 : 0);
            if (srcN > 1) h += row('Cross-ref (' + srcN + ' sources)', crossBonus);
            h += '<div class="conf-sep"></div>';
            h += '<div class="conf-row"><span class="conf-label" style="color:#fff">Total</span><span class="conf-val" style="color:#fff">' + pct + '%</span></div>';
            _confTip.innerHTML = h;
            var rect = badge.getBoundingClientRect();
            _confTip.style.display = 'block';
            var tipW = _confTip.offsetWidth;
            var tipH = _confTip.offsetHeight;
            var left = rect.left + rect.width / 2 - tipW / 2;
            // Position below badge; if it would go off-screen bottom, flip above
            var top = rect.bottom + 8;
            if (top + tipH > window.innerHeight) top = rect.top - tipH - 8;
            if (left < 4) left = 4;
            if (left + tipW > window.innerWidth - 4) left = window.innerWidth - tipW - 4;
            _confTip.style.left = left + 'px';
            _confTip.style.top = top + 'px';
        }}
        document.addEventListener('mouseover', function(e) {{
            var badge = e.target.closest('.conf-badge');
            if (badge) {{
                if (badge !== _confBadgeActive) _showConfTip(badge);
            }} else if (_confTip && !_confTip.contains(e.target)) {{
                _confTip.style.display = 'none';
                _confBadgeActive = null;
            }}
        }});

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
            solvents: ['22%','10%','48px','48px','48px','52px','52px','9%','50px','11%'],
            polymers: ['22%','10%','48px','48px','48px','52px','9%','50px','11%'],
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
        var _isSearchActive = false;
        function onSimpleModeChange() {{
            simpleMode = document.getElementById('simple-mode').checked;
            // Update the 3D plot to show/hide non-common materials
            _updatePlotForCommonFilter();
            // Rebuild home table with filter applied
            buildHomeTable();
            // Re-run last search so results table reflects the filter
            if (_isSearchActive && lastSearchQuery) {{
                var parsed = parseQuery(lastSearchQuery);
                var result = executeSearch(parsed);
                var html = renderResultsHTML(result);
                showResults(html);
                if (!result.error) updatePlotWithResults(result);
            }}
        }}

        // Pre-compute original coordinate arrays for common-filter toggling.
        // Plotly 3D scatter renders per-point size arrays differently from
        // scalars (smaller due to sizeref normalization), so we hide non-common
        // points by nulling their coordinates instead.
        var _allSolX = SOLVENTS.map(function(s) {{ return s.dd; }});
        var _allSolY = SOLVENTS.map(function(s) {{ return s.dp; }});
        var _allSolZ = SOLVENTS.map(function(s) {{ return s.dh; }});
        var _comSolX = SOLVENTS.map(function(s) {{ return s.common ? s.dd : null; }});
        var _comSolY = SOLVENTS.map(function(s) {{ return s.common ? s.dp : null; }});
        var _comSolZ = SOLVENTS.map(function(s) {{ return s.common ? s.dh : null; }});
        var _allPolyX = POLYMERS.map(function(p) {{ return p.dd; }});
        var _allPolyY = POLYMERS.map(function(p) {{ return p.dp; }});
        var _allPolyZ = POLYMERS.map(function(p) {{ return p.dh; }});
        var _comPolyX = POLYMERS.map(function(p) {{ return p.common ? p.dd : null; }});
        var _comPolyY = POLYMERS.map(function(p) {{ return p.common ? p.dp : null; }});
        var _comPolyZ = POLYMERS.map(function(p) {{ return p.common ? p.dh : null; }});
        var _comSolColors = null;  // built lazily after _solventColors is populated
        var _comPolyColors = null;

        function _updatePlotForCommonFilter() {{
            if (!plotDiv || !plotDiv.data) return;
            // Build common-only colors lazily (needs colors from buildFullPlot)
            if (!_comSolColors && _solventColors.length) {{
                _comSolColors = SOLVENTS.map(function(s, i) {{ return s.common ? (_solventColors[i] || '#888') : 'rgba(0,0,0,0)'; }});
            }}
            if (!_comPolyColors && _polymerColors.length) {{
                _comPolyColors = POLYMERS.map(function(p, i) {{ return p.common ? (_polymerColors[i] || '#a9a9a9') : 'rgba(0,0,0,0)'; }});
            }}
            // Use dimmed styling when a search has dimmed the base traces
            var sSize = _plotDimmed ? 2 : 5;
            var pSize = _plotDimmed ? 3 : 7;
            var sColor = _plotDimmed ? '#999' : null;
            var pColor = _plotDimmed ? '#665500' : null;
            var sOpacity = _plotDimmed ? 0.1 : 0.85;
            var pOpacity = _plotDimmed ? 0.12 : 0.95;
            var hInfo = _plotDimmed ? 'skip' : 'none';
            if (simpleMode) {{
                // Hide non-common materials by nulling their coordinates
                var sColors = _plotDimmed ? sColor : _comSolColors;
                var pColors = _plotDimmed ? pColor : _comPolyColors;
                Plotly.restyle(plotDiv, {{
                    'x': [_comSolX, _comPolyX],
                    'y': [_comSolY, _comPolyY],
                    'z': [_comSolZ, _comPolyZ],
                    'marker.size': [sSize, pSize],
                    'marker.color': [sColors, pColors],
                    'marker.opacity': [sOpacity, pOpacity],
                    'hoverinfo': [hInfo, hInfo],
                }}, [0, 1]);
            }} else {{
                // Restore all points with full coordinates
                Plotly.restyle(plotDiv, {{
                    'x': [_allSolX, _allPolyX],
                    'y': [_allSolY, _allPolyY],
                    'z': [_allSolZ, _allPolyZ],
                    'marker.size': [sSize, pSize],
                    'marker.color': [sColor || _solventColors, pColor || _polymerColors],
                    'marker.opacity': [sOpacity, pOpacity],
                    'hoverinfo': [hInfo, hInfo],
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
                const exact = _solventMap.get(aliased);
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
                h.push('<tr data-name="', r.name.replace(/"/g, '&quot;'), '" onclick="highlightInPlot(\\x27', enc, '\\x27)" onmouseenter="hoverInPlot(\\x27', enc, '\\x27)" onmouseleave="unhoverInPlot()" style="cursor:pointer"><td class="rank">', (i + 1), '</td><td><span class="hoverable-name" onmouseenter="showStructure(event,\\x27', enc, '\\x27)" onmouseleave="hideStructure()">', r.name, '</span></td>');
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
            // Filter by active datasets
            var fSolv = _dsFilterSolvents();
            var fPoly = _dsFilterPolymers();
            // Single trace for all solvents with per-point colors (instead of 22+ traces)
            _solventColors = fSolv.map(s => CAT_COLORS[s.cat] || '#888');
            _polymerColors = fPoly.map(p => POLY_CAT_COLORS[p.cat] || '#a9a9a9');
            fullTraces = [
                {{
                    type: 'scatter3d', mode: 'markers',
                    name: 'Solvents',
                    x: fSolv.map(s => s.dd), y: fSolv.map(s => s.dp), z: fSolv.map(s => s.dh),
                    hoverinfo: 'none',
                    marker: {{ size: 5, color: _solventColors, opacity: 0.85 }},
                    showlegend: false,
                }},
                {{
                    type: 'scatter3d', mode: 'markers',
                    name: 'Polymers',
                    x: fPoly.map(p => p.dd), y: fPoly.map(p => p.dp), z: fPoly.map(p => p.dh),
                    hoverinfo: 'none',
                    marker: {{ size: 7, color: _polymerColors, symbol: 'diamond', opacity: 0.95 }},
                    showlegend: false,
                }},
            ];
            // Pre-allocate a hidden highlight trace so clicking in the home table works
            fullTraces.push({{
                type: 'scatter3d', mode: 'markers+text',
                name: '★ Highlighted',
                x: [0], y: [0], z: [0],
                text: [''],
                textposition: 'top center',
                textfont: {{ size: 13, color: '#FFD700' }},
                hoverinfo: 'none',
                marker: {{ size: 16, color: '#e94560', symbol: 'circle', opacity: 1, line: {{ width: 2, color: 'white' }} }},
                visible: false,
                showlegend: false,
            }});
            _baseTraceCount = fullTraces.length;
            _highlightIdx = _baseTraceCount - 1;
            Plotly.newPlot(plotDiv, fullTraces, makeLayout(), {{ responsive: true }});
            _buildLegend();
        }}

        function _buildLegend() {{
            var el = document.getElementById('plot-legend');
            if (!el) return;
            // Collect unique solvent categories with counts
            var sCats = {{}};
            SOLVENTS.forEach(function(s) {{
                var c = s.cat || 'other';
                if (!sCats[c]) sCats[c] = 0;
                sCats[c]++;
            }});
            // Collect unique polymer categories with counts
            var pCats = {{}};
            POLYMERS.forEach(function(p) {{
                var c = p.cat || 'Other';
                if (!pCats[c]) pCats[c] = 0;
                pCats[c]++;
            }});
            // Sort categories by count descending
            var sList = Object.keys(sCats).sort(function(a,b) {{ return sCats[b] - sCats[a]; }});
            var pList = Object.keys(pCats).sort(function(a,b) {{ return pCats[b] - pCats[a]; }});
            var h = '';
            // Solvents group
            h += '<div class="legend-group">';
            h += '<div class="legend-header" onclick="toggleLegendGroup(this)">';
            h += '<span class="legend-arrow">&#9654;</span>';
            h += '<span class="legend-marker" style="background:' + (CAT_COLORS['alcohol'] || '#888') + '"></span>';
            h += 'Solvents (' + SOLVENTS.length + ')';
            h += '</div>';
            h += '<div class="legend-items">';
            sList.forEach(function(cat) {{
                var color = CAT_COLORS[cat] || '#888';
                var label = cat.charAt(0).toUpperCase() + cat.slice(1);
                h += '<div class="legend-item"><span class="legend-swatch" style="background:' + color + '"></span>' + label + ' (' + sCats[cat] + ')</div>';
            }});
            h += '</div></div>';
            // Polymers group
            h += '<div class="legend-group">';
            h += '<div class="legend-header" onclick="toggleLegendGroup(this)">';
            h += '<span class="legend-arrow">&#9654;</span>';
            h += '<span class="legend-marker diamond" style="background:' + (POLY_CAT_COLORS['Vinyl & Styrene'] || '#a9a9a9') + '"></span>';
            h += 'Polymers (' + POLYMERS.length + ')';
            h += '</div>';
            h += '<div class="legend-items">';
            pList.forEach(function(cat) {{
                var color = POLY_CAT_COLORS[cat] || '#a9a9a9';
                h += '<div class="legend-item"><span class="legend-swatch diamond" style="background:' + color + '"></span>' + cat + ' (' + pCats[cat] + ')</div>';
            }});
            h += '</div></div>';
            el.innerHTML = h;
        }}

        function toggleLegendGroup(header) {{
            var arrow = header.querySelector('.legend-arrow');
            var items = header.nextElementSibling;
            if (items.classList.contains('open')) {{
                items.classList.remove('open');
                arrow.classList.remove('open');
            }} else {{
                items.classList.add('open');
                arrow.classList.add('open');
            }}
        }}

        // Fixed axis ranges — never change
        var FIXED_AXES = {{
            xRange: [12, 22], yRange: [0, 28], zRange: [0, 45],
        }};
        var axisStyle = {{
            gridcolor: '#dfe6e9', zerolinecolor: '#b2bec3',
            backgroundcolor: '#f8f9fa', showbackground: true,
            tickfont: {{ size: 11, color: '#636e72' }},
            showspikes: false,
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
                showlegend: false,
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
        var _polymerColors = [];
        var _resultTraceCount = 0;
        var _plotDimmed = false;

        function _dimBaseTraces() {{
            // Restyle the 2 base traces to be dim background dots.
            // No Plotly.react, no layout rebuild — camera stays exactly where it is.
            if (_plotDimmed) return;
            _plotDimmed = true;
            if (simpleMode) {{
                // Dim common materials, fully hide non-common
                _updatePlotForCommonFilter();
            }} else {{
                Plotly.restyle(plotDiv, {{
                    'marker.size': [2, 3],
                    'marker.color': ['#999', '#aa8800'],
                    'marker.opacity': [0.1, 0.12],
                    'hoverinfo': ['skip', 'skip'],
                    'hovertemplate': [null, null],
                }}, [0, 1]);
            }}
        }}

        function _restoreBaseTraces() {{
            // Restore the 2 base traces to full interactive appearance.
            if (!_plotDimmed) return;
            _plotDimmed = false;
            // Delegate to _updatePlotForCommonFilter which handles both
            // coordinate restoration and simpleMode filtering in one restyle.
            _updatePlotForCommonFilter();
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
            unpinAll();
            Plotly.relayout(plotDiv, {{ 'title.text': 'Hansen Solubility Parameter Space' }});
        }}

        // ===================== TOOLTIP SYSTEM (scene annotations) =====================
        var _highlightIdx = -1; // kept for search result traces
        var _pinnedName = null;
        var _currentAnnotation = null;
        var _tableHover = false; // true while mouse is over a table row
        var _annotationTimer = 0; // debounce timer for relayout calls
        var _pendingAnnotation = null; // name queued for next relayout (null = hide)

        function _annotationText(mat, isSolvent) {{
            var h = '<b>' + mat.name + '</b>';
            if (isSolvent) {{
                if (mat.cas) h += '<br>CAS: ' + mat.cas;
                if (mat.mw != null) h += '<br>MW: ' + mat.mw;
                if (mat.bp != null) h += '<br>BP: ' + mat.bp + '°C';
            }} else {{
                if (mat.r != null) h += '<br>R₀=' + mat.r;
            }}
            h += '<br>δD=' + mat.dd.toFixed(1) + ', δP=' + mat.dp.toFixed(1) + ', δH=' + mat.dh.toFixed(1);
            return h;
        }}

        // Debounced annotation update: coalesces rapid hover AND click events
        // to avoid stacking expensive Plotly.relayout calls on the 3D scene.
        var _annotationBusy = false; // true while a relayout is in-flight
        function _scheduleAnnotation(name) {{
            _pendingAnnotation = name;
            if (_annotationTimer) clearTimeout(_annotationTimer);
            if (_annotationBusy) return; // will flush when current relayout finishes
            _annotationTimer = setTimeout(_flushAnnotation, 80);
        }}
        function _flushAnnotation() {{
            clearTimeout(_annotationTimer);
            _annotationTimer = 0;
            var name = _pendingAnnotation;
            _pendingAnnotation = null;
            if (name) {{
                if (_currentAnnotation === name) return;
                _annotationBusy = true;
                _applyAnnotation(name).then(function() {{
                    _annotationBusy = false;
                    if (_pendingAnnotation != null && _pendingAnnotation !== _currentAnnotation) _flushAnnotation();
                }});
            }} else {{
                if (!_currentAnnotation) return;
                _currentAnnotation = null;
                _annotationBusy = true;
                Plotly.relayout(plotDiv, {{ 'scene.annotations': [] }}).then(function() {{
                    _annotationBusy = false;
                    if (_pendingAnnotation != null) _flushAnnotation();
                }});
            }}
        }}

        function _applyAnnotation(name) {{
            if (_currentAnnotation === name) return Promise.resolve();
            var mat = _solventMap.get(name);
            var isSolvent = !!mat;
            if (!mat) mat = _polymerMap.get(name);
            if (!mat) return Promise.resolve();
            _currentAnnotation = name;
            var bgColor = isSolvent ? (CAT_COLORS[mat.cat] || '#888') : 'gold';
            return Plotly.relayout(plotDiv, {{
                'scene.annotations': [
                    // Caret triangle
                    {{
                        x: mat.dd, y: mat.dp, z: mat.dh,
                        text: '\u25C0',
                        showarrow: false,
                        xshift: 8,
                        xanchor: 'left',
                        bgcolor: 'rgba(0,0,0,0)',
                        bordercolor: 'rgba(0,0,0,0)',
                        borderwidth: 0,
                        borderpad: 0,
                        font: {{ color: bgColor, size: 20 }}
                    }},
                    // Tooltip text box
                    {{
                        x: mat.dd, y: mat.dp, z: mat.dh,
                        text: _annotationText(mat, isSolvent),
                        align: 'left',
                        showarrow: false,
                        xshift: 21,
                        xanchor: 'left',
                        bgcolor: bgColor,
                        font: {{ color: '#000', size: 13, family: 'Open Sans, verdana, arial, sans-serif' }},
                        bordercolor: bgColor,
                        borderwidth: 1,
                        borderpad: 6
                    }}
                ]
            }});
        }}

        // Public API: all annotation updates go through the debounced path
        // to prevent stacking expensive Plotly.relayout calls on rapid clicks.
        function showAnnotation(name) {{
            _scheduleAnnotation(name);
        }}

        function hideAnnotation() {{
            _scheduleAnnotation(null);
        }}

        function unpinAll() {{
            _pinnedName = null;
            hideAnnotation();
            if (_prevHighlightedRow) {{ _prevHighlightedRow.style.background = ''; _prevHighlightedRow = null; }}
        }}

        // Called from table row onclick — immediate (no debounce)
        function highlightInPlot(encodedName) {{
            var name = decodeURIComponent(encodedName);
            if (_pinnedName === name) {{
                unpinAll();
                return;
            }}
            _pinnedName = name;
            showAnnotation(name);
            requestAnimationFrame(function() {{ selectInTable(name); }});
        }}

        // Called from table row onmouseenter — debounced
        function hoverInPlot(encodedName) {{
            _tableHover = true;
            if (_pinnedName) return;
            showAnnotation(decodeURIComponent(encodedName));
        }}

        // Called from table row onmouseleave — debounced
        function unhoverInPlot() {{
            _tableHover = false;
            if (!_pinnedName) hideAnnotation();
        }}

        var _prevHighlightedRow = null;
        function selectInTable(name) {{
            // If the home panel is visible, switch tabs if needed so the material is in view
            var homePanel = document.getElementById('home-panel');
            if (homePanel && homePanel.style.display !== 'none') {{
                var isSolvent = _solventMap.has(name);
                var isPolymer = !isSolvent && _polymerMap.has(name);
                if (isSolvent && homeTab !== 'solvents') {{
                    switchHomeTab('solvents');
                }} else if (isPolymer && homeTab !== 'polymers') {{
                    switchHomeTab('polymers');
                }}
            }}
            // Clear only the previously highlighted row instead of all rows
            if (_prevHighlightedRow) {{
                _prevHighlightedRow.style.background = '';
                _prevHighlightedRow = null;
            }}
            // Highlight in whichever table is visible: results (chat-panel) or home table
            var containers = [document.getElementById('chat-panel'), homePanel];
            for (var ci = 0; ci < containers.length; ci++) {{
                var c = containers[ci];
                if (!c || c.style.display === 'none' || !c.classList.contains('visible') && ci === 0) continue;
                var row = c.querySelector('tr[data-name="' + name.replace(/\\\\/g, '\\\\\\\\').replace(/"/g, '\\\\"') + '"]');
                if (row) {{
                    row.style.background = '#fff3cd';
                    _prevHighlightedRow = row;
                    row.scrollIntoView({{ block: 'center', behavior: 'auto' }});
                    return;
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
                'RED': 'Relative Energy Difference = Ra/R\u2080. RED &lt; 1 = compatible, RED &gt; 1 = incompatible',
                'Conf.': 'Data confidence: High (\u226580%) = cross-referenced with CAS/SMILES, Med (50-79%) = verified identity, Low (&lt;50%) = single source only'
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
                // Name, CAS #, δD, δP, δH, MW, BP, Category, Confidence, Source
                var solWidths = getWidths('solvents');
                solWidths.forEach(function(w) {{
                    var col = document.createElement('col');
                    col.style.width = w;
                    cg.appendChild(col);
                }});
                tbl.insertBefore(cg, thead);
                headerHtml = '<tr>';
                ['Name','CAS #','&delta;D (MPa<sup>\u00bd</sup>)','&delta;P (MPa<sup>\u00bd</sup>)','&delta;H (MPa<sup>\u00bd</sup>)','MW (g/mol)','BP (&deg;C)','Category','Conf.','Source'].forEach(function(label, i) {{
                    headerHtml += thWithTip(label, i);
                }});
                headerHtml += '</tr>';
                var filtered = _dsFilterSolvents();
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
                    rowsHtml += '<tr data-name="' + s.name.replace(/"/g, '&quot;') + '" onclick="highlightInPlot(\\x27' + encodeURIComponent(s.name) + '\\x27)" onmouseenter="hoverInPlot(\\x27' + encodeURIComponent(s.name) + '\\x27)" onmouseleave="unhoverInPlot()" style="cursor:pointer;border-left:3px solid ' + catColor + '">';
                    rowsHtml += '<td><span class="hoverable-name" onmouseenter="showStructure(event,\\x27' + encodeURIComponent(s.name) + '\\x27)" onmouseleave="hideStructure()">' + s.name + '</span></td>';
                    rowsHtml += '<td>' + (s.cas || '') + '</td>';
                    rowsHtml += '<td>' + lnk(s.dd, s.srcUrl) + '</td>';
                    rowsHtml += '<td>' + lnk(s.dp, s.srcUrl) + '</td>';
                    rowsHtml += '<td>' + lnk(s.dh, s.srcUrl) + '</td>';
                    rowsHtml += '<td>' + lnk(s.mw, s.mwSrc) + '</td>';
                    rowsHtml += '<td>' + (s.bp != null ? lnk(s.bp, s.bpSrc) : '') + '</td>';
                    rowsHtml += '<td style="color:' + catColor + '">' + (s.cat || '') + '</td>';
                    rowsHtml += '<td>' + confBadge(s, false) + '</td>';
                    rowsHtml += '<td>' + ((s.src && s.srcUrl) ? '<a href="' + s.srcUrl + '" target="_blank" rel="noopener" style="color:#0984e3;text-decoration:none">' + s.src + '</a>' : (s.src || '')) + '</td>';
                    rowsHtml += '</tr>';
                }}
            }} else {{
                // Name, CAS, δD, δP, δH, R₀, Type, Confidence, Source
                var polyWidths = getWidths('polymers');
                polyWidths.forEach(function(w) {{
                    var col = document.createElement('col');
                    col.style.width = w;
                    cg.appendChild(col);
                }});
                tbl.insertBefore(cg, thead);
                headerHtml = '<tr>';
                ['Name','CAS #','&delta;D (MPa<sup>\u00bd</sup>)','&delta;P (MPa<sup>\u00bd</sup>)','&delta;H (MPa<sup>\u00bd</sup>)','R&#8320; (MPa<sup>\u00bd</sup>)','Type','Conf.','Source'].forEach(function(label, i) {{
                    headerHtml += thWithTip(label, i);
                }});
                headerHtml += '</tr>';
                var filtered = _dsFilterPolymers();
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
                    rowsHtml += '<tr data-name="' + p.name.replace(/"/g, '&quot;') + '" onclick="highlightInPlot(\\x27' + encodeURIComponent(p.name) + '\\x27)" onmouseenter="hoverInPlot(\\x27' + encodeURIComponent(p.name) + '\\x27)" onmouseleave="unhoverInPlot()" style="cursor:pointer">';
                    rowsHtml += '<td><span class="hoverable-name">' + p.name + '</span></td>';
                    rowsHtml += '<td>' + (p.cas || '') + '</td>';
                    rowsHtml += '<td>' + lnk(p.dd, p.srcUrl) + '</td>';
                    rowsHtml += '<td>' + lnk(p.dp, p.srcUrl) + '</td>';
                    rowsHtml += '<td>' + lnk(p.dh, p.srcUrl) + '</td>';
                    rowsHtml += '<td>' + (p.r || '') + '</td>';
                    rowsHtml += '<td>' + (p.type || '') + '</td>';
                    rowsHtml += '<td>' + confBadge(p, true) + '</td>';
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

        var _filterTimer = 0;
        function filterHomeTable(val) {{
            homeFilterText = val.trim();
            clearTimeout(_filterTimer);
            _filterTimer = setTimeout(buildHomeTable, 120);
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
            const solvent = _solventMap.get(name);
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
            _isSearchActive = true;
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
            _isSearchActive = false;
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
            // All tooltips use scene annotations for one consistent style
            plotDiv.on('plotly_hover', function(data) {{
                if (_pinnedName || _tableHover) return;
                try {{
                    var pt = data.points[0];
                    var name = '';
                    if (pt.curveNumber === 0 && SOLVENTS[pt.pointNumber]) name = SOLVENTS[pt.pointNumber].name;
                    else if (pt.curveNumber === 1 && POLYMERS[pt.pointNumber]) name = POLYMERS[pt.pointNumber].name;
                    if (name) showAnnotation(name);
                }} catch(e) {{}}
            }});
            plotDiv.on('plotly_unhover', function() {{
                if (!_pinnedName && !_tableHover) hideAnnotation();
            }});
            plotDiv.on('plotly_click', function(data) {{
                try {{
                    if (!data || !data.points || !data.points.length) return;
                    var pt = data.points[0];
                    var name = '';
                    if (pt.curveNumber === 0 && SOLVENTS[pt.pointNumber]) name = SOLVENTS[pt.pointNumber].name;
                    else if (pt.curveNumber === 1 && POLYMERS[pt.pointNumber]) name = POLYMERS[pt.pointNumber].name;
                    if (!name) return;
                    if (_pinnedName === name) {{
                        unpinAll();
                    }} else {{
                        _pinnedName = name;
                        showAnnotation(name);
                        selectInTable(name);
                    }}
                }} catch(e) {{ console.error('plotly_click error:', e); }}
            }});
            // Click outside plot or table row clears pin
            document.addEventListener('click', function(e) {{
                if (!_pinnedName) return;
                if (plotDiv.contains(e.target)) return;
                if (e.target.closest('tr[data-name]')) return;
                unpinAll();
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
            "conf": row.get("confidence", "").strip(),
            "srcN": int(row.get("source_count", "1").strip() or "1"),
            "src": SOURCE_NAMES.get(src_key, src_key),
            "srcUrl": row.get("source_url", "").strip(),
            "dsId": row.get("dataset_id", "").strip(),
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
            "conf": row.get("confidence", "").strip(),
            "srcN": int(row.get("source_count", "1").strip() or "1"),
            "src": SOURCE_NAMES.get(src_key, src_key),
            "srcUrl": row.get("source_url", "").strip(),
            "dsId": row.get("dataset_id", "").strip(),
        })

db_solvents_json = json.dumps(db_solvents)
db_polymers_json = json.dumps(db_polymers)

# Load CAS candidates for the crosslink feature in database.html
cas_candidates_path = os.path.join(os.path.dirname(__file__), "data", "processed", "cas_candidates.json")
cas_candidates_map = {}
if os.path.exists(cas_candidates_path):
    with open(cas_candidates_path) as f:
        _raw_cands = json.load(f)
    for entry in _raw_cands:
        name = entry.get("original_name", "")
        opts = []
        for o in entry.get("options", [])[:5]:  # top 5 options
            opts.append({
                "name": o.get("corrected_name", ""),
                "cas": o.get("cas", ""),
                "iupac": o.get("iupac", ""),
                "conf": round(o.get("confidence", 0), 2),
                "reason": o.get("reason", ""),
                "mw": o.get("pubchem_mw"),
                "density": o.get("ref_density"),
                "mv_match": o.get("mv_match"),
                "mv_pct": o.get("mv_pct_diff"),
            })
        if opts:
            cas_candidates_map[name] = opts
cas_candidates_json = json.dumps(cas_candidates_map)

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
.conf-tip {{
    display: none; position: fixed; z-index: 9999;
    background: #2d3436; color: #dfe6e9; border-radius: 6px; padding: 10px 14px;
    font-size: 0.75rem; line-height: 1.5; white-space: nowrap;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}}
.conf-row {{ display: flex; justify-content: space-between; gap: 18px; }}
.conf-row .conf-label {{ color: #b2bec3; }}
.conf-row .conf-val {{ font-weight: 600; }}
.conf-row .conf-val.pos {{ color: #00b894; }}
.conf-row .conf-val.zero {{ color: #636e72; }}
.conf-sep {{ border-top: 1px solid #636e72; margin: 4px 0; }}
/* Source filter in header */
.src-filter-wrap {{
    position: relative; margin-top: 4px;
}}
.src-filter-btn {{
    display: block; width: 100%; padding: 2px 4px; font-size: 0.7rem;
    border: 1px solid #dfe6e9; border-radius: 3px; background: #fff;
    color: #636e72; cursor: pointer; text-align: left;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.src-filter-btn:hover {{ border-color: #b2bec3; }}
.src-filter-drop {{
    display: none; position: absolute; top: 100%; left: 0; z-index: 20;
    background: #fff; border: 1px solid #dfe6e9; border-radius: 4px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.12); min-width: 180px;
    max-height: 260px; overflow-y: auto; padding: 4px 0;
}}
.src-filter-drop.open {{ display: block; }}
.src-filter-opt {{
    display: flex; align-items: center; gap: 6px; padding: 4px 10px;
    font-size: 0.72rem; color: #2d3436; cursor: pointer; white-space: nowrap;
}}
.src-filter-opt:hover {{ background: #f5f6fa; }}
.src-filter-opt input {{ margin: 0; cursor: pointer; }}
.src-filter-opt label {{ cursor: pointer; }}
/* Crosslink ? badge */
.cas-missing {{
    display: inline-flex; align-items: center; justify-content: center;
    width: 20px; height: 20px; border-radius: 50%;
    background: #fdcb6e; color: #2d3436; font-weight: 700; font-size: 0.75rem;
    cursor: pointer; border: none; line-height: 1;
}}
.cas-missing:hover {{ background: #f39c12; }}
/* Crosslink popover */
.xl-popover {{
    display: none; position: fixed; z-index: 1000;
    background: #fff; border: 1px solid #dfe6e9; border-radius: 8px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.18); width: 380px; max-height: 420px;
    overflow-y: auto; font-size: 0.82rem;
}}
.xl-popover.visible {{ display: block; }}
.xl-header {{
    padding: 10px 14px; border-bottom: 1px solid #eee;
    font-weight: 700; color: #2d3436; display: flex; align-items: center; justify-content: space-between;
}}
.xl-header .xl-close {{
    background: none; border: none; font-size: 1.1rem; cursor: pointer; color: #636e72; padding: 0 4px;
}}
.xl-header .xl-close:hover {{ color: #e94560; }}
.xl-opt {{
    padding: 10px 14px; border-bottom: 1px solid #f0f2f5; cursor: pointer; transition: background 0.15s;
}}
.xl-opt:last-child {{ border-bottom: none; }}
.xl-opt:hover {{ background: #f0f8ff; }}
.xl-opt-name {{ font-weight: 600; color: #2d3436; }}
.xl-opt-cas {{ color: #0984e3; font-family: monospace; }}
.xl-opt-detail {{ color: #636e72; font-size: 0.75rem; margin-top: 2px; }}
.xl-opt-conf {{
    display: inline-block; padding: 1px 6px; border-radius: 3px;
    font-size: 0.7rem; font-weight: 600; color: #fff; margin-left: 6px;
}}
.xl-opt-mv {{ font-size: 0.7rem; margin-left: 4px; }}
.xl-opt-mv.match {{ color: #27ae60; }}
.xl-opt-mv.mismatch {{ color: #e74c3c; }}
</style>
</head>
<body>
<div class="header">
    <h1><a href="materialism.html">Materialism</a> — Database</h1>
    <div class="nav-links">
        <a href="cas_review.html">Crosslink</a>
        <a href="manage.html" style="margin-right:12px">Manage Datasets</a>
        <a href="materialism.html">Search</a>
    </div>
</div>
<div class="toolbar">
    <div class="db-tabs">
        <button id="tab-solv" class="db-tab active" onclick="switchTab('solvents')">Solvents ({len(db_solvents)})</button>
        <button id="tab-poly" class="db-tab" onclick="switchTab('polymers')">Polymers ({len(db_polymers)})</button>
    </div>
    <input type="text" id="db-filter" placeholder="Filter by name or CAS..." oninput="renderTable()">
    <div id="ds-toggle-db" style="display:flex;align-items:center;gap:6px;font-size:0.8rem;color:#636e72;margin-left:8px;"></div>
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
var CAS_CANDIDATES = {cas_candidates_json};
var DATASETS_META = {datasets_meta_json};
// Dataset toggle state (shared with materialism.html via localStorage)
var _LS_DS_KEY = 'materialism_active_datasets';
function _loadActiveDsets() {{ try {{ var v = localStorage.getItem(_LS_DS_KEY); return v ? JSON.parse(v) : null; }} catch(e) {{ return null; }} }}
function _saveActiveDsets(obj) {{ try {{ localStorage.setItem(_LS_DS_KEY, JSON.stringify(obj)); }} catch(e) {{}} }}
function _getActiveDsets() {{ var s = _loadActiveDsets(); if (s) return s; var d = {{}}; Object.keys(DATASETS_META).forEach(function(k) {{ d[k] = true; }}); return d; }}
var _activeDsets = _getActiveDsets();
function _isDsActive(dsId) {{ if (!dsId) return true; return _activeDsets[dsId] !== false; }}
var SRC_TIERS = {{
    'Hansen Handbook 2007': 50, 'Mendeley (Langner 2022)': 40,
    'SolvPred (Fang)': 35, 'Accudyne Test': 40, 'Wolfram Data Repo': 35,
    'Pang et al. 2024': 30, 'Hansen Handbook A.1': 30, 'Hansen Handbook A.2': 30,
}};

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
    {{key:'conf', label:'Conf.', w:'56px', tip:'Data confidence score'}},
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
    {{key:'conf', label:'Conf.', w:'56px', tip:'Data confidence score'}},
    {{key:'src', label:'Source', w:'140px'}},
];

var activeTab = 'solvents';
var editing = false;
var edits = {{}};  // key: "type:index:field" -> value
var sortCol = null, sortAsc = true;
var srcFilterSet = {{}};  // keys = selected source names; empty = show all

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

function toggleSrcFilter(val) {{
    if (srcFilterSet[val]) delete srcFilterSet[val];
    else srcFilterSet[val] = true;
    renderTable();
    updateTabCounts();
}}
function clearSrcFilter() {{
    srcFilterSet = {{}};
    renderTable();
    updateTabCounts();
}}
function _hasSrcFilter() {{
    return Object.keys(srcFilterSet).length > 0;
}}
function _matchesSrcFilter(src) {{
    return !_hasSrcFilter() || srcFilterSet[src];
}}
function _countForTab(tab) {{
    var data = tab === 'solvents' ? SOLVENTS : POLYMERS;
    if (!_hasSrcFilter()) return data.length;
    var n = 0;
    for (var i = 0; i < data.length; i++) {{
        if (srcFilterSet[data[i].src]) n++;
    }}
    return n;
}}
function updateTabCounts() {{
    document.getElementById('tab-solv').textContent = 'Solvents (' + _countForTab('solvents') + ')';
    document.getElementById('tab-poly').textContent = 'Polymers (' + _countForTab('polymers') + ')';
}}
var _srcDropOpen = false;
function toggleSrcDrop(e) {{
    e.stopPropagation();
    _srcDropOpen = !_srcDropOpen;
    var drop = document.getElementById('src-drop');
    if (drop) drop.classList.toggle('open', _srcDropOpen);
}}

function renderTable() {{
    var cols = activeTab === 'solvents' ? SOLV_COLS : POLY_COLS;
    var data = activeTab === 'solvents' ? SOLVENTS : POLYMERS;
    var filter = document.getElementById('db-filter').value.toLowerCase().trim();

    // Build index array for filtering
    var indices = [];
    for (var i = 0; i < data.length; i++) {{
        // Dataset filter
        if (!_isDsActive(data[i].dsId)) continue;
        if (filter) {{
            var row = data[i];
            var name = getVal(activeTab, i, 'name').toLowerCase();
            var cas = getVal(activeTab, i, 'cas').toLowerCase();
            if (name.indexOf(filter) === -1 && cas.indexOf(filter) === -1) continue;
        }}
        if (_hasSrcFilter() && !_matchesSrcFilter(getVal(activeTab, i, 'src'))) continue;
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
        if (c.key === 'src') {{
            var nSel = Object.keys(srcFilterSet).length;
            var btnLabel = nSel === 0 ? 'All sources' : nSel + ' selected';
            hdr += '<th' + cls + ' style="width:' + c.w + ';position:relative">';
            hdr += '<span onclick="sortBy(' + ci + ')" style="cursor:pointer">' + c.label + '</span>';
            hdr += '<div class="src-filter-wrap">';
            hdr += '<button class="src-filter-btn" onclick="toggleSrcDrop(event)">' + btnLabel + ' &#9662;</button>';
            hdr += '<div class="src-filter-drop' + (_srcDropOpen ? ' open' : '') + '" id="src-drop" onclick="event.stopPropagation()">';
            if (nSel > 0) {{
                hdr += '<div class="src-filter-opt" onclick="clearSrcFilter()" style="color:#e94560;font-weight:600">Clear all</div>';
            }}
            _srcOptions.forEach(function(s) {{
                var checked = srcFilterSet[s] ? ' checked' : '';
                var esc = s.replace(/'/g, '\\x27');
                hdr += '<div class="src-filter-opt" onclick="toggleSrcFilter(\\x27' + esc + '\\x27)">';
                hdr += '<input type="checkbox"' + checked + ' tabindex="-1"><label>' + s + '</label></div>';
            }});
            hdr += '</div></div></th>';
        }} else {{
            hdr += '<th' + cls + ' style="width:' + c.w + '"' + (c.tip ? ' title="' + c.tip + '"' : '') + ' onclick="sortBy(' + ci + ')">' + c.label + '</th>';
        }}
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
                // Numeric formatting
                if (val !== '' && val != null) {{
                    if (c.key === 'dd' || c.key === 'dp' || c.key === 'dh' || c.key === 'mw' || c.key === 'mv' || c.key === 'r') {{
                        var n = parseFloat(val); if (!isNaN(n)) display = n.toFixed(1);
                    }} else if (c.key === 'bp') {{
                        var n = parseFloat(val); if (!isNaN(n)) display = n.toFixed(0);
                    }} else if (c.key === 'density') {{
                        var n = parseFloat(val); if (!isNaN(n)) display = n.toFixed(2);
                    }}
                }}
                // CAS link or ? badge
                if (c.key === 'cas') {{
                    if (val) {{
                        display = '<a class="cas-link" href="https://commonchemistry.cas.org/detail?cas_rn=' + encodeURIComponent(val) + '" target="_blank" rel="noopener">' + val + '</a>';
                    }} else {{
                        var matName = (activeTab === 'solvents' ? SOLVENTS : POLYMERS)[idx].name;
                        if (CAS_CANDIDATES[matName]) {{
                            display = '<button class="cas-missing" onclick="openCrosslink(event,\\x27' + activeTab + '\\x27,' + idx + ')" title="Find CAS #">?</button>';
                        }}
                    }}
                }}
                // Source link
                if (c.key === 'src') {{
                    var srcUrl = activeTab === 'solvents' ? SOLVENTS[idx].srcUrl : POLYMERS[idx].srcUrl;
                    if (srcUrl) display = '<a href="' + srcUrl + '" target="_blank" rel="noopener">' + val + '</a>';
                }}
                // Confidence badge
                if (c.key === 'conf' && val) {{
                    var cv = parseFloat(val);
                    var pct = Math.round(cv * 100);
                    var cColor;
                    if (cv >= 0.8) {{ cColor = '#27ae60'; }}
                    else if (cv >= 0.5) {{ cColor = '#f39c12'; }}
                    else {{ cColor = '#e74c3c'; }}
                    var mat = (activeTab === 'solvents' ? SOLVENTS : POLYMERS)[idx];
                    var isPoly = activeTab === 'polymers';
                    display = '<span class="conf-badge" data-src="' + (mat.src || '').replace(/"/g, '&quot;') + '" data-cas="' + (mat.cas ? '1' : '0') + '" data-smi="' + (!isPoly && mat.smiles ? '1' : '0') + '" data-poly="' + (isPoly ? '1' : '0') + '" data-srcn="' + (mat.srcN || 1) + '" data-pct="' + pct + '" style="display:inline-block;padding:2px 6px;border-radius:4px;font-size:0.75rem;font-weight:600;color:#fff;background:' + cColor + ';cursor:help">' + pct + '%</span>';
                }}
                html += '<td' + (isEdited ? ' style="background:#e8f8f0"' : '') + '>' + display + '</td>';
            }}
        }}
        html += '</tr>';
    }}
    document.getElementById('db-tbody').innerHTML = html;
}}

// Build sorted list of unique source names for the header dropdown
var _srcOptions = (function() {{
    var srcSet = {{}};
    SOLVENTS.forEach(function(s) {{ if (s.src) srcSet[s.src] = true; }});
    POLYMERS.forEach(function(p) {{ if (p.src) srcSet[p.src] = true; }});
    return Object.keys(srcSet).sort();
}})();

loadEdits();
// Build dataset toggle checkboxes for database page
(function() {{
    var wrap = document.getElementById('ds-toggle-db');
    if (!wrap) return;
    var dsKeys = Object.keys(DATASETS_META);
    if (dsKeys.length === 0) return;
    var lbl = document.createElement('span');
    lbl.textContent = 'Datasets:';
    lbl.style.fontWeight = '600';
    wrap.appendChild(lbl);
    dsKeys.forEach(function(k) {{
        var ds = DATASETS_META[k];
        var label = document.createElement('label');
        label.style.cssText = 'display:flex;align-items:center;gap:3px;cursor:pointer;';
        var cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.checked = _activeDsets[k] !== false;
        cb.onchange = function() {{
            _activeDsets[k] = cb.checked;
            _saveActiveDsets(_activeDsets);
            renderTable();
        }};
        label.appendChild(cb);
        label.appendChild(document.createTextNode(ds.name || k));
        wrap.appendChild(label);
    }});
}})();
renderTable();
// Shared confidence tooltip
var _confTip = null;
var _confBadgeActive = null;
document.addEventListener('mouseover', function(e) {{
    var badge = e.target.closest('.conf-badge');
    if (badge) {{
        if (badge === _confBadgeActive) return;
        if (!_confTip) {{ _confTip = document.createElement('div'); _confTip.className = 'conf-tip'; document.body.appendChild(_confTip); }}
        _confBadgeActive = badge;
        var src = badge.dataset.src || 'Unknown';
        var base = SRC_TIERS[src] || 25;
        var hasCas = badge.dataset.cas === '1';
        var hasSmi = badge.dataset.smi === '1';
        var isPoly = badge.dataset.poly === '1';
        var srcN = parseInt(badge.dataset.srcn) || 1;
        var crossBonus = srcN > 1 ? Math.min((srcN - 1) * 15, 30) : 0;
        var pct = badge.dataset.pct;
        function row(lbl, val) {{ var cls = val > 0 ? 'pos' : 'zero'; return '<div class="conf-row"><span class="conf-label">' + lbl + '</span><span class="conf-val ' + cls + '">' + (val > 0 ? '+' : '') + val + '%</span></div>'; }}
        var h = '<div style="font-weight:700;margin-bottom:4px;color:#fff">Confidence Breakdown</div>';
        h += row('Source: ' + src, base);
        h += row('CAS verified', hasCas ? 15 : 0);
        if (!isPoly) h += row('SMILES confirmed', hasSmi ? 10 : 0);
        if (srcN > 1) h += row('Cross-ref (' + srcN + ' sources)', crossBonus);
        h += '<div class="conf-sep"></div>';
        h += '<div class="conf-row"><span class="conf-label" style="color:#fff">Total</span><span class="conf-val" style="color:#fff">' + pct + '%</span></div>';
        _confTip.innerHTML = h;
        var rect = badge.getBoundingClientRect();
        _confTip.style.display = 'block';
        var tipW = _confTip.offsetWidth, tipH = _confTip.offsetHeight;
        var left = rect.left + rect.width / 2 - tipW / 2;
        var top = rect.bottom + 8;
        if (top + tipH > window.innerHeight) top = rect.top - tipH - 8;
        if (left < 4) left = 4;
        if (left + tipW > window.innerWidth - 4) left = window.innerWidth - tipW - 4;
        _confTip.style.left = left + 'px';
        _confTip.style.top = top + 'px';
    }} else if (_confTip && !_confTip.contains(e.target)) {{
        _confTip.style.display = 'none';
        _confBadgeActive = null;
    }}
}});

// ===================== CROSSLINK POPOVER =====================
var _xlPop = null;
var _xlType = null;
var _xlIdx = null;

function _ensurePopover() {{
    if (_xlPop) return;
    _xlPop = document.createElement('div');
    _xlPop.className = 'xl-popover';
    document.body.appendChild(_xlPop);
}}

function closeCrosslink() {{
    if (_xlPop) _xlPop.classList.remove('visible');
    _xlType = null;
    _xlIdx = null;
}}

function openCrosslink(event, type, idx) {{
    event.stopPropagation();
    _ensurePopover();
    _xlType = type;
    _xlIdx = idx;
    var mat = (type === 'solvents' ? SOLVENTS : POLYMERS)[idx];
    var opts = CAS_CANDIDATES[mat.name];
    if (!opts || !opts.length) {{ closeCrosslink(); return; }}

    var h = '<div class="xl-header"><span>CAS lookup: ' + mat.name + '</span><button class="xl-close" onclick="closeCrosslink()">&times;</button></div>';
    for (var i = 0; i < opts.length; i++) {{
        var o = opts[i];
        var pct = Math.round(o.conf * 100);
        var cColor = o.conf >= 0.8 ? '#27ae60' : (o.conf >= 0.5 ? '#f39c12' : '#e74c3c');
        h += '<div class="xl-opt" onclick="applyCrosslink(' + i + ')">';
        h += '<div><span class="xl-opt-name">' + o.name + '</span>';
        if (o.cas) h += ' <span class="xl-opt-cas">' + o.cas + '</span>';
        h += '<span class="xl-opt-conf" style="background:' + cColor + '">' + pct + '%</span>';
        if (o.mv_match === true) h += '<span class="xl-opt-mv match">Vm ✓</span>';
        else if (o.mv_match === false) h += '<span class="xl-opt-mv mismatch">Vm ' + (o.mv_pct != null ? o.mv_pct + '%↕' : '✗') + '</span>';
        h += '</div>';
        if (o.iupac) h += '<div class="xl-opt-detail">IUPAC: ' + o.iupac + '</div>';
        h += '<div class="xl-opt-detail">' + o.reason + '</div>';
        h += '</div>';
    }}
    _xlPop.innerHTML = h;
    _xlPop.classList.add('visible');

    // Position near the ? button
    var rect = event.target.getBoundingClientRect();
    var popW = 380, popH = _xlPop.offsetHeight || 300;
    var left = rect.right + 8;
    var top = rect.top;
    if (left + popW > window.innerWidth - 8) left = rect.left - popW - 8;
    if (top + popH > window.innerHeight - 8) top = Math.max(8, window.innerHeight - popH - 8);
    _xlPop.style.left = left + 'px';
    _xlPop.style.top = top + 'px';
}}

function applyCrosslink(optIdx) {{
    if (_xlType == null || _xlIdx == null) return;
    var mat = (_xlType === 'solvents' ? SOLVENTS : POLYMERS)[_xlIdx];
    var opts = CAS_CANDIDATES[mat.name];
    if (!opts || !opts[optIdx]) return;
    var o = opts[optIdx];

    // Apply CAS
    if (o.cas) setVal(_xlType, _xlIdx, 'cas', o.cas);
    // Apply corrected name if different
    if (o.name && o.name !== mat.name) setVal(_xlType, _xlIdx, 'name', o.name);
    // Apply MW if available and solvent
    if (_xlType === 'solvents' && o.mw) setVal(_xlType, _xlIdx, 'mw', String(o.mw));
    // Apply density if available and solvent
    if (_xlType === 'solvents' && o.density) setVal(_xlType, _xlIdx, 'density', String(o.density));

    closeCrosslink();
    renderTable();
}}

// Close popover / source dropdown on outside click
document.addEventListener('click', function(e) {{
    if (_xlPop && _xlPop.classList.contains('visible') && !_xlPop.contains(e.target) && !e.target.classList.contains('cas-missing')) {{
        closeCrosslink();
    }}
    // Close source filter dropdown
    if (_srcDropOpen) {{
        var drop = document.getElementById('src-drop');
        if (drop && !drop.contains(e.target) && !e.target.classList.contains('src-filter-btn')) {{
            _srcDropOpen = false;
            drop.classList.remove('open');
        }}
    }}
}});
</script>
</body>
</html>"""

db_output_path = os.path.join(os.path.dirname(__file__), "database.html")
with open(db_output_path, "w") as f:
    f.write(database_html)
print(f"Generated: {db_output_path}")
print(f"Database page: {len(db_solvents)} solvents, {len(db_polymers)} polymers")

# ===================== MANAGE PAGE =====================
# Load per-dataset data for the management page
DATASETS_DIR = os.path.join(os.path.dirname(__file__), "data", "datasets")
per_dataset_data = {}
for ds_id, ds_meta in DATASETS_META.items():
    ds_dir = os.path.join(DATASETS_DIR, ds_id)
    chems = []
    polys = []
    chem_path = os.path.join(ds_dir, "chemicals.csv")
    poly_path = os.path.join(ds_dir, "polymers.csv")
    if os.path.exists(chem_path):
        with open(chem_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                dd = row.get("delta_d", "").strip()
                dp = row.get("delta_p", "").strip()
                dh = row.get("delta_h", "").strip()
                if not (dd and dp and dh):
                    continue
                chems.append({
                    "name": row.get("name", "").strip(),
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
                    "conf": row.get("confidence", "").strip(),
                })
    if os.path.exists(poly_path):
        with open(poly_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                dd = row.get("delta_d", "").strip()
                dp = row.get("delta_p", "").strip()
                dh = row.get("delta_h", "").strip()
                if not (dd and dp and dh):
                    continue
                polys.append({
                    "name": row.get("name", "").strip(),
                    "cas": row.get("cas_number", "").strip(),
                    "dd": dd, "dp": dp, "dh": dh,
                    "r": row.get("radius", "").strip(),
                    "type": row.get("type", "").strip(),
                    "conf": row.get("confidence", "").strip(),
                })
    per_dataset_data[ds_id] = {"chemicals": chems, "polymers": polys, "meta": ds_meta}

per_dataset_json = json.dumps(per_dataset_data)

manage_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Materialism — Manage Datasets</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: #f5f6fa; color: #2d3436; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; display: flex; flex-direction: column; height: 100vh; }}
.header {{ background: #fff; padding: 15px 30px; display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #dfe6e9; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
.header h1 {{ font-size: 1.5rem; color: #e94560; }}
.header h1 a {{ color: #e94560; text-decoration: none; }}
.header .nav-links {{ color: #636e72; font-size: 0.9rem; display: flex; align-items: center; gap: 12px; }}
.header .nav-links a {{ color: #636e72; text-decoration: none; border-bottom: 1px dotted #b2bec3; cursor: pointer; }}
.main {{ display: flex; flex: 1; overflow: hidden; }}
.sidebar {{ width: 280px; background: #fff; border-right: 1px solid #dfe6e9; overflow-y: auto; padding: 12px; }}
.ds-card {{
    padding: 12px; margin-bottom: 8px; border: 1px solid #dfe6e9; border-radius: 6px;
    cursor: pointer; transition: all 0.2s;
}}
.ds-card:hover {{ border-color: #b2bec3; background: #f8f9fa; }}
.ds-card.active {{ border-color: #e94560; background: #fff5f7; }}
.ds-card h3 {{ font-size: 0.9rem; color: #2d3436; margin-bottom: 4px; }}
.ds-card .ds-counts {{ font-size: 0.75rem; color: #636e72; }}
.ds-card .ds-status {{ display: inline-block; font-size: 0.7rem; padding: 1px 6px; border-radius: 3px; margin-top: 4px; }}
.ds-card .ds-status.on {{ background: #d5f5e3; color: #27ae60; }}
.ds-card .ds-status.off {{ background: #fadbd8; color: #e74c3c; }}
.content {{ flex: 1; overflow: auto; padding: 20px; }}
.ds-detail-header {{ margin-bottom: 16px; }}
.ds-detail-header h2 {{ font-size: 1.2rem; color: #2d3436; margin-bottom: 6px; }}
.ds-detail-header .ds-meta {{ font-size: 0.82rem; color: #636e72; line-height: 1.6; }}
.ds-detail-header .ds-meta a {{ color: #0984e3; }}
.ds-detail-header .toggle-btn {{
    display: inline-block; padding: 4px 12px; border: 1px solid #dfe6e9; border-radius: 4px;
    font-size: 0.8rem; cursor: pointer; background: #fff; margin-top: 6px; transition: all 0.2s;
}}
.ds-detail-header .toggle-btn:hover {{ background: #f5f6fa; }}
.ds-detail-header .toggle-btn.on {{ border-color: #27ae60; color: #27ae60; }}
.ds-detail-header .toggle-btn.off {{ border-color: #e74c3c; color: #e74c3c; }}
.filter-row {{ margin-bottom: 10px; }}
.filter-row input {{ padding: 6px 10px; border: 1px solid #dfe6e9; border-radius: 4px; font-size: 0.82rem; width: 250px; }}
.filter-row input:focus {{ outline: none; border-color: #e94560; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; }}
th {{
    background: #f0f2f5; color: #e94560; padding: 8px 10px; text-align: left;
    font-weight: 600; position: sticky; top: 0; z-index: 1;
    border-bottom: 2px solid #dfe6e9; white-space: nowrap; cursor: pointer;
}}
th:hover {{ background: #e8eaed; }}
td {{ padding: 6px 10px; border-bottom: 1px solid #eee; white-space: nowrap; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }}
.empty-state {{
    text-align: center; padding: 60px 20px; color: #636e72;
}}
.empty-state h2 {{ font-size: 1.4rem; color: #2d3436; margin-bottom: 12px; }}
.empty-state p {{ font-size: 0.95rem; line-height: 1.6; max-width: 500px; margin: 0 auto; }}
.empty-state code {{ background: #f0f2f5; padding: 2px 6px; border-radius: 3px; font-size: 0.85rem; }}
/* Import panels */
.import-section {{ margin-bottom: 16px; border-bottom: 1px solid #dfe6e9; padding-bottom: 12px; }}
.import-section h4 {{
    font-size: 0.8rem; color: #636e72; text-transform: uppercase; letter-spacing: 0.5px;
    margin-bottom: 8px; cursor: pointer; user-select: none;
}}
.import-section h4:hover {{ color: #2d3436; }}
.import-section h4::before {{ content: '\\25B6 '; font-size: 0.6rem; }}
.import-section h4.open::before {{ content: '\\25BC '; }}
.import-panel {{ display: none; }}
.import-panel.open {{ display: block; }}
.drop-zone {{
    border: 2px dashed #dfe6e9; border-radius: 6px; padding: 18px 12px; text-align: center;
    font-size: 0.8rem; color: #636e72; cursor: pointer; transition: all 0.2s; margin-bottom: 8px;
}}
.drop-zone:hover, .drop-zone.dragover {{ border-color: #e94560; background: #fff5f7; color: #e94560; }}
.drop-zone input[type="file"] {{ display: none; }}
.import-input {{
    width: 100%; padding: 6px 8px; border: 1px solid #dfe6e9; border-radius: 4px;
    font-size: 0.8rem; margin-bottom: 6px;
}}
.import-input:focus {{ outline: none; border-color: #e94560; }}
.import-btn {{
    width: 100%; padding: 6px 0; border: none; border-radius: 4px; font-size: 0.8rem;
    cursor: pointer; transition: all 0.2s; background: #e94560; color: #fff;
}}
.import-btn:hover {{ background: #d63851; }}
.import-btn:disabled {{ background: #b2bec3; cursor: not-allowed; }}
.import-btn.secondary {{ background: #fff; color: #636e72; border: 1px solid #dfe6e9; }}
.import-btn.secondary:hover {{ background: #f5f6fa; }}
.analysis-card {{
    background: #fff; border: 1px solid #dfe6e9; border-radius: 8px; padding: 20px; margin-bottom: 16px;
}}
.analysis-card h3 {{ font-size: 1rem; color: #2d3436; margin-bottom: 12px; }}
.analysis-stat {{ display: inline-block; margin-right: 16px; margin-bottom: 8px; }}
.analysis-stat .label {{ font-size: 0.75rem; color: #636e72; }}
.analysis-stat .value {{ font-size: 1.1rem; font-weight: 600; color: #2d3436; }}
.analysis-issue {{ padding: 4px 8px; margin: 2px 0; border-radius: 3px; font-size: 0.8rem; }}
.analysis-issue.warning {{ background: #ffeaa7; color: #856404; }}
.analysis-issue.error {{ background: #fab1a0; color: #721c24; }}
.mapping-table {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; margin: 8px 0; }}
.mapping-table th {{ background: #f0f2f5; padding: 4px 8px; text-align: left; font-size: 0.75rem; }}
.mapping-table td {{ padding: 4px 8px; border-bottom: 1px solid #eee; }}
.mapping-table select {{ font-size: 0.8rem; padding: 2px 4px; border: 1px solid #dfe6e9; border-radius: 3px; }}
.import-form {{ margin-top: 12px; display: flex; gap: 8px; align-items: end; flex-wrap: wrap; }}
.import-form label {{ font-size: 0.8rem; color: #636e72; }}
.import-form input {{ padding: 6px 8px; border: 1px solid #dfe6e9; border-radius: 4px; font-size: 0.8rem; }}
.search-result-card {{
    background: #fff; border: 1px solid #dfe6e9; border-radius: 6px; padding: 14px; margin-bottom: 10px;
}}
.search-result-card h4 {{ font-size: 0.9rem; color: #2d3436; margin-bottom: 4px; }}
.search-result-card .sr-desc {{ font-size: 0.82rem; color: #636e72; margin-bottom: 6px; }}
.search-result-card .sr-tags {{ display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 6px; }}
.search-result-card .sr-tag {{ font-size: 0.7rem; padding: 2px 6px; border-radius: 3px; background: #f0f2f5; color: #636e72; }}
.search-result-card .sr-tag.good {{ background: #d5f5e3; color: #27ae60; }}
.search-result-card .sr-tag.warn {{ background: #ffeaa7; color: #856404; }}
.loading {{ text-align: center; padding: 30px; color: #636e72; }}
.loading::after {{ content: ''; display: inline-block; width: 18px; height: 18px; border: 2px solid #dfe6e9; border-top-color: #e94560; border-radius: 50%; animation: spin 0.8s linear infinite; margin-left: 8px; vertical-align: middle; }}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
.rebuild-btn {{
    width: 100%; padding: 8px 0; margin-top: 12px; border: 1px solid #dfe6e9; border-radius: 4px;
    background: #fff; color: #636e72; font-size: 0.8rem; cursor: pointer; transition: all 0.2s;
}}
.rebuild-btn:hover {{ background: #f5f6fa; border-color: #b2bec3; }}
/* Inferred value styles */
td.inferred {{ background: #edf7ed; }}
td .q-mark {{ color: #e67e22; font-size: 0.65rem; vertical-align: super; font-weight: 700; cursor: help; }}
td .src-dot {{ display: inline-block; width: 5px; height: 5px; border-radius: 50%; margin-left: 3px; vertical-align: middle; }}
td .src-dot.pubchem {{ background: #3498db; }}
td .src-dot.cas {{ background: #27ae60; }}
td .src-dot.both {{ background: #8e44ad; }}
td .src-dot.dataset {{ background: #95a5a6; }}
.cell-tooltip {{
    position: fixed; z-index: 9999; background: #2d3436; color: #fff; padding: 6px 10px;
    border-radius: 4px; font-size: 0.72rem; max-width: 320px; pointer-events: none;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25); line-height: 1.4;
}}
.cell-tooltip a {{ color: #74b9ff; }}
.infer-btn {{
    display: inline-block; padding: 4px 12px; border: 1px solid #0984e3; border-radius: 4px;
    font-size: 0.8rem; cursor: pointer; background: #fff; color: #0984e3; margin-left: 8px;
    margin-top: 6px; transition: all 0.2s;
}}
.infer-btn:hover {{ background: #0984e3; color: #fff; }}
.infer-btn:disabled {{ border-color: #b2bec3; color: #b2bec3; cursor: not-allowed; background: #f5f6fa; }}
.infer-progress {{ background: #fff; border: 1px solid #dfe6e9; border-radius: 6px; padding: 12px; margin-bottom: 12px; }}
.infer-progress .bar-bg {{ background: #eee; border-radius: 3px; height: 6px; margin: 8px 0; }}
.infer-progress .bar-fg {{ background: #0984e3; border-radius: 3px; height: 6px; transition: width 0.3s; }}
.api-key-row {{ display: flex; gap: 4px; margin-bottom: 6px; }}
.api-key-row input {{ flex: 1; font-size: 0.72rem; padding: 4px 6px; }}
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
</head>
<body>
<div class="header">
    <h1><a href="materialism.html">Materialism</a> &mdash; Manage Datasets</h1>
    <div class="nav-links">
        <a href="database.html">Database</a>
        <a href="materialism.html">Search</a>
    </div>
</div>
<div class="main">
    <div class="sidebar" id="sidebar">
        <div class="import-section">
            <h4 onclick="togglePanel('upload-panel', this)" class="open">Upload File</h4>
            <div class="import-panel open" id="upload-panel">
                <div class="drop-zone" id="drop-zone" onclick="document.getElementById('file-input').click()">
                    Drop CSV, Excel, JSON, or PDF here<br><small>or click to browse</small>
                    <input type="file" id="file-input" accept=".csv,.xlsx,.xls,.json,.pdf,.tsv">
                </div>
            </div>
            <h4 onclick="togglePanel('url-panel', this)">From URL</h4>
            <div class="import-panel" id="url-panel">
                <input class="import-input" id="url-input" placeholder="https://example.com/data.csv">
                <button class="import-btn" onclick="analyzeUrl()">Analyze</button>
            </div>
            <h4 onclick="togglePanel('search-panel', this)">Search Databases</h4>
            <div class="import-panel" id="search-panel">
                <div class="api-key-row">
                    <input class="import-input" id="claude-api-key" type="password" placeholder="Claude API key (sk-ant-...)" style="margin-bottom:0">
                    <button class="import-btn secondary" style="width:auto;padding:2px 8px;font-size:0.7rem" onclick="saveApiKey()">Save</button>
                </div>
                <input class="import-input" id="search-input" placeholder="e.g. polymer HSP databases">
                <button class="import-btn" onclick="searchDatabases()">Search</button>
            </div>
        </div>
        <div id="ds-list"></div>
        <button class="rebuild-btn" onclick="triggerRebuild()">Export Datasets</button>
    </div>
    <div class="content" id="content">
        <div class="empty-state" id="empty-state">
            <h2>Welcome to Materialism</h2>
            <p>Upload a CSV or Excel file using the panel on the left to get started.</p>
        </div>
    </div>
</div>
<script>
var DATASETS = {per_dataset_json};
var _LS_DS_KEY = 'materialism_active_datasets';
function _loadA() {{ try {{ var v = localStorage.getItem(_LS_DS_KEY); return v ? JSON.parse(v) : null; }} catch(e) {{ return null; }} }}
function _saveA(obj) {{ try {{ localStorage.setItem(_LS_DS_KEY, JSON.stringify(obj)); }} catch(e) {{}} }}
function _getA() {{ var s = _loadA(); if (s) return s; var d = {{}}; Object.keys(DATASETS).forEach(function(k) {{ d[k] = true; }}); return d; }}
var _activeDsets = _getA();
var _currentDs = null;
var _filterText = '';
var _sortCol = null;
var _sortAsc = true;

// --- Import panel toggling ---
function togglePanel(panelId, header) {{
    var p = document.getElementById(panelId);
    var isOpen = p.classList.contains('open');
    // Close all panels
    document.querySelectorAll('.import-panel').forEach(function(el) {{ el.classList.remove('open'); }});
    document.querySelectorAll('.import-section h4').forEach(function(el) {{ el.classList.remove('open'); }});
    if (!isOpen) {{
        p.classList.add('open');
        header.classList.add('open');
    }}
}}

// --- Column alias sets for auto-mapping (mirrors lib/schema.py) ---
var _ALIASES = {{
    name: ['name','chemical','compound','solvent','material','molecule'],
    cas_number: ['cas','cas_number','cas_no','casrn','cas number','cas #'],
    delta_d: ['delta_d','dd','dispersion','\\u03b4d','deltad','d_d','hansen_d','dd_mpa05','dd_mpa0.5','\\u03b4d (mpa^0.5)'],
    delta_p: ['delta_p','dp','polar','polarity','\\u03b4p','deltap','d_p','hansen_p','dp_mpa05','dp_mpa0.5','\\u03b4p (mpa^0.5)'],
    delta_h: ['delta_h','dh','hydrogen','h-h bonding','h_bonding','\\u03b4h','deltah','d_h','hansen_h','dh_mpa05','dh_mpa0.5','\\u03b4h (mpa^0.5)','hydrogen_bonding'],
    molecular_weight: ['molecular_weight','mw','mol_weight','molar_mass','mwt_g_mol'],
    boiling_point: ['boiling_point','bp','boiling','b.p.','tb_c'],
    density: ['density','rho','\\u03c1','density_g_cm3'],
    molar_volume: ['molar_volume','mv','mol_volume','vm','mvol_cm3_mol','volume_cm3_per_mol'],
    category: ['category','type','class','group'],
    smiles: ['smiles','smi'],
    molecular_formula: ['molecular_formula','formula','molecular formula'],
    ghs_hazard: ['ghs_hazard','ghs','h_statements','hazard'],
    radius: ['radius','r0','r_0','interaction_radius'],
}};

function _autoMap(headers) {{
    var mapping = {{}}, used = {{}};
    var lowerMap = {{}};
    headers.forEach(function(h) {{ lowerMap[h.toLowerCase().trim()] = h; }});
    Object.keys(_ALIASES).forEach(function(canon) {{
        _ALIASES[canon].forEach(function(alias) {{
            if (lowerMap[alias] && !used[canon]) {{
                var orig = lowerMap[alias];
                if (!mapping[orig]) {{
                    mapping[orig] = canon;
                    used[canon] = true;
                }}
            }}
        }});
    }});
    return mapping;
}}

function _parseFloat(v) {{
    if (v == null || v === '') return null;
    var n = parseFloat(String(v).replace(',','.'));
    return isNaN(n) ? null : n;
}}

function _normCAS(v) {{
    if (!v) return '';
    var s = String(v).trim();
    if (/^\\d{{2,7}}-\\d{{2}}-\\d$/.test(s)) return s;
    var digits = s.replace(/\\D/g, '');
    if (digits.length >= 5 && digits.length <= 10) {{
        return digits.slice(0,-3) + '-' + digits.slice(-3,-1) + '-' + digits.slice(-1);
    }}
    return '';
}}

// --- Client-side file parsing ---
function _parseCSVText(text) {{
    var delim = (text.indexOf('\\t') > -1 && text.split('\\t').length > text.split(',').length) ? '\\t' : ',';
    var lines = text.split(/\\r?\\n/);
    var headers = lines[0].split(delim).map(function(h) {{ return h.trim().replace(/^["']|["']$/g, ''); }});
    var rows = [];
    for (var i = 1; i < lines.length; i++) {{
        if (!lines[i].trim()) continue;
        var vals = lines[i].split(delim);
        var row = {{}};
        headers.forEach(function(h, j) {{
            var v = (vals[j] || '').trim().replace(/^["']|["']$/g, '');
            row[h] = v;
        }});
        rows.push(row);
    }}
    return {{ headers: headers, rows: rows }};
}}

function _parseExcelBuffer(buf) {{
    if (typeof XLSX === 'undefined') {{
        throw new Error('SheetJS library not loaded. Check internet connection.');
    }}
    var wb = XLSX.read(buf, {{ type: 'array' }});
    var ws = wb.Sheets[wb.SheetNames[0]];
    var data = XLSX.utils.sheet_to_json(ws, {{ defval: '' }});
    var headers = data.length > 0 ? Object.keys(data[0]) : [];
    return {{ headers: headers, rows: data }};
}}

function _analyzeLocally(headers, rows, filename) {{
    var mapping = _autoMap(headers);
    var rev = {{}};
    Object.keys(mapping).forEach(function(k) {{ rev[mapping[k]] = k; }});

    var total = rows.length;
    var hspCount = 0, casCount = 0, smilesCount = 0, outliers = 0, dupNames = 0;
    var namesSeen = {{}}, hasRadius = false;

    rows.forEach(function(row) {{
        var dd = _parseFloat(row[rev.delta_d]);
        var dp = _parseFloat(row[rev.delta_p]);
        var dh = _parseFloat(row[rev.delta_h]);
        if (dd != null && dp != null && dh != null) {{
            hspCount++;
            if (dd < 10 || dd > 25 || dp < 0 || dp > 25 || dh < 0 || dh > 30) outliers++;
        }}
        var cas = rev.cas_number ? _normCAS(row[rev.cas_number]) : '';
        if (cas) casCount++;
        var smi = rev.smiles ? String(row[rev.smiles] || '').trim() : '';
        if (smi && smi !== 'None' && smi !== 'nan') smilesCount++;
        if (rev.radius && _parseFloat(row[rev.radius]) != null) hasRadius = true;
        var nm = rev.name ? String(row[rev.name] || '').trim().toLowerCase() : '';
        if (nm) {{ if (namesSeen[nm]) dupNames++; namesSeen[nm] = true; }}
    }});

    var issues = [];
    if (!rev.name) issues.push({{ severity: 'error', message: 'No name column detected' }});
    if (!rev.delta_d || !rev.delta_p || !rev.delta_h) issues.push({{ severity: 'error', message: 'Missing HSP columns (need delta_d, delta_p, delta_h)' }});
    if (outliers > 0) issues.push({{ severity: 'warning', message: outliers + ' rows have HSP values outside typical ranges' }});
    if (dupNames > 0) issues.push({{ severity: 'warning', message: dupNames + ' duplicate names within this dataset' }});

    var sampleRows = rows.slice(0, 5).map(function(row) {{
        var s = {{}};
        Object.keys(mapping).forEach(function(k) {{ s[mapping[k]] = String(row[k] || '').substring(0, 80); }});
        return s;
    }});

    var ext = (filename || '').split('.').pop().toLowerCase();
    var fileType = (ext === 'xlsx' || ext === 'xls') ? 'excel' : ext === 'json' ? 'json' : 'csv';

    return {{
        file_type: fileType,
        original_filename: filename,
        row_count: total,
        columns_found: headers,
        column_mapping: mapping,
        unmapped_columns: headers.filter(function(h) {{ return !mapping[h]; }}),
        hsp_coverage: total > 0 ? Math.round(1000 * hspCount / total) / 10 : 0,
        cas_coverage: total > 0 ? Math.round(1000 * casCount / total) / 10 : 0,
        smiles_coverage: total > 0 ? Math.round(1000 * smilesCount / total) / 10 : 0,
        quality_issues: issues,
        sample_rows: sampleRows,
        detected_type: hasRadius ? 'both' : 'chemicals',
        _headers: headers,
        _rows: rows,
    }};
}}

// --- File upload via drag-and-drop / file picker ---
var _dropZone = document.getElementById('drop-zone');
var _fileInput = document.getElementById('file-input');
_dropZone.addEventListener('dragover', function(e) {{ e.preventDefault(); _dropZone.classList.add('dragover'); }});
_dropZone.addEventListener('dragleave', function() {{ _dropZone.classList.remove('dragover'); }});
_dropZone.addEventListener('drop', function(e) {{ e.preventDefault(); _dropZone.classList.remove('dragover'); if (e.dataTransfer.files.length) uploadFile(e.dataTransfer.files[0]); }});
_fileInput.addEventListener('change', function() {{ if (_fileInput.files.length) uploadFile(_fileInput.files[0]); _fileInput.value=''; }});

var _pendingAnalysis = null;

function uploadFile(file) {{
    var ct = document.getElementById('content');
    ct.innerHTML = '<div class="loading">Analyzing ' + file.name + '...</div>';
    var reader = new FileReader();
    reader.onerror = function() {{ ct.innerHTML = '<div class="analysis-card"><h3>Error</h3><p>Failed to read file.</p></div>'; }};
    reader.onload = function(e) {{
        try {{
            var parsed;
            var ext = file.name.split('.').pop().toLowerCase();
            if (ext === 'xlsx' || ext === 'xls') {{
                parsed = _parseExcelBuffer(new Uint8Array(e.target.result));
            }} else if (ext === 'json') {{
                var data = JSON.parse(new TextDecoder().decode(new Uint8Array(e.target.result)));
                if (Array.isArray(data)) {{
                    parsed = {{ headers: data.length ? Object.keys(data[0]) : [], rows: data }};
                }} else {{
                    var arr = null;
                    ['data','chemicals','solvents','compounds','results','entries'].forEach(function(k) {{ if (!arr && data[k] && Array.isArray(data[k])) arr = data[k]; }});
                    if (!arr) Object.values(data).forEach(function(v) {{ if (!arr && Array.isArray(v) && v.length && typeof v[0] === 'object') arr = v; }});
                    arr = arr || [];
                    parsed = {{ headers: arr.length ? Object.keys(arr[0]) : [], rows: arr }};
                }}
            }} else {{
                parsed = _parseCSVText(new TextDecoder().decode(new Uint8Array(e.target.result)));
            }}
            var report = _analyzeLocally(parsed.headers, parsed.rows, file.name);
            _pendingAnalysis = report;
            showAnalysis(report);
        }} catch(err) {{
            ct.innerHTML = '<div class="analysis-card"><h3>Error</h3><p>' + err.message + '</p></div>';
        }}
    }};
    reader.readAsArrayBuffer(file);
}}

function analyzeUrl() {{
    var ct = document.getElementById('content');
    ct.innerHTML = '<div class="analysis-card"><h3>URL Import</h3><p>URL analysis requires the API server.<br>Start it with: <code>python -m backend.app.main</code><br>Or download the file and upload it directly.</p></div>';
}}

function searchDatabases() {{
    var ct = document.getElementById('content');
    ct.innerHTML = '<div class="analysis-card"><h3>Search</h3><p>Database search requires the API server with a Claude API key.<br>Start it with: <code>python -m backend.app.main</code></p></div>';
}}

function showAnalysis(report) {{
    var ct = document.getElementById('content');
    var h = '<div class="analysis-card">';
    h += '<h3>Analysis: ' + (report.original_filename || 'File') + '</h3>';
    h += '<div style="margin-bottom:12px">';
    h += '<span class="analysis-stat"><span class="label">Type</span><br><span class="value">' + report.file_type + '</span></span>';
    h += '<span class="analysis-stat"><span class="label">Rows</span><br><span class="value">' + report.row_count + '</span></span>';
    h += '<span class="analysis-stat"><span class="label">Detected</span><br><span class="value">' + report.detected_type + '</span></span>';
    h += '<span class="analysis-stat"><span class="label">HSP</span><br><span class="value">' + report.hsp_coverage + '%</span></span>';
    h += '<span class="analysis-stat"><span class="label">CAS</span><br><span class="value">' + report.cas_coverage + '%</span></span>';
    h += '<span class="analysis-stat"><span class="label">SMILES</span><br><span class="value">' + report.smiles_coverage + '%</span></span>';
    h += '</div>';

    // Quality issues
    if (report.quality_issues && report.quality_issues.length > 0) {{
        h += '<div style="margin-bottom:12px">';
        report.quality_issues.forEach(function(iss) {{
            h += '<div class="analysis-issue ' + iss.severity + '">' + iss.message + '</div>';
        }});
        h += '</div>';
    }}

    // Column mapping (editable)
    if (report.column_mapping) {{
        var canonicals = ['name','cas_number','delta_d','delta_p','delta_h','molecular_weight','boiling_point','density','molar_volume','smiles','molecular_formula','ghs_hazard','category','radius'];
        h += '<table class="mapping-table"><thead><tr><th>Source Column</th><th>Maps To</th></tr></thead><tbody>';
        var allCols = report.columns_found || [];
        allCols.forEach(function(col) {{
            var mapped = report.column_mapping[col] || '';
            h += '<tr><td>' + col + '</td><td><select data-col="' + col + '" class="mapping-select">';
            h += '<option value="">(unmapped)</option>';
            canonicals.forEach(function(c) {{ h += '<option value="' + c + '"' + (mapped === c ? ' selected' : '') + '>' + c + '</option>'; }});
            h += '</select></td></tr>';
        }});
        h += '</tbody></table>';
    }}

    // Sample rows
    if (report.sample_rows && report.sample_rows.length > 0) {{
        h += '<details style="margin-top:8px"><summary style="font-size:0.85rem;cursor:pointer;color:#636e72">Sample rows (' + report.sample_rows.length + ')</summary>';
        h += '<table class="mapping-table" style="margin-top:4px"><thead><tr>';
        var sampleKeys = Object.keys(report.sample_rows[0]);
        sampleKeys.forEach(function(k) {{ h += '<th>' + k + '</th>'; }});
        h += '</tr></thead><tbody>';
        report.sample_rows.forEach(function(row) {{
            h += '<tr>';
            sampleKeys.forEach(function(k) {{ h += '<td>' + (row[k]||'') + '</td>'; }});
            h += '</tr>';
        }});
        h += '</tbody></table></details>';
    }}

    // Import form
    h += '<div class="import-form">';
    h += '<div><label>Dataset ID</label><br><input id="import-id" placeholder="my_dataset" style="width:180px"></div>';
    h += '<div><label>Name</label><br><input id="import-name" placeholder="My Dataset" style="width:220px"></div>';
    h += '<div><label>Source URL</label><br><input id="import-url" placeholder="https://..." style="width:220px" value="' + (report.original_url || '').replace(/"/g,'&quot;') + '"></div>';
    h += '<div><label>Confidence</label><br><input id="import-conf" type="number" step="0.05" min="0" max="1" value="0.30" style="width:70px"></div>';
    h += '<div style="padding-top:18px"><button class="import-btn" style="width:auto;padding:6px 20px" onclick="doImport()">Import</button></div>';
    h += '</div>';

    h += '</div>';
    ct.innerHTML = h;
}}

function doImport() {{
    if (!_pendingAnalysis) return;
    var dsId = document.getElementById('import-id').value.trim();
    if (!dsId) {{ alert('Dataset ID is required'); return; }}
    if (!/^[a-z0-9_]+$/.test(dsId)) {{ alert('ID must be lowercase alphanumeric with underscores'); return; }}

    // Collect edited column mapping
    var mapping = {{}};
    document.querySelectorAll('.mapping-select').forEach(function(sel) {{
        var col = sel.getAttribute('data-col');
        if (sel.value) mapping[col] = sel.value;
    }});

    var rev = {{}};
    Object.keys(mapping).forEach(function(k) {{ rev[mapping[k]] = k; }});

    var dsName = document.getElementById('import-name').value.trim() || dsId;
    var sourceUrl = document.getElementById('import-url').value.trim();
    var confTier = parseFloat(document.getElementById('import-conf').value) || 0.30;

    // Normalize rows into chemicals/polymers
    var rows = _pendingAnalysis._rows || [];
    var chemicals = [], polymers = [];
    rows.forEach(function(row) {{
        var name = rev.name ? String(row[rev.name] || '').trim() : '';
        if (!name) return;
        var dd = _parseFloat(row[rev.delta_d]);
        var dp = _parseFloat(row[rev.delta_p]);
        var dh = _parseFloat(row[rev.delta_h]);
        if (dd == null || dp == null || dh == null) return;
        var cas = rev.cas_number ? _normCAS(row[rev.cas_number]) : '';
        var radius = rev.radius ? _parseFloat(row[rev.radius]) : null;
        if (radius != null) {{
            polymers.push({{
                name: name, cas: cas, dd: dd, dp: dp, dh: dh, r: radius,
                type: rev.category ? String(row[rev.category] || '').trim() : '',
                conf: confTier, dsId: dsId
            }});
        }} else {{
            chemicals.push({{
                name: name, cas: cas, dd: dd, dp: dp, dh: dh,
                mw: rev.molecular_weight ? _parseFloat(row[rev.molecular_weight]) : null,
                bp: rev.boiling_point ? _parseFloat(row[rev.boiling_point]) : null,
                cat: rev.category ? String(row[rev.category] || '').trim() : '',
                smiles: rev.smiles ? String(row[rev.smiles] || '').trim() : '',
                density: rev.density ? _parseFloat(row[rev.density]) : null,
                conf: confTier, dsId: dsId
            }});
        }}
    }});

    var meta = {{
        id: dsId, name: dsName, source_url: sourceUrl,
        imported_at: new Date().toISOString(),
        chemical_count: chemicals.length, polymer_count: polymers.length,
        confidence_tier: confTier,
        fields_available: Object.values(mapping),
    }};

    // Save to DATASETS and localStorage
    DATASETS[dsId] = {{ chemicals: chemicals, polymers: polymers, meta: meta }};
    _activeDsets[dsId] = true;
    _saveA(_activeDsets);
    _saveImportedDatasets();

    var ct = document.getElementById('content');
    ct.innerHTML = '<div class="analysis-card"><h3>Imported!</h3><p>' + chemicals.length + ' chemicals, ' + polymers.length + ' polymers imported as <b>' + dsId + '</b>.</p></div>';
    _pendingAnalysis = null;
    buildSidebar();
}}

// --- localStorage persistence for imported datasets ---
var _LS_IMPORTED_KEY = 'materialism_imported_datasets';

function _saveImportedDatasets() {{
    // Save all datasets that were imported in-browser (not embedded from generate_html.py)
    var toSave = {{}};
    Object.keys(DATASETS).forEach(function(k) {{
        if (DATASETS[k]._imported) toSave[k] = DATASETS[k];
    }});
    // Mark current import
    Object.keys(DATASETS).forEach(function(k) {{
        if (!DATASETS[k]._embedded) {{
            DATASETS[k]._imported = true;
            toSave[k] = {{ chemicals: DATASETS[k].chemicals, polymers: DATASETS[k].polymers, meta: DATASETS[k].meta }};
        }}
    }});
    try {{ localStorage.setItem(_LS_IMPORTED_KEY, JSON.stringify(toSave)); }} catch(e) {{}}
}}

function _loadImportedDatasets() {{
    try {{
        var raw = localStorage.getItem(_LS_IMPORTED_KEY);
        if (!raw) return;
        var saved = JSON.parse(raw);
        Object.keys(saved).forEach(function(k) {{
            if (!DATASETS[k]) {{
                DATASETS[k] = saved[k];
                DATASETS[k]._imported = true;
            }}
        }});
    }} catch(e) {{}}
}}

// _loadImportedDatasets() is called in the init block below after marking embedded datasets

// --- Claude API key (stored in localStorage) ---
var _LS_API_KEY = 'materialism_claude_api_key';
function saveApiKey() {{
    var k = document.getElementById('claude-api-key').value.trim();
    if (k) {{ localStorage.setItem(_LS_API_KEY, k); alert('API key saved.'); }}
}}
function _getApiKey() {{ return localStorage.getItem(_LS_API_KEY) || ''; }}
// Load saved key into input on page load
setTimeout(function() {{
    var saved = _getApiKey();
    if (saved) document.getElementById('claude-api-key').value = saved;
}}, 0);

// --- PubChem + CAS Common Chemistry lookup ---
function _delay(ms) {{ return new Promise(function(r) {{ setTimeout(r, ms); }}); }}

function _pubchemLookup(query, isCAS) {{
    var encoded = encodeURIComponent(query);
    var propUrl = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/' + encoded + '/property/MolecularWeight,MolecularFormula,CanonicalSMILES,IUPACName/JSON';
    return fetch(propUrl).then(function(r) {{
        if (!r.ok) return null;
        return r.json();
    }}).then(function(data) {{
        if (!data || !data.PropertyTable || !data.PropertyTable.Properties || !data.PropertyTable.Properties[0]) return null;
        var p = data.PropertyTable.Properties[0];
        var result = {{
            mw: p.MolecularWeight || null,
            formula: p.MolecularFormula || '',
            smiles: p.CanonicalSMILES || '',
            iupac: p.IUPACName || '',
            cid: p.CID || null,
            source: 'PubChem',
            url: p.CID ? 'https://pubchem.ncbi.nlm.nih.gov/compound/' + p.CID : '',
        }};
        // If we have a CID, try to get CAS from synonyms
        if (result.cid && !isCAS) {{
            return _delay(150).then(function() {{
                return fetch('https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/' + result.cid + '/synonyms/JSON');
            }}).then(function(r2) {{
                if (!r2.ok) return result;
                return r2.json().then(function(synData) {{
                    var syns = (synData.InformationList && synData.InformationList.Information && synData.InformationList.Information[0] && synData.InformationList.Information[0].Synonym) || [];
                    for (var i = 0; i < syns.length; i++) {{
                        if (/^\\d{{2,7}}-\\d{{2}}-\\d$/.test(syns[i])) {{
                            result.cas = syns[i];
                            break;
                        }}
                    }}
                    return result;
                }});
            }}).catch(function() {{ return result; }});
        }}
        return result;
    }}).catch(function() {{ return null; }});
}}

function _casChemSearch(query) {{
    return fetch('https://commonchemistry.cas.org/api/search?q=' + encodeURIComponent(query))
        .then(function(r) {{ if (!r.ok) return null; return r.json(); }})
        .then(function(data) {{
            if (!data || !data.results || data.results.length === 0) return null;
            return data.results[0].rn;
        }}).catch(function() {{ return null; }});
}}

function _casChemDetail(casRn) {{
    return fetch('https://commonchemistry.cas.org/api/detail?cas_rn=' + encodeURIComponent(casRn))
        .then(function(r) {{ if (!r.ok) return null; return r.json(); }})
        .then(function(d) {{
            if (!d) return null;
            // Strip HTML tags from name
            var nm = (d.name || '').replace(/<[^>]*>/g, '');
            // Parse MW from string
            var mwStr = (d.molecularMass || '').replace(/[^\\d.]/g, '');
            return {{
                name: nm,
                cas: d.rn || casRn,
                mw: mwStr ? parseFloat(mwStr) : null,
                formula: (d.molecularFormula || '').replace(/<[^>]*>/g, ''),
                smiles: d.smile || '',
                source: 'CAS Common Chemistry',
                url: 'https://commonchemistry.cas.org/detail?cas_rn=' + encodeURIComponent(casRn),
            }};
        }}).catch(function() {{ return null; }});
}}

function _mwClose(a, b) {{
    if (a == null || b == null) return false;
    return Math.abs(a - b) / Math.max(a, b) < 0.01;
}}

// --- Infer missing values engine ---
var _inferRunning = false;
var _inferCancelled = false;

async function inferMissing(dsId) {{
    if (_inferRunning) return;
    _inferRunning = true;
    _inferCancelled = false;
    // Show progress bar
    var progEl = document.getElementById('infer-progress');
    if (progEl) {{ progEl.style.display = 'block'; progEl.innerHTML = '<div class="loading" style="padding:8px">Starting inference...</div>'; }}
    var btn = document.getElementById('infer-btn');
    if (btn) btn.disabled = true;
    var ds = DATASETS[dsId];
    var items = (ds.chemicals && ds.chemicals.length > 0) ? ds.chemicals : ds.polymers || [];
    var fillable = ['cas','mw','smiles'];
    var queue = [];

    items.forEach(function(item, idx) {{
        var missing = fillable.filter(function(f) {{
            var v = item[f];
            return v == null || v === '' || v === 0;
        }});
        if (missing.length > 0) queue.push({{ item: item, idx: idx, missing: missing }});
    }});

    if (queue.length === 0) {{
        _inferRunning = false;
        var ct = document.getElementById('content');
        var bar = document.getElementById('infer-progress');
        if (bar) bar.innerHTML = '<span style="color:#27ae60;font-size:0.82rem">All fields already populated. Nothing to infer.</span>';
        return;
    }}

    var filled = 0, errors = 0;
    for (var i = 0; i < queue.length; i++) {{
        if (_inferCancelled) break;
        var entry = queue[i];
        var item = entry.item;
        // Ensure _src tracking object
        if (!item._src) item._src = {{}};

        // Show progress
        var bar = document.getElementById('infer-progress');
        if (bar) {{
            var pct = Math.round(100 * (i + 1) / queue.length);
            bar.innerHTML = '<div style="font-size:0.8rem;color:#2d3436">Looking up <b>' + (item.name||'').substring(0,40) + '</b> (' + (i+1) + '/' + queue.length + ')</div>'
                + '<div class="bar-bg"><div class="bar-fg" style="width:' + pct + '%"></div></div>'
                + '<button class="import-btn secondary" style="width:auto;padding:2px 10px;font-size:0.72rem;margin-top:4px" onclick="_inferCancelled=true">Cancel</button>';
        }}

        try {{
            // --- PubChem lookup ---
            var pub = null;
            var lookupByCAS = false;
            if (item.cas && item.cas.length > 3) {{
                pub = await _pubchemLookup(item.cas, true);
                if (pub) lookupByCAS = true;
            }}
            if (!pub && item.name) {{
                await _delay(200);
                pub = await _pubchemLookup(item.name, false);
            }}

            // --- CAS Common Chemistry lookup ---
            var casChem = null;
            var casRnToLookup = item.cas || (pub && pub.cas);
            if (casRnToLookup) {{
                await _delay(200);
                casChem = await _casChemDetail(casRnToLookup);
            }} else if (item.name && !pub) {{
                // Try CAS search by name
                await _delay(200);
                var foundCas = await _casChemSearch(item.name);
                if (foundCas) {{
                    await _delay(200);
                    casChem = await _casChemDetail(foundCas);
                }}
            }}

            // --- Fill missing values ---
            entry.missing.forEach(function(field) {{
                var pubVal = null, casVal = null, pubUrl = '', casUrl = '';
                if (pub) {{
                    pubUrl = pub.url || '';
                    if (field === 'cas') pubVal = pub.cas || null;
                    else if (field === 'mw') pubVal = pub.mw;
                    else if (field === 'smiles') pubVal = pub.smiles || null;
                }}
                if (casChem) {{
                    casUrl = casChem.url || '';
                    if (field === 'cas') casVal = casChem.cas || null;
                    else if (field === 'mw') casVal = casChem.mw;
                    else if (field === 'smiles') casVal = casChem.smiles || null;
                }}

                var val = null, uncertain = false, srcLabel = '', srcUrl = '';
                if (pubVal != null && pubVal !== '' && casVal != null && casVal !== '') {{
                    // Both sources have a value
                    var match = (field === 'mw') ? _mwClose(pubVal, casVal) : (String(pubVal) === String(casVal));
                    if (match) {{
                        val = pubVal; srcLabel = 'PubChem + CAS Common Chemistry';
                        srcUrl = pubUrl;
                    }} else {{
                        // Disagree — use PubChem but mark uncertain
                        val = pubVal; srcLabel = 'PubChem (CAS disagrees: ' + casVal + ')';
                        srcUrl = pubUrl; uncertain = true;
                    }}
                }} else if (pubVal != null && pubVal !== '') {{
                    val = pubVal; srcLabel = 'PubChem'; srcUrl = pubUrl;
                    if (!lookupByCAS) uncertain = true;
                }} else if (casVal != null && casVal !== '') {{
                    val = casVal; srcLabel = 'CAS Common Chemistry'; srcUrl = casUrl;
                    if (!lookupByCAS) uncertain = true;
                }}

                if (val != null && val !== '') {{
                    item[field] = val;
                    item._src[field] = {{ label: srcLabel, url: srcUrl, uncertain: uncertain }};
                    filled++;
                }}
            }});
        }} catch(e) {{
            errors++;
        }}

        await _delay(250); // rate limit
    }}

    _inferRunning = false;
    _saveImportedDatasets();

    // Show completion
    var bar2 = document.getElementById('infer-progress');
    if (bar2) {{
        bar2.innerHTML = '<span style="color:#27ae60;font-size:0.82rem">Done! Filled <b>' + filled + '</b> values across ' + queue.length + ' chemicals.' + (errors > 0 ? ' (' + errors + ' lookup errors)' : '') + (_inferCancelled ? ' (Cancelled)' : '') + '</span>';
    }}
    renderDetail();
}}

// --- Cell tooltip system ---
var _tooltipEl = null;
document.addEventListener('mouseover', function(e) {{
    var td = e.target.closest('td[data-src]');
    if (!td) {{ if (_tooltipEl) {{ _tooltipEl.remove(); _tooltipEl = null; }} return; }}
    if (_tooltipEl) return;
    var src = td.getAttribute('data-src');
    var srcUrl = td.getAttribute('data-src-url');
    if (!src) return;
    _tooltipEl = document.createElement('div');
    _tooltipEl.className = 'cell-tooltip';
    var inner = '<b>Source:</b> ' + src;
    if (srcUrl) inner += '<br><b>URL:</b> ' + srcUrl;
    _tooltipEl.innerHTML = inner;
    document.body.appendChild(_tooltipEl);
    var rect = td.getBoundingClientRect();
    _tooltipEl.style.left = Math.min(rect.left, window.innerWidth - 340) + 'px';
    _tooltipEl.style.top = (rect.bottom + 4) + 'px';
}});
document.addEventListener('mouseout', function(e) {{
    var td = e.target.closest('td[data-src]');
    if (td && _tooltipEl) {{ _tooltipEl.remove(); _tooltipEl = null; }}
}});

// --- Claude-powered database search (client-side) ---
function searchDatabases() {{
    var q = document.getElementById('search-input').value.trim();
    if (!q) return;
    var apiKey = _getApiKey();
    if (!apiKey) {{
        var ct = document.getElementById('content');
        ct.innerHTML = '<div class="analysis-card"><h3>API Key Required</h3><p>Enter your Claude API key in the Search Databases panel, then try again.</p></div>';
        return;
    }}
    var ct = document.getElementById('content');
    ct.innerHTML = '<div class="loading">Searching for HSP databases...</div>';

    fetch('https://api.anthropic.com/v1/messages', {{
        method: 'POST',
        headers: {{
            'Content-Type': 'application/json',
            'x-api-key': apiKey,
            'anthropic-version': '2023-06-01',
            'anthropic-dangerous-direct-browser-access': 'true',
        }},
        body: JSON.stringify({{
            model: 'claude-sonnet-4-5-20250929',
            max_tokens: 2048,
            messages: [{{ role: 'user', content: 'Find downloadable Hansen Solubility Parameter (HSP) databases or datasets matching this query: "' + q + '". Return a JSON array of objects with fields: name, url, description, estimated_materials (number), material_types (array of strings like "solvents","polymers"), download_format (e.g. "CSV","Excel","PDF"), has_cas (boolean), has_smiles (boolean), quality ("high","medium","low"). Only include real, verifiable sources. Return ONLY the JSON array, no other text.' }}],
        }})
    }}).then(function(r) {{
        if (!r.ok) return r.json().then(function(err) {{ throw new Error(err.error && err.error.message || 'API error ' + r.status); }});
        return r.json();
    }}).then(function(data) {{
        var text = data.content && data.content[0] && data.content[0].text || '';
        // Extract JSON from response
        var jsonMatch = text.match(/\\[.*\\]/s);
        if (!jsonMatch) {{ ct.innerHTML = '<div class="analysis-card"><h3>No structured results</h3><pre style="white-space:pre-wrap;font-size:0.8rem">' + text + '</pre></div>'; return; }}
        try {{
            var results = JSON.parse(jsonMatch[0]);
            showSearchResults(results);
        }} catch(e) {{
            ct.innerHTML = '<div class="analysis-card"><h3>Parse Error</h3><pre style="white-space:pre-wrap;font-size:0.8rem">' + text + '</pre></div>';
        }}
    }}).catch(function(err) {{
        ct.innerHTML = '<div class="analysis-card"><h3>Search Error</h3><p>' + err.message + '</p></div>';
    }});
}}

function showSearchResults(results) {{
    var ct = document.getElementById('content');
    if (results.length === 0) {{
        ct.innerHTML = '<div class="analysis-card"><h3>No Results</h3><p>No HSP databases found for this query. Try different keywords.</p></div>';
        return;
    }}
    var h = '<h3 style="margin-bottom:12px">Search Results (' + results.length + ')</h3>';
    results.forEach(function(r) {{
        h += '<div class="search-result-card">';
        h += '<h4>' + (r.name || 'Unknown') + '</h4>';
        if (r.url) h += '<div style="font-size:0.78rem;margin-bottom:4px"><a href="' + r.url + '" target="_blank" style="color:#0984e3">' + r.url + '</a></div>';
        if (r.description) h += '<div class="sr-desc">' + r.description + '</div>';
        h += '<div class="sr-tags">';
        if (r.estimated_materials) h += '<span class="sr-tag">' + r.estimated_materials + ' materials</span>';
        if (r.material_types) r.material_types.forEach(function(t) {{ h += '<span class="sr-tag">' + t + '</span>'; }});
        if (r.download_format) h += '<span class="sr-tag">' + r.download_format + '</span>';
        if (r.has_cas === true) h += '<span class="sr-tag good">Has CAS</span>';
        if (r.has_cas === false) h += '<span class="sr-tag warn">No CAS</span>';
        if (r.has_smiles === true) h += '<span class="sr-tag good">Has SMILES</span>';
        if (r.quality) h += '<span class="sr-tag ' + (r.quality === 'high' ? 'good' : r.quality === 'low' ? 'warn' : '') + '">Quality: ' + r.quality + '</span>';
        h += '</div>';
        if (r.url) h += '<button class="import-btn secondary" style="width:auto;padding:4px 14px;font-size:0.78rem" onclick="analyzeSearchResult(\\'' + r.url.replace(/'/g,"\\\\'") + '\\')">Analyze This Source</button>';
        h += '</div>';
    }});
    ct.innerHTML = h;
}}

function analyzeSearchResult(url) {{
    document.getElementById('url-input').value = url;
    analyzeUrl();
}}

function triggerRebuild() {{
    // Export imported datasets as CSV downloads
    var ct = document.getElementById('content');
    var dsKeys = Object.keys(DATASETS);
    if (dsKeys.length === 0) {{
        ct.innerHTML = '<div class="analysis-card"><h3>Nothing to Export</h3><p>Import a dataset first.</p></div>';
        return;
    }}
    var h = '<div class="analysis-card"><h3>Export Datasets</h3>';
    h += '<p>Download CSV files for each imported dataset:</p>';
    dsKeys.forEach(function(k) {{
        var ds = DATASETS[k];
        var nc = (ds.chemicals || []).length;
        var np = (ds.polymers || []).length;
        h += '<div style="margin:6px 0">';
        h += '<b>' + (ds.meta && ds.meta.name || k) + '</b> (' + nc + ' chemicals, ' + np + ' polymers) ';
        if (nc > 0) h += '<button class="import-btn secondary" style="width:auto;padding:2px 10px;font-size:0.75rem" onclick="exportCSV(\\'' + k + '\\',\\'chemicals\\')">Download Chemicals CSV</button> ';
        if (np > 0) h += '<button class="import-btn secondary" style="width:auto;padding:2px 10px;font-size:0.75rem" onclick="exportCSV(\\'' + k + '\\',\\'polymers\\')">Download Polymers CSV</button>';
        h += '</div>';
    }});
    h += '</div>';
    ct.innerHTML = h;
}}

function exportCSV(dsId, type) {{
    var ds = DATASETS[dsId];
    var items = ds[type] || [];
    if (items.length === 0) return;
    var cols = type === 'chemicals'
        ? ['name','cas','dd','dp','dh','mw','bp','cat','smiles','density','conf']
        : ['name','cas','dd','dp','dh','r','type','conf'];
    var csv = cols.join(',') + '\\n';
    items.forEach(function(r) {{
        csv += cols.map(function(c) {{
            var v = r[c] == null ? '' : String(r[c]);
            return v.indexOf(',') > -1 ? '"' + v + '"' : v;
        }}).join(',') + '\\n';
    }});
    var blob = new Blob([csv], {{ type: 'text/csv' }});
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = dsId + '_' + type + '.csv';
    a.click();
}}

// --- Dataset sidebar ---
function buildSidebar() {{
    var sb = document.getElementById('ds-list');
    var dsKeys = Object.keys(DATASETS);
    if (dsKeys.length === 0) {{
        sb.innerHTML = '<div style="padding:10px 0;color:#636e72;font-size:0.82rem">No datasets yet. Use the import tools above.</div>';
        return;
    }}
    document.getElementById('empty-state').style.display = 'none';
    var html = '<div style="font-size:0.75rem;color:#636e72;text-transform:uppercase;letter-spacing:0.5px;margin:8px 0 6px">Datasets</div>';
    dsKeys.forEach(function(k) {{
        var ds = DATASETS[k];
        var m = ds.meta || {{}};
        var active = _activeDsets[k] !== false;
        var sel = _currentDs === k ? ' active' : '';
        var nc = (ds.chemicals || []).length;
        var np = (ds.polymers || []).length;
        html += '<div class="ds-card' + sel + '" onclick="selectDs(\\'' + k + '\\')">';
        html += '<h3>' + (m.name || k) + '</h3>';
        html += '<div class="ds-counts">' + nc + ' chemicals, ' + np + ' polymers</div>';
        html += '<span class="ds-status ' + (active ? 'on' : 'off') + '">' + (active ? 'Active' : 'Inactive') + '</span>';
        html += '</div>';
    }});
    sb.innerHTML = html;
}}

function selectDs(dsId) {{
    _currentDs = dsId;
    _filterText = '';
    _sortCol = null;
    _sortAsc = true;
    buildSidebar();
    renderDetail();
}}

function toggleDs(dsId) {{
    _activeDsets[dsId] = !(_activeDsets[dsId] !== false);
    _saveA(_activeDsets);
    buildSidebar();
    renderDetail();
}}

function renderDetail() {{
    var ct = document.getElementById('content');
    if (!_currentDs) {{
        ct.innerHTML = '<div class="empty-state"><h2>Select a dataset</h2><p>Click a dataset in the sidebar to view its data.</p></div>';
        return;
    }}
    var ds = DATASETS[_currentDs];
    var m = ds.meta || {{}};
    var active = _activeDsets[_currentDs] !== false;
    var nc = (ds.chemicals || []).length;
    var np = (ds.polymers || []).length;

    var html = '<div class="ds-detail-header">';
    html += '<h2>' + (m.name || _currentDs) + '</h2>';
    html += '<div class="ds-meta">';
    if (m.source_url) html += 'Source: <a href="' + m.source_url + '" target="_blank">' + m.source_url + '</a><br>';
    if (m.imported_at) html += 'Imported: ' + m.imported_at.replace('T', ' ').replace(/\\..*/,'') + '<br>';
    html += nc + ' chemicals, ' + np + ' polymers<br>';
    if (m.confidence_tier != null) html += 'Confidence tier: ' + m.confidence_tier + '<br>';
    if (m.quality_notes) html += 'Notes: ' + m.quality_notes + '<br>';
    if (m.fields_available) html += 'Fields: ' + m.fields_available.join(', ') + '<br>';
    html += '</div>';
    html += '<button class="toggle-btn ' + (active ? 'on' : 'off') + '" onclick="toggleDs(\\'' + _currentDs + '\\')">' + (active ? 'Active (click to deactivate)' : 'Inactive (click to activate)') + '</button>';
    html += '<button class="infer-btn" id="infer-btn" onclick="inferMissing(\\'' + _currentDs + '\\')"' + (_inferRunning ? ' disabled' : '') + '>Infer Missing Values</button>';
    html += '</div>';
    html += '<div class="infer-progress" id="infer-progress" style="display:none"></div>';

    html += '<div class="filter-row"><input type="text" id="manage-filter" placeholder="Filter by name or CAS..." oninput="_filterText=this.value;renderDetail()" value="' + (_filterText||'').replace(/"/g,'&quot;') + '"></div>';

    // Determine what data to show
    var items, cols;
    if (nc > 0) {{
        items = ds.chemicals;
        cols = ['name','cas','dd','dp','dh','mw','bp','cat','conf'];
    }} else {{
        items = ds.polymers;
        cols = ['name','cas','dd','dp','dh','r','type','conf'];
    }}

    if (!items || items.length === 0) {{
        html += '<p style="color:#636e72">No data in this dataset.</p>';
        ct.innerHTML = html;
        return;
    }}

    // Filter
    var filtered = items;
    if (_filterText) {{
        var q = _filterText.toLowerCase();
        filtered = filtered.filter(function(r) {{
            return (r.name||'').toLowerCase().indexOf(q) !== -1 || (r.cas||'').indexOf(q) !== -1;
        }});
    }}

    // Sort
    if (_sortCol !== null && cols[_sortCol]) {{
        var sk = cols[_sortCol];
        filtered = filtered.slice().sort(function(a,b) {{
            var va = a[sk]||'', vb = b[sk]||'';
            var na = parseFloat(va), nb = parseFloat(vb);
            if (!isNaN(na) && !isNaN(nb)) return _sortAsc ? na-nb : nb-na;
            return _sortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
        }});
    }}

    var colLabels = {{
        name:'Name', cas:'CAS #', dd:'\\u03b4D', dp:'\\u03b4P', dh:'\\u03b4H',
        mw:'MW', bp:'BP', cat:'Category', conf:'Conf.', r:'R\\u2080', type:'Type',
        smiles:'SMILES', formula:'Formula', density:'Density', mv:'V_m', ghs:'GHS'
    }};

    html += '<table><thead><tr>';
    cols.forEach(function(c, i) {{
        html += '<th onclick="manageSort(' + i + ')">' + (colLabels[c]||c);
        if (_sortCol === i) html += _sortAsc ? ' \\u25B2' : ' \\u25BC';
        html += '</th>';
    }});
    html += '</tr></thead><tbody>';
    var dsSource = (m.name || _currentDs);
    var dsSourceUrl = m.source_url || '';
    var limit = Math.min(filtered.length, 2000);
    for (var i = 0; i < limit; i++) {{
        var r = filtered[i];
        html += '<tr>';
        cols.forEach(function(c) {{
            var v = r[c]; if (v == null) v = '';
            var srcInfo = r._src && r._src[c];
            var srcLabel = srcInfo ? srcInfo.label : dsSource;
            var srcUrl = srcInfo ? (srcInfo.url || '') : dsSourceUrl;
            var isInferred = !!srcInfo;
            var isUncertain = srcInfo && srcInfo.uncertain;
            var cls = isInferred ? ' class="inferred"' : '';
            var attrs = ' data-src="' + srcLabel.replace(/"/g,'&quot;') + '"';
            if (srcUrl) attrs += ' data-src-url="' + srcUrl.replace(/"/g,'&quot;') + '"';
            html += '<td' + cls + attrs + '>' + v;
            if (isUncertain) html += '<span class="q-mark">?</span>';
            html += '</td>';
        }});
        html += '</tr>';
    }}
    if (filtered.length > limit) {{
        html += '<tr><td colspan="' + cols.length + '" style="color:#636e72;text-align:center">... and ' + (filtered.length - limit) + ' more rows</td></tr>';
    }}
    html += '</tbody></table>';
    html += '<div style="margin-top:8px;font-size:0.8rem;color:#636e72">Showing ' + Math.min(limit, filtered.length) + ' of ' + filtered.length + ' entries</div>';

    ct.innerHTML = html;
}}

function manageSort(col) {{
    if (_sortCol === col) _sortAsc = !_sortAsc;
    else {{ _sortCol = col; _sortAsc = true; }}
    renderDetail();
}}

// Mark embedded datasets so we don't save them to localStorage
Object.keys(DATASETS).forEach(function(k) {{ DATASETS[k]._embedded = true; }});
_loadImportedDatasets();

// Init
buildSidebar();
var dsKeys = Object.keys(DATASETS);
if (dsKeys.length > 0) selectDs(dsKeys[0]);
</script>
</body>
</html>"""

manage_output_path = os.path.join(os.path.dirname(__file__), "manage.html")
with open(manage_output_path, "w") as f:
    f.write(manage_html)
print(f"Generated: {manage_output_path}")
ds_total_chems = sum(len(d.get("chemicals", [])) for d in per_dataset_data.values())
ds_total_polys = sum(len(d.get("polymers", [])) for d in per_dataset_data.values())
print(f"Manage page: {len(per_dataset_data)} datasets, {ds_total_chems} chemicals, {ds_total_polys} polymers")
