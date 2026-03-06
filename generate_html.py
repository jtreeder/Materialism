"""Generate a standalone interactive HTML file with the full HSP visualization."""

import os
import sys
import json
import csv

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import numpy as np
from lib.classify import classify_chemical

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
CF_CACHE_PATH = os.path.join(os.path.dirname(__file__), "data", "classyfire_cache.json")

# Load ClassyFire classification cache { CAS: {class, subclass} }
if os.path.exists(CF_CACHE_PATH):
    with open(CF_CACHE_PATH) as _cf:
        _cf_cache = json.load(_cf)
else:
    _cf_cache = {}

def _get_cfclass(cas):
    """Return (cfclass, cflevel) where cflevel is 'subclass' or 'class' or ''."""
    entry = _cf_cache.get(cas)
    if not entry:
        return "", ""
    sub = entry.get("subclass", "").strip()
    cls = entry.get("class", "").strip()
    if sub:
        return sub, "subclass"
    if cls:
        return cls, "class"
    return "", ""

# Load manifest for dataset metadata
if os.path.exists(MANIFEST_PATH):
    with open(MANIFEST_PATH) as _mf:
        _manifest = json.load(_mf)
else:
    _manifest = {"version": 1, "datasets": {}}
DATASETS_META = {k: v for k, v in _manifest.get("datasets", {}).items() if v.get("active", True)}

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
    "hsp_solvents_2": "HSP Solvents 2",
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
            "cat": (lambda _c, _n, _s: classify_chemical(_n, _s) if _c == "other" else _c)(
                row.get("category", "other").strip() or "other",
                chem_name,
                row.get("smiles", "").strip(),
            ),
            "smiles": row.get("smiles", "").strip(),
            "conf": float(conf_val) if conf_val else 0,
            "srcN": int(srcn_val) if srcn_val else 1,
            "src": SOURCE_NAMES.get(src_key, src_key),
            "srcUrl": src_url,
            "mwSrc": mw_src if mw_val else "",
            "bpSrc": bp_src if bp_val else "",
            "common": _is_common_solvent(chem_name, chem_cas),
            "dsId": row.get("dataset_id", "").strip(),
            "cfclass": _get_cfclass(chem_cas)[0],
            "cflevel": _get_cfclass(chem_cas)[1],
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
    "hydrocarbon": "#1f77b4", "aromatic": "#ff7f0e", "halogenated": "#2ca02c",
    "ether": "#d62728", "ketone": "#9467bd", "ester": "#8c564b",
    "alcohol": "#e377c2", "amide": "#7f7f7f", "sulfoxide": "#bcbd22",
    "acid": "#17becf", "nitrile": "#204d20", "glycol ether": "#750069",
    "amine": "#4d0cbe", "terpene": "#9eaeff", "inorganic": "#8e7500",
    "nitro": "#820000", "glycol": "#1c4959", "fluorinated": "#8ec28a",
    "heterocyclic": "#00715d",
    "aldehyde": "#db9e92", "sulfur compound": "#c200aa", "other": "#5d3d00",
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
    # Handbook chapter titles → broad categories
    "Chemical Resistance of Plastics": "Engineering",
    "Chemical Resistance of High Performance and Other Polymers": "Engineering",
    "Chemical Resistance Data - Modern Plastics Encylopedia": "Engineering",
    "Correlations for Some Barrier-Type Polymers": "Engineering",
    "Practical Film Thickness": "Resin",
    "Polyvinylidene Chloride": "Vinyl & Styrene",
    "Alkyd": "Polyester & Alkyd",
    "Polyisobutylene": "Polyolefin",
    # Catch-all chapter titles that contain mixed polymer types
    "Based on Solvent Range Solubility Data - Not too Reliable": "Other",
    "Miscellaneous - Solvent Range": "Other",
    "Miscellaneous": "Other",
    "Special Data": "Other",
    "Special": "Other",
    "Supplemental Chemical Resistance Corrlations": "Other",
    "Polymer Solubility Data from Various Sources": "Other",
}
# Everything not explicitly mapped falls to "Other"
POLYMER_CAT_COLORS = {
    "Polyolefin": "#5d496d", "Vinyl & Styrene": "#6555ff",
    "Acrylic": "#8600be", "Cellulose": "#2dd720",
    "Polyester & Alkyd": "#ba5d08", "Epoxy": "#db92ff",
    "Polyamide & Imide": "#00a6fb", "Rubber & Elastomer": "#496d00",
    "Fluoropolymer": "#aa9a61", "Engineering": "#df35ff",
    "Urethane": "#7d8aba", "Natural & Bio": "#965582",
    "Resin": "#698a59", "Halogenated": "#eb6d5d",
    "Other": "#0035ff",
}

# Assign broad category to each polymer using the type-to-category mapping.
# This groups the many specific types (including handbook chapter titles)
# into a manageable set of broad categories for coloring and legend display.
for p in poly_data:
    raw_type = p["type"] or "Other"
    p["cat"] = POLYMER_TYPE_TO_CAT.get(raw_type, "Other")
    p["color"] = POLYMER_CAT_COLORS.get(p["cat"], "#a9a9a9")

# Pre-compute color field for solvents too
for s in solvents:
    s["color"] = CATEGORY_COLORS.get(s.get("cat", "other"), "#888888")

# Serialize data for JS embedding
solvents_json = json.dumps(solvents)
polymers_json = json.dumps(poly_data)
cat_colors_json = json.dumps(CATEGORY_COLORS)
poly_cat_colors_json = json.dumps(POLYMER_CAT_COLORS)
poly_type_to_cat_json = json.dumps(POLYMER_TYPE_TO_CAT)
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
            overflow: auto; padding: 12px 14px;
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
        .home-table-wrap {{ flex: 1; overflow: auto; min-height: 0; }}

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
        .results-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 8px; }}
        .results-table th {{
            background: #f0f2f5; color: #e94560; padding: 8px 10px;
            text-align: left; font-weight: 600; position: sticky; top: 0; z-index: 1; border-bottom: 2px solid #dfe6e9;
            white-space: nowrap;
        }}
        .results-table td {{ padding: 8px 10px; border-bottom: 1px solid #eee; position: relative; white-space: nowrap; }}
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
        .legend-header.legend-hidden {{
            opacity: 0.35;
            text-decoration: line-through;
        }}
        .legend-header.legend-hidden .legend-marker {{
            opacity: 0.3;
        }}
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
            cursor: pointer; user-select: none;
        }}
        .legend-item:hover {{ background: #f5f6fa; }}
        .legend-swatch {{
            display: inline-block; width: 8px; height: 8px; border-radius: 50%;
            flex-shrink: 0;
        }}
        .legend-swatch.diamond {{
            border-radius: 0; transform: rotate(45deg); width: 7px; height: 7px;
        }}
        .legend-item.legend-hidden {{
            opacity: 0.35;
            text-decoration: line-through;
        }}
        .legend-item.legend-hidden .legend-swatch {{
            opacity: 0.3;
        }}
        .src-popup {{ position: fixed; z-index: 9999; background: #fff; border: 1px solid #dfe6e9; border-radius: 6px; box-shadow: 0 4px 18px rgba(0,0,0,0.14); padding: 8px 12px; font-size: 0.78rem; color: #2d3436; max-width: 280px; pointer-events: auto; }}
        .src-popup-label {{ display: block; font-weight: 600; margin-bottom: 4px; color: #2d3436; }}
        .src-popup-link {{ display: inline-block; color: #e94560; text-decoration: none; font-size: 0.74rem; word-break: break-all; }}
        .src-popup-link:hover {{ text-decoration: underline; }}
        .src-val {{ cursor: pointer; border-bottom: 1px dashed #b2bec3; }}
        .src-val:hover {{ color: #e94560; border-color: #e94560; }}
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
            <div class="plot-container" style="position:relative;">
                <div id="plotly-div" style="width:100%; height:100%;"></div>
                <div id="plot-legend" class="plot-legend"></div>
            </div>
            <p style="color:#636e72; padding:6px 10px; font-size:0.8rem; margin:0;">
                Drag to rotate &middot; Scroll to zoom
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
        const POLYMER_TYPE_TO_CAT = {poly_type_to_cat_json};

        function _normalizeCat(cat) {{
            if (!cat) return 'other';
            if (CAT_COLORS[cat]) return cat;
            var lc = cat.toLowerCase();
            if (CAT_COLORS[lc]) return lc;
            if (lc.indexOf('aromatic') !== -1) return 'aromatic';
            if (lc.indexOf('glycol ether') !== -1) return 'glycol ether';
            if (lc.indexOf('glycol') !== -1 || lc.indexOf('polyol') !== -1) return 'glycol';
            if (lc.indexOf('hydrocarbon') !== -1) return 'hydrocarbon';
            if (lc.indexOf('sulfoxide') !== -1 || lc.indexOf('sulfone') !== -1) return 'sulfoxide';
            if (lc.indexOf('sulfur') !== -1) return 'sulfur compound';
            if (lc.indexOf('fluorin') !== -1) return 'fluorinated';
            if (lc.indexOf('halogen') !== -1 || lc.indexOf('chlorin') !== -1) return 'halogenated';
            if (lc.indexOf('nitrile') !== -1) return 'nitrile';
            if (lc.indexOf('nitro') !== -1) return 'nitro';
            if (lc.indexOf('heterocycl') !== -1) return 'heterocyclic';
            if (lc.indexOf('aldehyde') !== -1) return 'aldehyde';
            if (lc.indexOf('terpene') !== -1) return 'terpene';
            if (lc.indexOf('inorganic') !== -1) return 'inorganic';
            if (lc.indexOf('ketone') !== -1) return 'ketone';
            if (lc.indexOf('ester') !== -1) return 'ester';
            if (lc.indexOf('amide') !== -1) return 'amide';
            if (lc.indexOf('amine') !== -1 || lc.indexOf('amino') !== -1) return 'amine';
            if (lc.indexOf('alcohol') !== -1) return 'alcohol';
            if (lc.indexOf('acid') !== -1) return 'acid';
            if (lc.indexOf('ether') !== -1) return 'ether';
            return 'other';
        }}

        const _LS_DS_KEY = 'materialism_active_datasets';
        function _loadActiveDsets() {{
            try {{ var v = localStorage.getItem(_LS_DS_KEY); return v ? JSON.parse(v) : null; }} catch(e) {{ return null; }}
        }}
        function _getActiveDsets() {{
            var saved = _loadActiveDsets();
            if (saved) return saved;
            var d = {{}};
            Object.keys(DATASETS_META).forEach(function(k) {{ d[k] = true; }});
            return d;
        }}
        function _isDsActive(dsId) {{
            if (!dsId) return true; // entries without dataset_id always shown
            // Visibility on the search page is controlled solely by the active toggle.
            // Deletion in the database management view does not hide embedded data here —
            // user-imported datasets are already excluded by the IIFE before reaching this.
            var active = _getActiveDsets();
            var ids = dsId.split(',');
            for (var i = 0; i < ids.length; i++) {{
                if (active[ids[i]] !== false) return true;
            }}
            return false;
        }}
        var _activeDsets = _getActiveDsets();

        // Each solvent/polymer has a pre-baked .color field set at generation time.
        // These helper functions get the color for a category name (for legends).

        function _onDatasetsChanged() {{
            _activeDsets = _getActiveDsets();
            if (plotDiv && plotDiv.data) _updatePlotForCommonFilter();
            _buildLegend();
            buildHomeTable();
        }}

        // --- Load imported datasets from manage page ---
        (function() {{
            try {{
                var raw = localStorage.getItem('materialism_imported_datasets');
                if (!raw) return;
                var imported = JSON.parse(raw);
                var _delRaw = localStorage.getItem('materialism_deleted_datasets');
                var _deletedIds = _delRaw ? JSON.parse(_delRaw) : [];
                Object.keys(imported).forEach(function(dsId) {{
                    if (_activeDsets[dsId] === false) return; // explicitly toggled off
                    if (_deletedIds.indexOf(dsId) !== -1) return; // deleted via UI — never re-add
                    if (DATASETS_META[dsId]) return; // already in embedded data — skip to prevent duplication
                    var ds = imported[dsId];
                    var meta = ds.meta || {{}};
                    var srcLabel = meta.name || dsId;
                    var srcUrl = meta.source_url || '';
                    (ds.chemicals || []).forEach(function(c) {{
                        var cat = _normalizeCat(c.cat);
                        var entry = {{
                            name: c.name || '', cas: c.cas || '', smiles: c.smiles || '',
                            formula: c.formula || '', dd: c.dd || '', dp: c.dp || '', dh: c.dh || '',
                            mw: c.mw || '', bp: c.bp || '', density: c.density || '',
                            mv: c.mv || '', cat: cat, ghs: c.ghs || '',
                            color: CAT_COLORS[cat] || '#888',
                            conf: c.conf || '', srcN: 1, src: srcLabel, srcUrl: srcUrl,
                            dsId: dsId, _imported: true
                        }};
                        SOLVENTS.push(entry);
                        if (!_solventMap.has(entry.name)) _solventMap.set(entry.name, entry);
                    }});
                    (ds.polymers || []).forEach(function(p) {{
                        var cat = p.cat || POLY_TYPE_TO_CAT[p.type] || 'Other';
                        var entry = {{
                            name: p.name || '', cas: p.cas || '', dd: p.dd || '', dp: p.dp || '', dh: p.dh || '',
                            r: p.r || '', type: p.type || '', cat: cat, conf: p.conf || '',
                            color: POLY_CAT_COLORS[cat] || '#a9a9a9',
                            srcN: 1, src: srcLabel, srcUrl: srcUrl,
                            dsId: dsId, _imported: true
                        }};
                        POLYMERS.push(entry);
                        if (!_polymerMap.has(entry.name)) _polymerMap.set(entry.name, entry);
                    }});
                    if (!DATASETS_META[dsId]) {{
                        DATASETS_META[dsId] = {{ name: srcLabel, source_url: srcUrl }};
                    }}
                }});
            }} catch(e) {{}}
        }})();

        // Filter arrays by active datasets
        function _dsFilterSolvents() {{
            return SOLVENTS.filter(function(s) {{ return _isDsActive(s.dsId); }});
        }}
        function _dsFilterPolymers() {{
            return POLYMERS.filter(function(p) {{ return _isDsActive(p.dsId); }});
        }}


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
                    else if (field === 'cat') {{ arr[idx].cat = val; arr[idx].color = CAT_COLORS[val] || '#888'; }}
                    else if (field === 'r' && type === 'polymers') arr[idx].r = parseFloat(val) || arr[idx].r;
                    else if (field === 'type' && type === 'polymers') {{ arr[idx].type = val; var _pc = POLYMER_TYPE_TO_CAT[val] || 'Other'; arr[idx].cat = _pc; arr[idx].color = POLY_CAT_COLORS[_pc] || '#a9a9a9'; }}
                    else if (field === 'src') arr[idx].src = val;
                }}
            }} catch(e) {{}}
        }})();

        // ===================== COLUMN WIDTH LOCK =====================
        var columnWidthsLocked = false;
        // Default widths for each table context
        var DEFAULT_WIDTHS = {{
            solvents: ['24%','10%','52px','52px','52px','56px','56px','10%'],
            polymers: ['26%','12%','52px','52px','52px','56px','10%'],
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
            _rerunActiveSearch();
            // Update legend counts to reflect filter
            _buildLegend();
        }}

        function _rerunActiveSearch() {{
            if (_isSearchActive && lastSearchQuery) {{
                var parsed = parseQuery(lastSearchQuery);
                var result = executeSearch(parsed);
                var html = renderResultsHTML(result);
                showResults(html);
                if (!result.error) updatePlotWithResults(result);
            }}
        }}

        // Pre-compute full coordinate arrays (used for initial plot creation).
        // All filtering (dataset, simpleMode, hidden categories) is done
        // dynamically in _updatePlotForCommonFilter via coordinate nulling.
        var _allSolX = SOLVENTS.map(function(s) {{ return s.dd; }});
        var _allSolY = SOLVENTS.map(function(s) {{ return s.dp; }});
        var _allSolZ = SOLVENTS.map(function(s) {{ return s.dh; }});
        // Color palette for data sources — assigned deterministically by first appearance
        var _srcColorPalette = ['#3498db','#e74c3c','#2ecc71','#f39c12','#9b59b6','#1abc9c','#e67e22','#34495e','#e91e8c','#00bcd4'];
        var _srcColorMap = {{}};
        var _srcColorIdx = 0;
        function _getSrcColor(src) {{
            var key = src || 'Base Database';
            if (!_srcColorMap[key]) {{ _srcColorMap[key] = _srcColorPalette[_srcColorIdx++ % _srcColorPalette.length]; }}
            return _srcColorMap[key];
        }}
        // Group polymers by category for per-category traces (ensures reliable
        // scatter3d coloring — per-point color arrays can fail with non-default symbols).
        var _polyCatOrder = [];
        var _polyCatData = {{}};
        POLYMERS.forEach(function(p, i) {{
            var cat = p.cat || 'Other';
            if (!_polyCatData[cat]) {{ _polyCatData[cat] = []; _polyCatOrder.push(cat); }}
            _polyCatData[cat].push({{ idx: i, p: p }});
        }});
        var _polyTraceStart = 1; // polymer traces start right after solvents trace (index 0)
        var _polyTraceCount = _polyCatOrder.length;

        // Hidden-category state for legend toggle
        var _hiddenSolCats = {{}};
        var _hiddenPolyCats = {{}};

        function _hasHiddenCats() {{
            for (var k in _hiddenSolCats) return true;
            for (var k in _hiddenPolyCats) return true;
            return false;
        }}

        function toggleCategoryVisibility(el) {{
            var cat = el.getAttribute('data-cat');
            var type = el.getAttribute('data-type');
            var set = (type === 'solvent') ? _hiddenSolCats : _hiddenPolyCats;
            if (set[cat]) {{
                delete set[cat];
                el.classList.remove('legend-hidden');
            }} else {{
                set[cat] = true;
                el.classList.add('legend-hidden');
            }}
            _syncGroupHeader(el.closest('.legend-group'));
            _updatePlotForCommonFilter();
            buildHomeTable();
            _rerunActiveSearch();
        }}

        function toggleGroupVisibility(header) {{
            var group = header.closest('.legend-group');
            var items = group.querySelectorAll('.legend-item');
            var type = items[0] ? items[0].getAttribute('data-type') : null;
            if (!type) return;
            var set = (type === 'solvent') ? _hiddenSolCats : _hiddenPolyCats;
            var anyVisible = false;
            items.forEach(function(it) {{
                if (!set[it.getAttribute('data-cat')]) anyVisible = true;
            }});
            items.forEach(function(it) {{
                var cat = it.getAttribute('data-cat');
                if (anyVisible) {{
                    set[cat] = true;
                    it.classList.add('legend-hidden');
                }} else {{
                    delete set[cat];
                    it.classList.remove('legend-hidden');
                }}
            }});
            header.classList.toggle('legend-hidden', anyVisible);
            _updatePlotForCommonFilter();
            buildHomeTable();
            _rerunActiveSearch();
        }}

        function _syncGroupHeader(group) {{
            if (!group) return;
            var header = group.querySelector('.legend-header');
            var items = group.querySelectorAll('.legend-item');
            var type = items[0] ? items[0].getAttribute('data-type') : null;
            if (!type) return;
            var set = (type === 'solvent') ? _hiddenSolCats : _hiddenPolyCats;
            var allHidden = true;
            items.forEach(function(it) {{
                if (!set[it.getAttribute('data-cat')]) allHidden = false;
            }});
            header.classList.toggle('legend-hidden', allHidden);
        }}

        function _updatePlotForCommonFilter() {{
            if (!plotDiv || !plotDiv.data) return;
            // Use dimmed styling when a search has dimmed the base traces
            var sSize = _plotDimmed ? 2 : 5;
            var pSize = _plotDimmed ? 3 : 7;
            var sOpacity = _plotDimmed ? 0.1 : 0.85;
            var pOpacity = _plotDimmed ? 0.12 : 0.95;
            var hInfo = _plotDimmed ? 'skip' : 'none';

            // Build filtered coordinate and color arrays for all traces,
            // then apply via a single batched Plotly.restyle call.
            // (Plotly.react with mutated data can interfere with scatter3d
            //  WebGL diamond marker rendering; restyle is more reliable.)
            var indices = [0];
            var allX = [], allY = [], allZ = [];
            var allSize = [], allColor = [], allOpacity = [], allHInfo = [];

            // Solvent trace (trace 0)
            var sx = [], sy = [], sz = [], sc = [];
            SOLVENTS.forEach(function(s, i) {{
                var visible = true;
                if (!_isDsActive(s.dsId)) visible = false;
                else if (simpleMode && !s.common) visible = false;
                else if (_hiddenSolCats[s.cat || 'other']) visible = false;
                sx.push(visible ? s.dd : null);
                sy.push(visible ? s.dp : null);
                sz.push(visible ? s.dh : null);
                sc.push(visible ? (s.color || '#888') : 'rgba(0,0,0,0)');
            }});
            allX.push(sx); allY.push(sy); allZ.push(sz);
            allSize.push(sSize);
            allColor.push(_plotDimmed ? '#999' : sc);
            allOpacity.push(sOpacity);
            allHInfo.push(hInfo);

            // Polymer category traces
            for (var ti = 0; ti < _polyTraceCount; ti++) {{
                var cat = _polyCatOrder[ti];
                var items = _polyCatData[cat];
                var catHidden = !!_hiddenPolyCats[cat];
                var trColor = POLY_CAT_COLORS[cat] || '#a9a9a9';
                var px = [], py = [], pz = [];
                for (var j = 0; j < items.length; j++) {{
                    var p = items[j].p;
                    var visible = true;
                    if (!_isDsActive(p.dsId)) visible = false;
                    else if (simpleMode && !p.common) visible = false;
                    else if (catHidden) visible = false;
                    px.push(visible ? p.dd : null);
                    py.push(visible ? p.dp : null);
                    pz.push(visible ? p.dh : null);
                }}
                indices.push(_polyTraceStart + ti);
                allX.push(px); allY.push(py); allZ.push(pz);
                allSize.push(pSize);
                allColor.push(_plotDimmed ? '#665500' : trColor);
                allOpacity.push(pOpacity);
                allHInfo.push(hInfo);
            }}

            Plotly.restyle(plotDiv, {{
                'x': allX, 'y': allY, 'z': allZ,
                'marker.size': allSize, 'marker.color': allColor,
                'marker.opacity': allOpacity, 'hoverinfo': allHInfo,
            }}, indices);
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

        function computeResultColors(validResults, r0) {{
            if (validResults.length === 0) {{ _resultColorMeta = null; return []; }}
            const useScore = validResults[0].ra == null && validResults[0].combinedScore != null;
            const distances = validResults.map(r => {{
                if (r.ra != null) return r.ra;
                if (r.combinedScore != null) return r.combinedScore;
                return 0;
            }});
            const minD = Math.min(...distances);
            const maxD = Math.max(...distances);
            const range = maxD - minD;
            _resultColorMeta = {{ min: minD, max: maxD, r0: r0 || null, metric: useScore ? 'Score' : 'Ra' }};
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
                var N = SOLVENTS.length, scored = [];
                var tDDs = targets.map(function(t) {{ return t.dd; }});
                var tDPs = targets.map(function(t) {{ return t.dp; }});
                var tDHs = targets.map(function(t) {{ return t.dh; }});
                var tRs = targets.map(function(t) {{ return (t.r && t.r > 0) ? t.r : 0; }});
                var tGood = targets.map(function(t) {{ return t.requirement === 'good' ? 1 : -1; }});
                for (var si = 0; si < N; si++) {{
                    if (!_isDsActive(SOLVENTS[si].dsId)) continue;
                    if (simpleMode && !_sCommon[si]) continue;
                    if (_hiddenSolCats[SOLVENTS[si].cat || 'other']) continue;
                    var cs = 0, dd0 = _sDD[si], dp0 = _sDP[si], dh0 = _sDH[si];
                    for (var ti = 0; ti < targets.length; ti++) {{
                        var ddd = dd0 - tDDs[ti], ddp = dp0 - tDPs[ti], ddh = dh0 - tDHs[ti];
                        cs += tGood[ti] * Math.sqrt(4 * ddd * ddd + ddp * ddp + ddh * ddh);
                    }}
                    scored.push({{ _i: si, combinedScore: cs }});
                }}
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
                var scored = [];
                for (var si = 0; si < N; si++) {{
                    if (!_isDsActive(SOLVENTS[si].dsId)) continue;
                    if (simpleMode && !_sCommon[si]) continue;
                    if (_hiddenSolCats[SOLVENTS[si].cat || 'other']) continue;
                    var ddd = _sDD[si] - tDD, ddp = _sDP[si] - tDP, ddh = _sDH[si] - tDH;
                    scored.push({{ _i: si, ra: Math.sqrt(4 * ddd * ddd + ddp * ddp + ddh * ddh) }});
                }}
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
                    if (!_isDsActive(SOLVENTS[si].dsId)) continue;
                    if (simpleMode && !_sCommon[si]) continue;
                    if (_hiddenSolCats[SOLVENTS[si].cat || 'other']) continue;
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
                var scored = POLYMERS.filter(function(p) {{ return p.name !== target.name && _isDsActive(p.dsId) && !_hiddenPolyCats[p.cat || 'Other']; }});
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
                var scored = POLYMERS.filter(function(p) {{ return p.r && p.r > 0 && _isDsActive(p.dsId) && !_hiddenPolyCats[p.cat || 'Other']; }});
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
            else if (parentIntent === 'similar_solvents') {{ h.push(th('Ra (MPa<sup>\u00bd</sup>)')); }}
            else {{ h.push(th('Ra (MPa<sup>\u00bd</sup>)'), th('R&#8320; (MPa<sup>\u00bd</sup>)')); }}
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
                        h.push('<td></td>');
                    }} else if (showRed) {{
                        h.push('<td></td><td style="color:#636e72">R&#8320;=', (t.r || 'N/A'), '</td>');
                    }} else if (parentIntent === 'similar_solvents') {{
                        h.push('<td></td>');
                    }} else {{
                        h.push('<td></td><td>', (t.r || ''), '</td>');
                    }}
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
                else {{ h.push('<td>', (r.ra != null ? r.ra.toFixed(2) : ''), '</td>'); if (showRed) {{ const red = r.red; let cls = 'red-bad'; if (red !== null) {{ if (red < 1) cls = 'red-good'; else if (red < 1.2) cls = 'red-boundary'; }} h.push('<td class="', cls, '">', (red !== null ? red.toFixed(2) : 'N/A'), '</td>'); }} else if (parentIntent === 'similar_solvents') {{ }} else {{ h.push('<td>', (r.r || ''), '</td>'); }} }}
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
            fullTraces = [
                {{
                    type: 'scatter3d', mode: 'markers',
                    name: 'Solvents',
                    x: _allSolX, y: _allSolY, z: _allSolZ,
                    hoverinfo: 'none',
                    marker: {{ size: 5, color: SOLVENTS.map(function(s){{ return s.color || '#888'; }}), opacity: 0.85 }},
                    showlegend: false,
                }},
            ];
            // One trace per polymer category — single color per trace is
            // the only reliable way to color scatter3d diamond markers.
            _polyCatOrder.forEach(function(cat) {{
                var items = _polyCatData[cat];
                var color = POLY_CAT_COLORS[cat] || '#a9a9a9';
                fullTraces.push({{
                    type: 'scatter3d', mode: 'markers',
                    name: cat,
                    x: items.map(function(e) {{ return e.p.dd; }}),
                    y: items.map(function(e) {{ return e.p.dp; }}),
                    z: items.map(function(e) {{ return e.p.dh; }}),
                    hoverinfo: 'none',
                    marker: {{ size: 7, color: color, symbol: 'diamond', opacity: 0.95 }},
                    showlegend: false,
                    _polyCat: cat,
                    _polyIndices: items.map(function(e) {{ return e.idx; }}),
                }});
            }});
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
            // Render the plot. Only apply dataset/filter updates on initial load
            // if there are actually saved filters — calling restyle immediately
            // after newPlot on scatter3d diamond markers can reset colors.
            Plotly.newPlot(plotDiv, fullTraces, makeLayout(), {{ responsive: true }}).then(function() {{
                var needsFilter = simpleMode || _hasHiddenCats();
                if (!needsFilter) {{
                    var saved = _loadActiveDsets();
                    if (saved) {{ for (var k in saved) {{ if (saved[k] === false) {{ needsFilter = true; break; }} }} }}
                }}
                if (needsFilter) _updatePlotForCommonFilter();
                _buildLegend();
            }});
        }}

        function _buildLegend() {{
            var el = document.getElementById('plot-legend');
            if (!el) return;

            // Results mode: replace category legend with a heat-bar
            if (_resultTraceCount > 0 && _resultColorMeta) {{
                var m = _resultColorMeta;
                var hasRed = m.r0 && m.r0 > 0 && m.metric === 'Ra';
                var minLabel, maxLabel;
                if (hasRed) {{
                    minLabel = 'RED&nbsp;' + (m.min / m.r0).toFixed(2);
                    maxLabel = 'RED&nbsp;' + (m.max / m.r0).toFixed(2);
                }} else if (m.metric === 'Ra') {{
                    minLabel = 'Ra&nbsp;' + m.min.toFixed(1);
                    maxLabel = 'Ra&nbsp;' + m.max.toFixed(1);
                }} else {{
                    minLabel = 'Best';
                    maxLabel = 'Worst';
                }}

                // Position of RED=1 tick on the bar (0–1 fraction)
                var tickPct = null;
                if (hasRed) {{
                    var t1 = (m.r0 - m.min) / (m.max - m.min);
                    if (t1 > 0.02 && t1 < 0.98) tickPct = (t1 * 100).toFixed(1);
                }}

                var h = '<div style="padding:8px 10px;min-width:170px">';
                h += '<div style="font-size:0.7rem;font-weight:700;color:#636e72;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px">Match Quality</div>';
                // Gradient bar
                h += '<div style="position:relative;height:14px;border-radius:3px;background:linear-gradient(to right,#00cc66,#cccc00 50%,#ef553b);margin-bottom:2px">';
                if (tickPct !== null) {{
                    h += '<div style="position:absolute;top:-4px;bottom:-4px;left:' + tickPct + '%;width:2px;background:#2d3436;border-radius:1px"></div>';
                }}
                h += '</div>';
                // Value labels
                h += '<div style="display:flex;justify-content:space-between;font-size:0.67rem;color:#636e72;font-family:monospace;margin-bottom:4px">';
                h += '<span>' + minLabel + '</span><span>' + maxLabel + '</span></div>';
                // RED=1 annotation
                if (tickPct !== null) {{
                    h += '<div style="font-size:0.67rem;color:#2d3436;padding-top:3px;border-top:1px solid #eee;margin-bottom:4px">';
                    h += '<span style="display:inline-block;width:10px;height:2px;background:#2d3436;vertical-align:middle;margin-right:3px;border-radius:1px"></span>';
                    h += 'RED\u00a0=\u00a01 (compatibility limit)</div>';
                }}
                // Good / poor labels
                h += '<div style="display:flex;justify-content:space-between;font-size:0.7rem;padding-top:4px;border-top:1px solid #eee">';
                h += '<span style="color:#00aa55;font-weight:600">&#9679; Good match</span>';
                h += '<span style="color:#ef553b;font-weight:600">Poor &#9679;</span>';
                h += '</div>';
                h += '</div>';
                el.innerHTML = h;
                return;
            }}

            // Collect solvent category counts — only active datasets, respecting simpleMode
            var sCats = {{}};
            var activeSolCount = 0;
            SOLVENTS.forEach(function(s) {{
                if (!_isDsActive(s.dsId)) return;
                if (simpleMode && !s.common) return;
                activeSolCount++;
                var cat = s.cat || 'other';
                sCats[cat] = (sCats[cat] || 0) + 1;
            }});
            // Collect polymer category counts — only active datasets, respecting simpleMode
            var pCats = {{}};
            var activePolyCount = 0;
            POLYMERS.forEach(function(p) {{
                if (!_isDsActive(p.dsId)) return;
                if (simpleMode && !p.common) return;
                activePolyCount++;
                var cat = p.cat || 'Other';
                pCats[cat] = (pCats[cat] || 0) + 1;
            }});
            // Order categories by their defined palette order, then alphabetically
            var sCatOrder = Object.keys(CAT_COLORS).filter(function(c) {{ return sCats[c]; }});
            Object.keys(sCats).forEach(function(c) {{ if (sCatOrder.indexOf(c) === -1) sCatOrder.push(c); }});
            var pCatOrder = Object.keys(POLY_CAT_COLORS).filter(function(c) {{ return pCats[c]; }});
            Object.keys(pCats).forEach(function(c) {{ if (pCatOrder.indexOf(c) === -1) pCatOrder.push(c); }});
            var h = '';
            // Solvents group
            var allSolHidden = sCatOrder.length > 0 && sCatOrder.every(function(c) {{ return !!_hiddenSolCats[c]; }});
            h += '<div class="legend-group">';
            h += '<div class="legend-header' + (allSolHidden ? ' legend-hidden' : '') + '" onclick="toggleGroupVisibility(this)">';
            h += '<span class="legend-arrow open" onclick="event.stopPropagation();toggleLegendGroup(this.parentNode)">&#9654;</span>';
            h += '<span class="legend-marker" style="background:#888"></span>';
            h += 'Solvents (' + activeSolCount + ')';
            h += '</div>';
            h += '<div class="legend-items open">';
            sCatOrder.forEach(function(cat) {{
                var color = CAT_COLORS[cat] || '#888';
                var hiddenCls = _hiddenSolCats[cat] ? ' legend-hidden' : '';
                var label = cat.charAt(0).toUpperCase() + cat.slice(1);
                h += '<div class="legend-item' + hiddenCls + '" data-cat="' + cat.replace(/"/g,'&quot;') + '" data-type="solvent" onclick="toggleCategoryVisibility(this)"><span class="legend-swatch" style="background:' + color + '"></span>' + label + ' (' + sCats[cat] + ')</div>';
            }});
            h += '</div></div>';
            // Polymers group
            var allPolyHidden = pCatOrder.length > 0 && pCatOrder.every(function(c) {{ return !!_hiddenPolyCats[c]; }});
            h += '<div class="legend-group">';
            h += '<div class="legend-header' + (allPolyHidden ? ' legend-hidden' : '') + '" onclick="toggleGroupVisibility(this)">';
            h += '<span class="legend-arrow open" onclick="event.stopPropagation();toggleLegendGroup(this.parentNode)">&#9654;</span>';
            h += '<span class="legend-marker diamond" style="background:#a9a9a9"></span>';
            h += 'Polymers (' + activePolyCount + ')';
            h += '</div>';
            h += '<div class="legend-items open">';
            pCatOrder.forEach(function(cat) {{
                var color = POLY_CAT_COLORS[cat] || '#a9a9a9';
                var hiddenCls = _hiddenPolyCats[cat] ? ' legend-hidden' : '';
                h += '<div class="legend-item' + hiddenCls + '" data-cat="' + cat.replace(/"/g,'&quot;') + '" data-type="polymer" onclick="toggleCategoryVisibility(this)"><span class="legend-swatch diamond" style="background:' + color + '"></span>' + cat + ' (' + pCats[cat] + ')</div>';
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

        // Track result traces layered on top of base traces (solvents + N polymer categories + highlight)
        var _baseTraceCount = 0;
        var _resultTraceCount = 0;
        var _plotDimmed = false;
        var _resultColorMeta = null;  // {{min, max, r0, metric}} for heat-bar legend

        function _dimBaseTraces() {{
            if (_plotDimmed) return;
            _plotDimmed = true;
            _updatePlotForCommonFilter();
        }}

        function _restoreBaseTraces() {{
            if (!_plotDimmed) return;
            _plotDimmed = false;
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
            const resultColors = computeResultColors(valid, isMulti ? null : (target && target.r));
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
                    _names: valid.map(r => r.name),
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
                        _names: [tgt.name],
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
                    _names: valid.map(r => r.name),
                }});
                newTraces.push({{ type: 'scatter3d', mode: 'markers+text', name: '★ Target: ' + target.name,
                    x: [target.dd], y: [target.dp], z: [target.dh], text: ['★ ' + target.name],
                    textposition: 'top center', textfont: {{ size: 13, color: '#e94560' }},
                    hovertemplate: '<b>★ ' + target.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}' + (target.r ? '<br>R₀=' + target.r : '') + '<extra></extra>',
                    marker: {{ size: 16, color: '#e94560', symbol: isReverse ? 'circle' : 'diamond', opacity: 1, line: {{ color: '#2d3436', width: 2 }} }},
                    _names: [target.name],
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
                    _names: valid.map(r => r.name),
                }});
                const tsym = (parentIntent === 'similar_polymers') ? 'diamond' : 'circle';
                newTraces.push({{ type: 'scatter3d', mode: 'markers+text', name: '★ Target: ' + target.name,
                    x: [target.dd], y: [target.dp], z: [target.dh], text: ['★ ' + target.name],
                    textposition: 'top center', textfont: {{ size: 13, color: '#e94560' }},
                    hovertemplate: '<b>★ ' + target.name + '</b><br>δD=%{{x:.1f}}, δP=%{{y:.1f}}, δH=%{{z:.1f}}<extra></extra>',
                    marker: {{ size: 16, color: '#e94560', symbol: tsym, opacity: 1, line: {{ color: '#2d3436', width: 2 }} }},
                    _names: [target.name],
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
            _buildLegend();
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
            _resultColorMeta = null;
            _buildLegend();
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
            var bgColor = mat.color || '#888';
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
                'Conf.': ''
            }};
            function thWithTip(label, idx) {{
                var tip = colTips[label] || '';
                return '<th onclick="sortResultsTable(this.closest(\\x27table\\x27),' + idx + ')" style="cursor:pointer"' + (tip ? ' title="' + tip + '"' : '') + '>' + label + '</th>';
            }}

            // Remove any existing colgroup (auto-sizing: let browser determine column widths)
            var existingCg = tbl.querySelector('colgroup');
            if (existingCg) existingCg.remove();

            if (homeTab === 'solvents') {{
                // Name, CAS #, δD, δP, δH, MW, BP, Class
                headerHtml = '<tr>';
                ['Name','CAS #','&delta;D (MPa<sup>\u00bd</sup>)','&delta;P (MPa<sup>\u00bd</sup>)','&delta;H (MPa<sup>\u00bd</sup>)','MW (g/mol)','BP (&deg;C)','Class'].forEach(function(label, i) {{
                    headerHtml += thWithTip(label, i);
                }});
                headerHtml += '</tr>';
                var filtered = _dsFilterSolvents();
                if (simpleMode) {{
                    filtered = filtered.filter(function(s) {{ return s.common; }});
                }}
                if (_hasHiddenCats()) {{
                    filtered = filtered.filter(function(s) {{ return !_hiddenSolCats[s.cat || 'other']; }});
                }}
                if (homeFilterText) {{
                    var q = homeFilterText.toLowerCase();
                    filtered = filtered.filter(function(s) {{ return s.name.toLowerCase().indexOf(q) !== -1 || (s.cas && s.cas.indexOf(q) !== -1) || (s.src && s.src.toLowerCase().indexOf(q) !== -1); }});
                }}
                document.getElementById('tab-solvents').textContent = 'Solvents (' + filtered.length + ')';
                rowsHtml = '';
                for (var i = 0; i < filtered.length; i++) {{
                    var s = filtered[i];
                    var catColor = s.color || CAT_COLORS[s.cat] || '#888';
                    function lnk(val, url, lbl) {{ if (val == null || val === '') return ''; var v = (typeof val === 'number') ? val.toFixed(1) : val; if (!url) return String(v); var sl = (lbl || 'Source').replace(/'/g,'\\x27'); var su = url.replace(/'/g,'\\x27'); return '<span class="src-val" onclick="event.stopPropagation();_showSrcPop(this,\\x27' + sl + '\\x27,\\x27' + su + '\\x27)">' + v + '</span>'; }}
                    rowsHtml += '<tr data-name="' + s.name.replace(/"/g, '&quot;') + '" onclick="highlightInPlot(\\x27' + encodeURIComponent(s.name) + '\\x27)" onmouseenter="hoverInPlot(\\x27' + encodeURIComponent(s.name) + '\\x27)" onmouseleave="unhoverInPlot()" style="cursor:pointer;border-left:3px solid ' + catColor + '">';
                    rowsHtml += '<td><span class="hoverable-name" onmouseenter="showStructure(event,\\x27' + encodeURIComponent(s.name) + '\\x27)" onmouseleave="hideStructure()">' + s.name + '</span></td>';
                    rowsHtml += '<td>' + (s.cas || '') + '</td>';
                    rowsHtml += '<td>' + lnk(s.dd, s.srcUrl, s.src) + '</td>';
                    rowsHtml += '<td>' + lnk(s.dp, s.srcUrl, s.src) + '</td>';
                    rowsHtml += '<td>' + lnk(s.dh, s.srcUrl, s.src) + '</td>';
                    rowsHtml += '<td>' + lnk(s.mw, s.mwSrc, s.src) + '</td>';
                    rowsHtml += '<td>' + (s.bp != null ? lnk(s.bp, s.bpSrc, s.src) : '') + '</td>';
                    var _cfNote = s.cfclass ? (s.cflevel === 'class' ? '<sup title="ClassyFire class used \u2014 no subclass available" style="color:#b2bec3;font-size:0.65rem;cursor:help">\u2020</sup>' : '') : '';
                    rowsHtml += '<td style="color:#636e72;font-size:0.82rem">' + (s.cfclass || '') + _cfNote + '</td>';
                    rowsHtml += '</tr>';
                }}
            }} else {{
                // Name, CAS, δD, δP, δH, R₀, Type
                headerHtml = '<tr>';
                ['Name','CAS #','&delta;D (MPa<sup>\u00bd</sup>)','&delta;P (MPa<sup>\u00bd</sup>)','&delta;H (MPa<sup>\u00bd</sup>)','R&#8320; (MPa<sup>\u00bd</sup>)'].forEach(function(label, i) {{
                    headerHtml += thWithTip(label, i);
                }});
                headerHtml += '</tr>';
                var filtered = _dsFilterPolymers();
                if (simpleMode) {{
                    filtered = filtered.filter(function(p) {{ return p.common; }});
                }}
                if (_hasHiddenCats()) {{
                    filtered = filtered.filter(function(p) {{ return !_hiddenPolyCats[p.cat || 'Other']; }});
                }}
                if (homeFilterText) {{
                    var q = homeFilterText.toLowerCase();
                    filtered = filtered.filter(function(p) {{ return p.name.toLowerCase().indexOf(q) !== -1 || (p.cas && p.cas.indexOf(q) !== -1) || (p.src && p.src.toLowerCase().indexOf(q) !== -1); }});
                }}
                document.getElementById('tab-polymers').textContent = 'Polymers (' + filtered.length + ')';
                rowsHtml = '';
                for (var i = 0; i < filtered.length; i++) {{
                    var p = filtered[i];
                    function lnk(val, url, lbl) {{ if (val == null || val === '') return ''; var v = (typeof val === 'number') ? val.toFixed(1) : val; if (!url) return String(v); var sl = (lbl || 'Source').replace(/'/g,'\\x27'); var su = url.replace(/'/g,'\\x27'); return '<span class="src-val" onclick="event.stopPropagation();_showSrcPop(this,\\x27' + sl + '\\x27,\\x27' + su + '\\x27)">' + v + '</span>'; }}
                    var catColor = p.color || POLY_CAT_COLORS[p.cat] || '#a9a9a9';
                    rowsHtml += '<tr data-name="' + p.name.replace(/"/g, '&quot;') + '" onclick="highlightInPlot(\\x27' + encodeURIComponent(p.name) + '\\x27)" onmouseenter="hoverInPlot(\\x27' + encodeURIComponent(p.name) + '\\x27)" onmouseleave="unhoverInPlot()" style="cursor:pointer;border-left:3px solid ' + catColor + '">';
                    rowsHtml += '<td><span class="hoverable-name">' + p.name + '</span></td>';
                    rowsHtml += '<td>' + (p.cas || '') + '</td>';
                    rowsHtml += '<td>' + lnk(p.dd, p.srcUrl, p.src) + '</td>';
                    rowsHtml += '<td>' + lnk(p.dp, p.srcUrl, p.src) + '</td>';
                    rowsHtml += '<td>' + lnk(p.dh, p.srcUrl, p.src) + '</td>';
                    rowsHtml += '<td>' + (p.r || '') + '</td>';
                    rowsHtml += '</tr>';
                }}
            }}

            thead.innerHTML = headerHtml;
            tbody.innerHTML = rowsHtml;

            // Update the inactive tab count too — filter by active datasets
            if (homeTab === 'solvents') {{
                var pf = _dsFilterPolymers();
                if (simpleMode) pf = pf.filter(function(p) {{ return p.common; }});
                if (_hasHiddenCats()) pf = pf.filter(function(p) {{ return !_hiddenPolyCats[p.cat || 'Other']; }});
                if (homeFilterText) {{ var q = homeFilterText.toLowerCase(); pf = pf.filter(function(p) {{ return p.name.toLowerCase().indexOf(q) !== -1 || (p.cas && p.cas.indexOf(q) !== -1) || (p.src && p.src.toLowerCase().indexOf(q) !== -1); }}); }}
                document.getElementById('tab-polymers').textContent = 'Polymers (' + pf.length + ')';
            }} else {{
                var sf = _dsFilterSolvents();
                if (simpleMode) sf = sf.filter(function(s) {{ return s.common; }});
                if (_hasHiddenCats()) sf = sf.filter(function(s) {{ return !_hiddenSolCats[s.cat || 'other']; }});
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

        // ---- Citation popup (shared with database page behavior) ----
        var _srcPop2 = null, _srcPopRef2 = null;
        function _showSrcPop(el, label, url) {{
            if (_srcPop2 && _srcPopRef2 === el) {{
                if (url) window.open(url, '_blank', 'noopener');
                _closeSrcPop2(); return;
            }}
            _closeSrcPop2();
            _srcPopRef2 = el;
            el.classList.add('active');
            if (!_srcPop2) {{ _srcPop2 = document.createElement('div'); _srcPop2.className = 'src-popup'; document.body.appendChild(_srcPop2); }}
            _srcPop2.innerHTML = '<span class="src-popup-label">' + label.replace(/</g,'&lt;') + '</span>' + (url ? '<a class="src-popup-link" href="' + url + '" target="_blank" rel="noopener">Open source \u2197</a>' : '');
            _srcPop2.style.display = 'block';
            var rect = el.getBoundingClientRect();
            var popW = _srcPop2.offsetWidth, popH = _srcPop2.offsetHeight;
            var left = rect.left, top = rect.bottom + 6;
            if (top + popH > window.innerHeight - 8) top = rect.top - popH - 6;
            if (left + popW > window.innerWidth - 8) left = window.innerWidth - popW - 8;
            if (left < 4) left = 4;
            _srcPop2.style.left = left + 'px'; _srcPop2.style.top = top + 'px';
        }}
        function _closeSrcPop2() {{
            if (_srcPopRef2) {{ _srcPopRef2.classList.remove('active'); _srcPopRef2 = null; }}
            if (_srcPop2) _srcPop2.style.display = 'none';
        }}
        document.addEventListener('click', function(e) {{
            if (_srcPop2 && _srcPop2.style.display !== 'none' && !_srcPop2.contains(e.target) && !e.target.closest('.src-val')) _closeSrcPop2();
        }});

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
        // Listen for dataset changes from the manage page (localStorage sync)
        window.addEventListener('storage', function(e) {{
            if (e.key === _LS_DS_KEY || e.key === 'materialism_imported_datasets') {{
                _onDatasetsChanged();
            }}
        }});

        document.addEventListener('DOMContentLoaded', function() {{
            loadLockedWidths();
            buildFullPlot();
            buildHomeTable();
            // All tooltips use scene annotations for one consistent style
            function _nameFromPoint(pt) {{
                if (pt.curveNumber === 0 && SOLVENTS[pt.pointNumber]) return SOLVENTS[pt.pointNumber].name;
                if (pt.curveNumber >= _polyTraceStart && pt.curveNumber < _polyTraceStart + _polyTraceCount) {{
                    var trace = plotDiv.data[pt.curveNumber];
                    if (trace && trace._polyIndices) {{
                        var polyIdx = trace._polyIndices[pt.pointNumber];
                        if (polyIdx != null && POLYMERS[polyIdx]) return POLYMERS[polyIdx].name;
                    }}
                }}
                // Results-state traces: check _names attached when building result traces
                if (pt.curveNumber >= _baseTraceCount) {{
                    var rtrace = plotDiv.data[pt.curveNumber];
                    if (rtrace && rtrace._names && rtrace._names[pt.pointNumber] != null) {{
                        return rtrace._names[pt.pointNumber];
                    }}
                }}
                return '';
            }}
            plotDiv.on('plotly_hover', function(data) {{
                if (_pinnedName || _tableHover) return;
                try {{
                    var name = _nameFromPoint(data.points[0]);
                    if (name) showAnnotation(name);
                }} catch(e) {{}}
            }});
            plotDiv.on('plotly_unhover', function() {{
                if (!_pinnedName && !_tableHover) hideAnnotation();
            }});
            plotDiv.on('plotly_click', function(data) {{
                try {{
                    if (!data || !data.points || !data.points.length) return;
                    var name = _nameFromPoint(data.points[0]);
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
        _db_cat_raw = row.get("category", "other").strip() or "other"
        _db_name = row["name"].strip()
        _db_smiles = row.get("smiles", "").strip()
        _db_cat = classify_chemical(_db_name, _db_smiles) if _db_cat_raw == "other" else _db_cat_raw
        db_solvents.append({
            "name": _db_name,
            "cas": row.get("cas_number", "").strip(),
            "smiles": _db_smiles,
            "formula": row.get("molecular_formula", "").strip(),
            "dd": dd, "dp": dp, "dh": dh,
            "mw": row.get("molecular_weight", "").strip(),
            "bp": row.get("boiling_point", "").strip(),
            "density": row.get("density", "").strip(),
            "mv": row.get("molar_volume", "").strip(),
            "cat": _db_cat,
            "color": CATEGORY_COLORS.get(_db_cat, "#888888"),
            "ghs": row.get("ghs_hazard", "").strip(),
            "conf": row.get("confidence", "").strip(),
            "srcN": int(row.get("source_count", "1").strip() or "1"),
            "src": SOURCE_NAMES.get(src_key, src_key),
            "srcUrl": row.get("source_url", "").strip(),
            "dsId": row.get("dataset_id", "").strip(),
            "cfclass": _get_cfclass(row.get("cas_number", "").strip())[0],
            "cflevel": _get_cfclass(row.get("cas_number", "").strip())[1],
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
        _db_poly_type = row.get("type", "").strip()
        _db_poly_cat = POLYMER_TYPE_TO_CAT.get(_db_poly_type, "Other")
        db_polymers.append({
            "name": row["name"].strip(),
            "cas": row.get("cas_number", "").strip(),
            "dd": dd, "dp": dp, "dh": dh,
            "r": row.get("radius", "").strip(),
            "type": _db_poly_type,
            "cat": _db_poly_cat,
            "color": POLYMER_CAT_COLORS.get(_db_poly_cat, "#a9a9a9"),
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

# ===================== LOAD PER-DATASET DATA =====================
DATASETS_DIR = os.path.join(os.path.dirname(__file__), "data", "datasets")
per_dataset_data = {}
for ds_id, ds_meta in DATASETS_META.items():
    if not ds_meta.get("active", True):
        continue
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
                    "cat": (lambda _c, _n, _s: classify_chemical(_n, _s) if _c == "other" else _c)(
                        row.get("category", "other").strip() or "other",
                        row.get("name", "").strip(),
                        row.get("smiles", "").strip(),
                    ),
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
    per_dataset_data[ds_id] = {"chemicals": chems, "polymers": polys, "meta": ds_meta, "_embedded": True}

per_dataset_json = json.dumps(per_dataset_data)

# Generate color legend rows for database sidebar
_legend_solvent_rows = ''
for _lname, _lcolor in CATEGORY_COLORS.items():
    _legend_solvent_rows += (
        '<div style="display:flex;align-items:center;gap:6px;padding:2px 0">'
        '<span style="display:inline-block;width:14px;height:14px;background:' + _lcolor + ';border-radius:2px;flex-shrink:0"></span>'
        '<span style="flex:1;font-size:0.75rem;color:#2d3436">' + _lname + '</span>'
        '<code style="font-size:0.68rem;color:' + _lcolor + ';padding:1px 4px;font-family:monospace">' + _lcolor + '</code>'
        '</div>'
    )
_legend_polymer_rows = ''
for _lname, _lcolor in POLYMER_CAT_COLORS.items():
    _legend_polymer_rows += (
        '<div style="display:flex;align-items:center;gap:6px;padding:2px 0">'
        '<span style="display:inline-block;width:14px;height:14px;background:' + _lcolor + ';border-radius:2px;flex-shrink:0"></span>'
        '<span style="flex:1;font-size:0.75rem;color:#2d3436">' + _lname + '</span>'
        '<code style="font-size:0.68rem;color:' + _lcolor + ';padding:1px 4px;font-family:monospace">' + _lcolor + '</code>'
        '</div>'
    )

def generate_import_html():
    # Load from _write_import_html.py (separate file for the full pipeline HTML)
    _import_mod = {}
    with open(os.path.join(os.path.dirname(__file__), "_write_import_html.py")) as _f:
        exec(_f.read(), _import_mod)
    return _import_mod.get("IMPORT_HTML", "")

# ===================== DATABASE PAGE: QUICK CSV IMPORT STRINGS =====================
# Written as regular strings (not f-strings) so JS object-literal braces need no doubling.

_db_csv_import_css = """
/* Quick CSV Import */
.csv-import-btn {
    display: block; width: 100%; padding: 8px 0; margin-bottom: 8px;
    border: 1px solid #0984e3; border-radius: 4px; background: #f0f7ff;
    color: #0984e3; font-size: 0.82rem; cursor: pointer; text-align: center;
    transition: all 0.2s; font-family: inherit;
}
.csv-import-btn:hover { background: #0984e3; color: #fff; }
.col-map-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.col-map-table th {
    background: #f0f2f5; padding: 6px 10px; font-weight: 600;
    color: #636e72; text-align: left; border: 1px solid #e0e4e8;
}
.col-map-table td { padding: 5px 8px; border: 1px solid #eee; }
.col-map-table select {
    padding: 3px 6px; border: 1px solid #dfe6e9; border-radius: 3px;
    font-size: 0.8rem; font-family: inherit; background: #fff;
}
.col-map-table select.mapped { border-color: #27ae60; background: #f0faf4; }
.csv-drop-zone {
    border: 2px dashed #dfe6e9; border-radius: 8px; padding: 40px 20px;
    text-align: center; cursor: pointer; transition: all 0.2s;
}
.csv-drop-zone.drag-over { border-color: #e94560; background: #fff5f7; }
"""

_db_csv_import_js = r"""
// ===================== QUICK CSV IMPORT =====================
var _csvImportState = {rows: null, headers: null, mapping: {}, dsType: 'chemicals', dsName: '', fileName: ''};

var _CSV_FIELD_DEFS = [
    {id: '_ignore', label: '(ignore)'},
    {id: 'name',    label: 'Name',              required: true},
    {id: 'cas',     label: 'CAS Number'},
    {id: 'dd',      label: '\u03b4D \u2014 Dispersion', required: true},
    {id: 'dp',      label: '\u03b4P \u2014 Polar',      required: true},
    {id: 'dh',      label: '\u03b4H \u2014 H-Bond',     required: true},
    {id: 'r',       label: 'Radius'},
    {id: 'mw',      label: 'Mol. Weight'},
    {id: 'bp',      label: 'Boiling Point'},
    {id: 'density', label: 'Density'},
    {id: 'smiles',  label: 'SMILES'},
    {id: 'cat',     label: 'Category'},
    {id: 'type',    label: 'Type'},
    {id: 'conf',    label: 'Confidence'},
];
// Fast lookup: which values are predefined field IDs (not passthrough)
var _PREDEFINED_FIELD_ID_SET = {};
_CSV_FIELD_DEFS.forEach(function(fd) { _PREDEFINED_FIELD_ID_SET[fd.id] = true; });

// Patterns ordered from most-specific to least-specific to avoid false matches.
var _CSV_PATTERNS = {
    name:    [/^name$/i, /^chemical[\s_]*name/i, /^compound[\s_]*name/i, /^compound$/i,
              /^solvent$/i, /^material$/i, /^substance$/i, /^polymer$/i,
              /^product$/i, /^molecule$/i, /^name[\s_-]/i, /[\s_-]name$/i],
    cas:     [/^cas$/i, /^cas[\s_-]?no\.?$/i, /^cas[\s_-]?number$/i,
              /^cas[\s_-]?rn$/i, /^casno$/i],
    dd:      [/^d[\s_]?d$/i, /^delta[\s_-]?d$/i, /^\u03b4[\s_]?d$/i,
              /^dd$/i, /^disp(ersion)?$/i, /^hd$/i, /^fd$/i, /^vd$/i,
              /^d[\s_-]disp/i, /^ddisp/i, /^dispersive$/i],
    dp:      [/^d[\s_]?p$/i, /^delta[\s_-]?p$/i, /^\u03b4[\s_]?p$/i,
              /^dp$/i, /^polar(ity)?$/i, /^hp$/i, /^fp$/i, /^vp$/i,
              /^d[\s_-]pol/i, /^dpol/i],
    dh:      [/^d[\s_]?h$/i, /^delta[\s_-]?h$/i, /^\u03b4[\s_]?h$/i,
              /^dh$/i, /^h[\s_-]?bond(ing)?$/i, /^hbond$/i, /^hh$/i,
              /^fh$/i, /^vh$/i, /^d[\s_-]hb/i, /^dhb/i, /^hydrogen[\s_-]?bond/i],
    r:       [/^r$/i, /^radius$/i, /^r0$/i, /^interaction[\s_-]?radius/i, /^ra$/i],
    mw:      [/^mw$/i, /^mol[\s_-]?wt$/i, /^molecular[\s_-]?weight$/i, /^mass$/i],
    bp:      [/^bp$/i, /^boiling[\s_-]?point$/i, /^b\.p\.$/i, /^tbp$/i],
    density: [/^density$/i, /^rho$/i, /^\u03c1$/i, /^dens$/i],
    smiles:  [/^smiles$/i, /^canonical[\s_-]?smiles$/i, /^smi$/i, /^structure$/i],
    cat:     [/^cat(egory)?$/i, /^class(ification)?$/i, /^group$/i],
    type:    [/^type$/i, /^polymer[\s_-]?type$/i, /^kind$/i],
    conf:    [/^conf(idence)?$/i, /^quality$/i, /^score$/i],
};

function _detectCsvCols(headers) {
    var mapping = {};
    var used = {};
    var fields = Object.keys(_CSV_PATTERNS);
    for (var fi = 0; fi < fields.length; fi++) {
        var field = fields[fi];
        var pats = _CSV_PATTERNS[field];
        for (var pi = 0; pi < pats.length; pi++) {
            var found = null;
            for (var hi = 0; hi < headers.length; hi++) {
                var h = headers[hi];
                if (!used[h] && pats[pi].test(h)) { found = h; break; }
            }
            if (found) { mapping[field] = found; used[found] = true; break; }
        }
    }
    // Default unrecognized columns to passthrough: keep original name as the field key
    for (var hi2 = 0; hi2 < headers.length; hi2++) {
        var h2 = headers[hi2];
        if (!used[h2]) mapping[h2] = h2;
    }
    return mapping;
}

function _parseCsvImportLine(line, delim) {
    var result = [], cur = '', inQ = false;
    for (var i = 0; i < line.length; i++) {
        var c = line[i];
        if (inQ) {
            if (c === '"' && line[i+1] === '"') { cur += '"'; i++; }
            else if (c === '"') { inQ = false; }
            else { cur += c; }
        } else {
            if (c === '"') { inQ = true; }
            else if (c === delim) { result.push(cur); cur = ''; }
            else { cur += c; }
        }
    }
    result.push(cur);
    return result;
}

function _parseCsvImportText(text) {
    var lines = text.split(/\r?\n/).filter(function(l) { return l.trim(); });
    if (!lines.length) return null;
    var tabCount = (lines[0].match(/\t/g) || []).length;
    var commaCount = (lines[0].match(/,/g) || []).length;
    var delim = tabCount > commaCount ? '\t' : ',';
    var headers = _parseCsvImportLine(lines[0], delim).map(function(h) { return h.trim(); });
    var rows = [];
    for (var i = 1; i < lines.length; i++) {
        if (!lines[i].trim()) continue;
        var vals = _parseCsvImportLine(lines[i], delim);
        var row = {};
        headers.forEach(function(h, idx) { row[h] = vals[idx] !== undefined ? vals[idx].trim() : ''; });
        rows.push(row);
    }
    return {headers: headers, rows: rows};
}

function showCsvImportView() {
    _viewMode = '_csv_import';
    buildSidebar();
    _renderCsvImportPanel();
}

function _onCsvDrop(e) {
    e.preventDefault();
    var file = e.dataTransfer.files[0];
    if (file) _loadCsvFile(file);
}

function _onCsvFileSelect(e) {
    var file = e.target.files[0];
    if (file) _loadCsvFile(file);
}

function _loadCsvFile(file) {
    _csvImportState.fileName = file.name;
    if (!_csvImportState.dsName) {
        _csvImportState.dsName = file.name.replace(/\.[^.]+$/, '');
    }
    var reader = new FileReader();
    reader.onload = function(ev) {
        var parsed = _parseCsvImportText(ev.target.result);
        if (!parsed || !parsed.rows.length) {
            alert('Could not parse file or file is empty.');
            return;
        }
        _csvImportState.headers = parsed.headers;
        _csvImportState.rows = parsed.rows;
        _csvImportState.mapping = _detectCsvCols(parsed.headers);
        _renderCsvImportPanel();
    };
    reader.readAsText(file);
}

function _updateColMapping(csvCol, fieldId) {
    // Unassign this csvCol from any existing field
    Object.keys(_csvImportState.mapping).forEach(function(f) {
        if (_csvImportState.mapping[f] === csvCol) delete _csvImportState.mapping[f];
    });
    // Also evict whatever column previously held this fieldId
    if (fieldId !== '_ignore' && _csvImportState.mapping[fieldId] && _csvImportState.mapping[fieldId] !== csvCol) {
        delete _csvImportState.mapping[fieldId];
    }
    if (fieldId !== '_ignore') _csvImportState.mapping[fieldId] = csvCol;
    _renderCsvImportPanel();
}

function _getMissingRequired() {
    var req = ['name', 'dd', 'dp', 'dh'];
    return req.filter(function(f) { return !_csvImportState.mapping[f]; });
}

function _renderColumnMappingTable() {
    var headers = _csvImportState.headers;
    var mapping = _csvImportState.mapping;
    // Reverse: csvCol -> fieldId
    var revMap = {};
    Object.keys(mapping).forEach(function(f) { if (mapping[f]) revMap[mapping[f]] = f; });
    var usedFields = {};
    Object.keys(mapping).forEach(function(f) { if (mapping[f]) usedFields[f] = true; });

    var h = '<div style="margin-bottom:16px">';
    h += '<div style="font-size:0.85rem;font-weight:600;color:#2d3436;margin-bottom:8px">Column Mapping</div>';
    h += '<table class="col-map-table"><thead><tr><th>CSV Column</th><th>Maps to</th><th>Sample Values</th></tr></thead><tbody>';
    headers.forEach(function(col) {
        var curField = revMap[col] || '_ignore';
        var sample = _csvImportState.rows.slice(0, 3).map(function(r) { return r[col] || ''; }).join(', ');
        if (sample.length > 50) sample = sample.substring(0, 50) + '\u2026';
        h += '<tr>';
        h += '<td style="font-family:monospace;font-size:0.8rem">' + col + '</td>';
        h += '<td><select class="' + (curField !== '_ignore' ? 'mapped' : '') + '"'
           + ' onchange="_updateColMapping(\'' + col.replace(/'/g, "\\'") + '\',this.value)">';
        _CSV_FIELD_DEFS.forEach(function(fd) {
            var inUse = fd.id !== '_ignore' && usedFields[fd.id] && revMap[col] !== fd.id;
            h += '<option value="' + fd.id + '"'
               + (fd.id === curField ? ' selected' : '') + '>'
               + fd.label + (fd.required ? ' \u2731' : '') + (inUse ? ' \u2014 reassign' : '') + '</option>';
        });
        // Per-column passthrough option: "col_name (new)" — keep as custom field
        // Only selectable when curField equals the column name itself (passthrough)
        var isPassthrough = curField === col && !_PREDEFINED_FIELD_ID_SET[col];
        h += '<option value="' + col + '"' + (isPassthrough ? ' selected' : '') + '>'
           + col + ' (new)</option>';
        h += '</select></td>';
        h += '<td style="color:#636e72;font-size:0.78rem">' + sample + '</td>';
        h += '</tr>';
    });
    h += '</tbody></table>';
    h += '<div style="font-size:0.72rem;color:#b2bec3;margin-top:4px">\u2731 required</div></div>';
    return h;
}

function _renderCsvPreview() {
    var headers = _csvImportState.headers;
    var rows = _csvImportState.rows.slice(0, 5);
    var revMap = {};
    Object.keys(_csvImportState.mapping).forEach(function(f) {
        if (_csvImportState.mapping[f]) revMap[_csvImportState.mapping[f]] = f;
    });
    var h = '<div style="margin-bottom:8px">';
    h += '<div style="font-size:0.85rem;font-weight:600;color:#2d3436;margin-bottom:8px">Preview ('
       + _csvImportState.rows.length + ' rows total)</div>';
    h += '<div style="overflow-x:auto"><table style="font-size:0.75rem;border-collapse:collapse"><thead><tr>';
    headers.forEach(function(col) {
        var field = revMap[col];
        var mapped = field && field !== '_ignore';
        h += '<th style="background:' + (mapped ? '#f0faf4' : '#f8f9fa')
           + ';padding:5px 8px;border:1px solid #e0e4e8;white-space:nowrap;font-weight:600;color:'
           + (mapped ? '#27ae60' : '#636e72') + '">' + col
           + (mapped ? '<br><span style="font-size:0.68rem;font-weight:400">\u2192 ' + field + '</span>' : '')
           + '</th>';
    });
    h += '</tr></thead><tbody>';
    rows.forEach(function(row) {
        h += '<tr>';
        headers.forEach(function(col) {
            var mapped = revMap[col] && revMap[col] !== '_ignore';
            h += '<td style="padding:4px 8px;border:1px solid #eee;'
               + (mapped ? 'background:#f9fffe' : '') + '">' + (row[col] || '') + '</td>';
        });
        h += '</tr>';
    });
    h += '</tbody></table></div></div>';
    return h;
}

function _executeQuickImport() {
    var nameEl = document.getElementById('csv-ds-name');
    var dsName = (nameEl ? nameEl.value : '') || _csvImportState.dsName || 'Imported Dataset';
    var dsType = _csvImportState.dsType;
    var mapping = _csvImportState.mapping;
    var rows = _csvImportState.rows;
    var dsId = 'import_' + Date.now();
    var chemicals = [], polymers = [];
    rows.forEach(function(raw) {
        function g(f) { var col = mapping[f]; return col ? (raw[col] || '') : ''; }
        if (!g('name') && !g('dd')) return; // skip blank rows
        var entry;
        if (dsType === 'polymers') {
            entry = {
                name: g('name'), cas: g('cas'),
                dd: g('dd'), dp: g('dp'), dh: g('dh'),
                r: g('r'), type: g('type') || g('cat'), conf: g('conf')
            };
            polymers.push(entry);
        } else {
            entry = {
                name: g('name'), cas: g('cas'),
                dd: g('dd'), dp: g('dp'), dh: g('dh'),
                mw: g('mw'), bp: g('bp'), density: g('density'),
                smiles: g('smiles'), cat: g('cat'), conf: g('conf')
            };
            chemicals.push(entry);
        }
        // Passthrough fields: any mapping key that is not a predefined field ID
        Object.keys(mapping).forEach(function(fieldId) {
            if (!_PREDEFINED_FIELD_ID_SET[fieldId]) {
                var col = mapping[fieldId];
                if (col) entry[fieldId] = raw[col] || '';
            }
        });
    });
    DATASETS[dsId] = {
        chemicals: dsType === 'chemicals' ? chemicals : [],
        polymers:  dsType === 'polymers'  ? polymers  : [],
        meta: {
            name: dsName,
            imported_at: new Date().toISOString(),
            source: _csvImportState.fileName || 'CSV import'
        },
        _imported: true
    };
    _activeDsets[dsId] = true;
    _saveActiveDsets(_activeDsets);
    _saveImportedDatasets();
    _csvImportState = {rows: null, headers: null, mapping: {}, dsType: 'chemicals', dsName: '', fileName: ''};
    _viewMode = dsId;
    buildSidebar();
    renderContent();
}

function _renderCsvImportPanel() {
    var ct = document.getElementById('content');
    var h = '<div class="detail-content"><div class="analysis-card" style="max-width:900px">';
    h += '<h3>Quick CSV Import</h3>';
    h += '<p style="font-size:0.82rem;color:#636e72;margin-bottom:16px">Import any CSV or TSV &mdash; column names are auto-detected and remapped to standard HSP fields. The search page is unaffected.</p>';
    // Name + type row
    h += '<div style="display:flex;gap:12px;margin-bottom:16px;align-items:flex-end">';
    h += '<div style="flex:1"><label style="font-size:0.8rem;font-weight:600;color:#636e72;display:block;margin-bottom:4px">Dataset Name</label>';
    h += '<input id="csv-ds-name" type="text" placeholder="My Dataset"'
       + ' style="width:100%;padding:7px 10px;border:1px solid #dfe6e9;border-radius:4px;font-size:0.87rem"'
       + ' value="' + (_csvImportState.dsName || '').replace(/"/g, '&quot;') + '"'
       + ' oninput="_csvImportState.dsName=this.value"></div>';
    h += '<div><label style="font-size:0.8rem;font-weight:600;color:#636e72;display:block;margin-bottom:4px">Data Type</label>';
    h += '<select style="padding:7px 10px;border:1px solid #dfe6e9;border-radius:4px;font-size:0.87rem;background:#fff"'
       + ' onchange="_csvImportState.dsType=this.value;_renderCsvImportPanel()">';
    h += '<option value="chemicals"' + (_csvImportState.dsType === 'chemicals' ? ' selected' : '') + '>Chemicals / Solvents</option>';
    h += '<option value="polymers"'  + (_csvImportState.dsType === 'polymers'  ? ' selected' : '') + '>Polymers</option>';
    h += '</select></div></div>';
    if (!_csvImportState.rows) {
        // Drop zone
        h += '<div class="csv-drop-zone"'
           + ' ondragover="event.preventDefault();this.classList.add(\'drag-over\')"'
           + ' ondragleave="this.classList.remove(\'drag-over\')"'
           + ' ondrop="_onCsvDrop(event);this.classList.remove(\'drag-over\')">';
        h += '<div style="font-size:2rem;margin-bottom:10px">&#128196;</div>';
        h += '<div style="font-size:0.95rem;font-weight:600;color:#2d3436;margin-bottom:6px">Drop CSV or TSV file here</div>';
        h += '<div style="font-size:0.78rem;color:#636e72;margin-bottom:14px">Any column names &bull; Comma or tab delimited</div>';
        h += '<input type="file" id="csv-file-input" accept=".csv,.tsv,.txt" style="display:none" onchange="_onCsvFileSelect(event)">';
        h += '<button class="import-btn secondary" style="width:auto;padding:6px 18px"'
           + ' onclick="document.getElementById(\'csv-file-input\').click()">Browse File</button>';
        h += '</div>';
    } else {
        h += '<div style="font-size:0.78rem;color:#636e72;margin-bottom:12px">File: <b>'
           + _csvImportState.fileName + '</b> \u2022 '
           + _csvImportState.rows.length + ' rows \u2022 '
           + _csvImportState.headers.length + ' columns</div>';
        h += _renderColumnMappingTable();
        h += _renderCsvPreview();
        var missing = _getMissingRequired();
        var btnStyle = 'width:auto;padding:6px 20px' + (missing.length ? ';opacity:0.5;cursor:not-allowed' : '');
        h += '<div style="margin-top:16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap">';
        h += '<button class="import-btn" style="' + btnStyle + '"'
           + (missing.length ? '' : ' onclick="_executeQuickImport()"')
           + '>Import ' + _csvImportState.rows.length + ' Rows</button>';
        h += '<button class="import-btn secondary" style="width:auto;padding:6px 20px"'
           + ' onclick="_csvImportState.rows=null;_csvImportState.headers=null;_csvImportState.mapping={};_renderCsvImportPanel()">'
           + '\u2190 Change File</button>';
        if (missing.length) {
            h += '<span style="color:#e74c3c;font-size:0.82rem">Required: ' + missing.join(', ') + '</span>';
        }
        h += '</div>';
    }
    h += '</div></div>';
    ct.innerHTML = h;
}
"""

database_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Materialism — Database</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: #f5f6fa; color: #2d3436; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; display: flex; flex-direction: column; height: 100vh; }}
.header {{ background: #fff; padding: 15px 30px; display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #dfe6e9; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
.header h1 {{ font-size: 1.5rem; color: #e94560; }}
.header h1 a {{ color: #e94560; text-decoration: none; }}
.header .nav-links {{ color: #636e72; font-size: 0.9rem; display: flex; align-items: center; gap: 12px; }}
.header .nav-links a {{ color: #636e72; text-decoration: none; border-bottom: 1px dotted #b2bec3; cursor: pointer; }}
.main {{ display: flex; flex: 1; overflow: hidden; }}
.sidebar {{ width: 280px; flex-shrink: 0; position: relative; z-index: 2; background: #fff; border-right: 1px solid #dfe6e9; overflow-y: auto; padding: 12px; }}
.active-db-btn {{
    width: 100%; padding: 10px 12px; border: 2px solid #e94560; border-radius: 6px;
    background: #fff; color: #e94560; font-size: 0.9rem; font-weight: 600;
    cursor: pointer; transition: all 0.2s; margin-bottom: 12px; text-align: left;
}}
.active-db-btn:hover {{ background: #fff5f7; }}
.active-db-btn.selected {{ background: #e94560; color: #fff; }}
.active-db-btn .btn-counts {{ font-size: 0.72rem; font-weight: 400; margin-top: 2px; opacity: 0.8; }}
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
.content {{ flex: 1; min-width: 0; overflow: hidden; padding: 0; position: relative; z-index: 0; display: flex; flex-direction: column; }}
.toolbar {{ background: #fff; padding: 10px 20px; display: flex; align-items: center; gap: 16px; border-bottom: 1px solid #dfe6e9; }}
.toolbar input {{ padding: 8px 12px; border: 1px solid #dfe6e9; border-radius: 4px; font-size: 0.85rem; width: 220px; }}
.toolbar input:focus {{ outline: none; border-color: #e94560; }}
.db-tabs {{ display: flex; gap: 0; }}
.db-tab {{ padding: 8px 18px; cursor: pointer; border: none; background: transparent; color: #636e72; font-size: 0.85rem; transition: all 0.2s; }}
.db-tab:hover {{ color: #2d3436; background: #f5f6fa; }}
.db-tab.active {{ color: #e94560; border-bottom: 2px solid #e94560; background: #fff; }}
.lock-btn {{
    display: inline-flex; align-items: center; gap: 5px; padding: 3px 10px;
    border: 1px solid #dfe6e9; border-radius: 4px; font-size: 0.75rem;
    cursor: pointer; background: #fff; transition: all 0.2s; color: #636e72;
}}
.lock-btn:hover {{ background: #f5f6fa; }}
.lock-btn.unlocked {{ border-color: #e94560; color: #e94560; }}
.lock-btn svg {{ width: 14px; height: 14px; fill: currentColor; }}
.table-wrap {{ overflow: auto; flex: 1; min-height: 0; }}
table {{ width: max-content; min-width: 100%; border-collapse: collapse; font-size: 0.8rem; }}
/* Dataset detail styles */
.ds-detail-header {{ margin-bottom: 16px; }}
.ds-title-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }}
.ds-detail-header h2 {{ font-size: 1.2rem; color: #2d3436; margin: 0; flex: 1; min-width: 0; }}
.ds-detail-header .ds-meta {{ font-size: 0.82rem; color: #636e72; line-height: 1.6; }}
.ds-detail-header .ds-meta a {{ color: #0984e3; }}
.ds-detail-header .toggle-btn {{
    display: inline-block; padding: 4px 12px; border: 1px solid #dfe6e9; border-radius: 4px;
    font-size: 0.8rem; cursor: pointer; background: #fff; margin-top: 6px; transition: all 0.2s;
}}
.ds-detail-header .toggle-btn:hover {{ background: #f5f6fa; }}
.ds-detail-header .toggle-btn.on {{ border-color: #27ae60; color: #27ae60; }}
.ds-detail-header .toggle-btn.off {{ border-color: #e74c3c; color: #e74c3c; }}
.delete-ds-btn {{
    display: inline-flex; align-items: center; gap: 5px; padding: 3px 10px;
    border: 1px solid #dfe6e9; border-radius: 4px; font-size: 0.75rem;
    cursor: pointer; background: #fff; transition: all 0.2s; color: #636e72; margin-left: auto;
}}
.delete-ds-btn:hover {{ background: #ffeaea; border-color: #e74c3c; color: #e74c3c; }}
.delete-ds-btn.confirm {{
    background: #e74c3c; border-color: #c0392b; color: #fff; animation: pulse-delete 0.6s ease;
}}
.delete-ds-btn.confirm:hover {{ background: #c0392b; }}
@keyframes pulse-delete {{ 0% {{ transform: scale(1); }} 50% {{ transform: scale(1.05); }} 100% {{ transform: scale(1); }} }}
td[contenteditable="true"] {{
    background: #fffef5; outline: none; cursor: text;
    box-shadow: inset 0 0 0 1px #f0d060;
}}
td[contenteditable="true"]:focus {{
    box-shadow: inset 0 0 0 2px #e94560;
    background: #fff;
}}
.detail-content {{ padding: 20px; flex: 1; min-height: 0; overflow-y: auto; }}
.filter-row {{ margin-bottom: 10px; }}
.filter-row input {{ padding: 6px 10px; border: 1px solid #dfe6e9; border-radius: 4px; font-size: 0.82rem; width: 250px; }}
.filter-row input:focus {{ outline: none; border-color: #e94560; }}
.empty-state {{
    text-align: center; padding: 60px 20px; color: #636e72;
}}
.empty-state h2 {{ font-size: 1.4rem; color: #2d3436; margin-bottom: 12px; }}
.empty-state p {{ font-size: 0.95rem; line-height: 1.6; max-width: 500px; margin: 0 auto; }}
.empty-state code {{ background: #f0f2f5; padding: 2px 6px; border-radius: 3px; font-size: 0.85rem; }}
/* Import link button */
.import-link-btn {{
    display: block; width: 100%; padding: 8px 0; margin-bottom: 12px; border: 1px dashed #e94560;
    border-radius: 4px; background: #fff5f7; color: #e94560; font-size: 0.82rem; cursor: pointer;
    text-align: center; text-decoration: none; transition: all 0.2s;
}}
.import-link-btn:hover {{ background: #e94560; color: #fff; }}
/* Export/utility buttons */
.import-btn {{
    width: 100%; padding: 6px 0; border: none; border-radius: 4px; font-size: 0.8rem;
    cursor: pointer; transition: all 0.2s; background: #e94560; color: #fff;
}}
.import-btn:hover {{ background: #d63851; }}
.import-btn.secondary {{ background: #fff; color: #636e72; border: 1px solid #dfe6e9; }}
.import-btn.secondary:hover {{ background: #f5f6fa; }}
.analysis-card {{
    background: #fff; border: 1px solid #dfe6e9; border-radius: 8px; padding: 20px; margin-bottom: 16px;
}}
.analysis-card h3 {{ font-size: 1rem; color: #2d3436; margin-bottom: 12px; }}
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
.infer-step-log {{ margin-top: 8px; max-height: 120px; overflow-y: auto; font-size: 0.75rem; line-height: 1.6; }}
.infer-step {{ color: #636e72; padding: 1px 0; }}
.infer-step .step-icon {{ display: inline-block; width: 16px; text-align: center; }}
.infer-step.active {{ color: #0984e3; font-weight: 500; }}
.infer-step.active .step-icon {{ animation: pulse 1s infinite; }}
.infer-step.ok {{ color: #27ae60; }}
.infer-step.warn {{ color: #b2bec3; }}
@keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} }}
.api-key-row {{ display: flex; gap: 4px; margin-bottom: 6px; }}
.api-key-row input {{ flex: 1; font-size: 0.72rem; padding: 4px 6px; }}
th {{
    background: #f0f2f5; color: #e94560; padding: 8px 10px; text-align: left;
    font-weight: 600; position: sticky; top: 0; z-index: 1;
    border-bottom: 2px solid #dfe6e9; white-space: nowrap; cursor: pointer;
}}
th:hover {{ background: #e8eaed; }}
th.sort-asc::after {{ content: ' ▲'; font-size: 0.7em; color: #e94560; }}
th.sort-desc::after {{ content: ' ▼'; font-size: 0.7em; color: #e94560; }}
td {{ padding: 6px 10px; border-bottom: 1px solid #eee; white-space: nowrap; }}
tr:hover {{ background: #f8f9fa; }}
td a {{ color: #0984e3; text-decoration: none; }}
td a:hover {{ text-decoration: underline; }}
td input {{
    width: 100%; border: none; background: transparent; font: inherit; color: inherit;
    padding: 2px 4px; outline: none;
}}
td input:focus {{ background: #fff3cd; border-radius: 2px; }}
td.editing {{ padding: 2px 4px; background: #fffcf0; }}
td.cell-selected {{ background: #dfe6fd !important; }}
td[data-src-url].active {{ outline: 2px solid #e94560; outline-offset: -2px; cursor: pointer; }}
td[data-src-url] {{ cursor: pointer; }}
tr.row-selected td {{ background: #e3edff !important; }}
tr.row-selected .rownum-cell {{ background: #b3c9f7 !important; color: #1a3a8f !important; font-weight: 700; }}
#db-tbody {{ user-select: none; -webkit-user-select: none; }}
#content tbody {{ user-select: none; -webkit-user-select: none; }}
.rownum-cell {{ color: #b2bec3; text-align: right; font-size: 0.72rem; cursor: pointer; padding: 6px 6px 6px 4px !important; }}
.rownum-cell:hover {{ background: #e8eaed; }}
tbody tr:hover {{ background: #f0f2f5; }}
.sel-info {{ display: inline-block; font-size: 0.75rem; color: #636e72; margin-left: 10px; margin-top: 8px; vertical-align: middle; }}
.sel-info button {{ margin-left: 6px; font-size: 0.72rem; padding: 2px 8px; border: 1px solid #dfe6e9; border-radius: 3px; background: #fff; color: #636e72; cursor: pointer; }}
.sel-info button:hover {{ background: #f5f6fa; }}
.clear-sel {{ color: #e94560; cursor: pointer; margin-left: 6px; text-decoration: underline; font-size: 0.75rem; }}
td.cell-note {{ font-style: italic; color: #b2bec3; font-size: 0.72rem; white-space: normal; max-width: 180px; }}
.edit-count {{ font-size: 0.8rem; color: #e94560; font-weight: 600; }}
.cas-link {{ color: #0984e3; text-decoration: none; }}
.cas-link:hover {{ text-decoration: underline; }}
.save-indicator {{ display: none; color: #00b894; font-size: 0.8rem; font-weight: 600; }}
.save-indicator.visible {{ display: inline; }}
/* Per-cell source reference indicator */
.cell-ref {{
    display: inline-block; margin-left: 2px; font-size: 0.6rem; vertical-align: super;
    color: #b2bec3; cursor: pointer; line-height: 1; user-select: none;
    transition: color 0.15s;
}}
.cell-ref:hover {{ color: #e94560; }}
.cell-ref.active {{ color: #e94560; }}
.src-popup {{
    position: fixed; z-index: 9999; background: #fff; border: 1px solid #dfe6e9;
    border-radius: 6px; box-shadow: 0 4px 18px rgba(0,0,0,0.14);
    padding: 8px 12px; font-size: 0.78rem; color: #2d3436;
    max-width: 280px; pointer-events: auto;
}}
.src-popup-label {{ display: block; font-weight: 600; margin-bottom: 4px; color: #2d3436; }}
.src-popup-link {{
    display: inline-block; color: #e94560; text-decoration: none;
    font-size: 0.74rem; word-break: break-all;
}}
.src-popup-link:hover {{ text-decoration: underline; }}
/* ClassyFire class-level note superscript */
.cf-class-note {{
    font-size: 0.65rem; vertical-align: super; color: #b2bec3;
    cursor: help; margin-left: 1px;
}}
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
/* Structure tooltip */
.struct-tooltip {{ display: none; position: fixed; z-index: 9999; background: #fff; border: 2px solid #e94560; border-radius: 8px; padding: 4px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); pointer-events: none; }}
.struct-tooltip img {{ display: block; width: 200px; height: 200px; border-radius: 4px; }}
.struct-tooltip .struct-name {{ text-align: center; font-size: 0.7rem; color: #333; padding: 2px 4px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.struct-tooltip.loading img {{ opacity: 0.3; }}
.hoverable-name {{ cursor: help; border-bottom: 1px dotted #b2bec3; }}
{_db_csv_import_css}
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
<script>if (typeof pdfjsLib !== 'undefined') pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';</script>
</head>
<body>
<div class="header">
    <h1><a href="materialism.html">Materialism</a> &mdash; Database <button id="title-lock-btn" onclick="toggleDbLock()" title="Click to unlock editing" style="background:none;border:none;cursor:pointer;padding:0 0 2px 6px;vertical-align:middle;color:#b2bec3;line-height:1"><svg id="title-lock-svg" viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M12 17a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm6-9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2h1V6a5 5 0 0 1 10 0v2h1zM9 6v2h6V6a3 3 0 0 0-6 0z"/></svg></button></h1>
    <div class="nav-links">
        <a href="cas_review.html">Crosslink</a>
        <a href="materialism.html">Search</a>
    </div>
</div>
<div class="main">
    <div class="sidebar" id="sidebar">
        <button class="active-db-btn selected" id="active-db-btn" onclick="selectActiveDb()">
            Active Database
            <div class="btn-counts" id="active-db-counts"></div>
        </button>
        <button class="csv-import-btn" onclick="showCsvImportView()">&#8679; Quick CSV Import</button>
        <a href="import.html" class="import-link-btn">+ Full Import Pipeline</a>
        <div id="ds-list"></div>
        <button class="rebuild-btn" onclick="triggerRebuild()">Export Datasets</button>
    </div>
    <div class="content" id="content">
    </div>
</div>
<script>
// ===================== DATA =====================
var SOLVENTS = {db_solvents_json};
var POLYMERS = {db_polymers_json};
var CAS_CANDIDATES = {cas_candidates_json};
var DATASETS_META = {datasets_meta_json};
var DATASETS = {per_dataset_json};
// Color maps for category-based coloring
var CAT_COLORS = {cat_colors_json};
var POLY_CAT_COLORS = {poly_cat_colors_json};
var POLY_TYPE_TO_CAT = {poly_type_to_cat_json};

// ===================== STATE =====================
var _LS_DS_KEY = 'materialism_active_datasets';
function _loadActiveDsets() {{ try {{ var v = localStorage.getItem(_LS_DS_KEY); return v ? JSON.parse(v) : null; }} catch(e) {{ return null; }} }}
function _saveActiveDsets(obj) {{ try {{ localStorage.setItem(_LS_DS_KEY, JSON.stringify(obj)); }} catch(e) {{}} }}
function _getActiveDsets() {{ var s = _loadActiveDsets(); if (s) return s; var d = {{}}; Object.keys(DATASETS_META).forEach(function(k) {{ d[k] = true; }}); return d; }}
var _activeDsets = _getActiveDsets();
function _isDsActive(dsId) {{ if (!dsId) return true; var ids = dsId.split(','); for (var i = 0; i < ids.length; i++) {{ if (DATASETS[ids[i]] && _activeDsets[ids[i]] !== false) return true; }} return false; }}
function _isFromActiveDataset(item) {{ return !!item._imported && !!DATASETS[item.dsId] && _isDsActive(item.dsId); }}

// View mode: 'active_db' or a dataset id
var _viewMode = 'active_db';
var _activeDbTab = 'solvents'; // solvents or polymers
var _filterText = '';
var _sortCol = null;
var _sortAsc = true;
var _dbEditing = false;
var _dbEdits = {{}};
var _editMode = {{}}; // per-dataset edit mode

// Cell selection for active DB view
var _selCells = {{}};
var _dragSel = false;
var _dragStart = null;
var _dragRowNum = false;
var _dragRowStart = null;
var _lastRowNum = null;
var _visibleIndices = [];

// Cell selection for dataset detail view
var _mSelCells = {{}};
var _mSelRows = {{}};  // row-level selection (keyed by oidx) for gutter click/drag
var _mDragSel = false;
var _mDragStart = null;
var _mDragRowNum = false;
var _mDragRowStart = null;
var _mLastRowNum = null;
var _mVisibleOidxs = [];
var _mCurrentCols = [];

// ===================== LOAD IMPORTED DATASETS =====================
(function() {{
    try {{
        var raw = localStorage.getItem('materialism_imported_datasets');
        if (!raw) return;
        var imported = JSON.parse(raw);
        var _delRaw = localStorage.getItem('materialism_deleted_datasets');
        var _deletedIds = _delRaw ? JSON.parse(_delRaw) : [];
        Object.keys(imported).forEach(function(dsId) {{
            if (_activeDsets[dsId] === false) return; // explicitly toggled off
            if (_deletedIds.indexOf(dsId) !== -1) return; // deleted via UI — never re-add
            if (DATASETS[dsId] && DATASETS[dsId]._embedded) return; // already in embedded unified data
            var ds = imported[dsId];
            var meta = ds.meta || {{}};
            var srcLabel = meta.name || dsId;
            var srcUrl = meta.source_url || '';
            (ds.chemicals || []).forEach(function(c) {{
                SOLVENTS.push({{
                    name: c.name || '', cas: c.cas || '', smiles: c.smiles || '',
                    formula: c.formula || '', dd: c.dd || '', dp: c.dp || '', dh: c.dh || '',
                    mw: c.mw || '', bp: c.bp || '', density: c.density || '',
                    mv: c.mv || '', cat: c.cat || '', ghs: c.ghs || '',
                    conf: c.conf || '', srcN: 1, src: srcLabel, srcUrl: srcUrl,
                    dsId: dsId, _imported: true
                }});
            }});
            (ds.polymers || []).forEach(function(p) {{
                POLYMERS.push({{
                    name: p.name || '', cas: p.cas || '', dd: p.dd || '', dp: p.dp || '', dh: p.dh || '',
                    r: p.r || '', type: p.type || '', conf: p.conf || '',
                    srcN: 1, src: srcLabel, srcUrl: srcUrl,
                    dsId: dsId, _imported: true
                }});
            }});
            if (!DATASETS_META[dsId]) {{
                DATASETS_META[dsId] = {{ name: srcLabel, source_url: srcUrl }};
            }}
            if (!DATASETS[dsId]) {{
                DATASETS[dsId] = ds;
                DATASETS[dsId]._imported = true;
            }}
        }});
    }} catch(e) {{}}
}})();

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
    {{key:'dd', label:'\u03b4D (MPa\u00bd)', w:'78px', tip:'Dispersion parameter'}},
    {{key:'dp', label:'\u03b4P (MPa\u00bd)', w:'78px', tip:'Polarity parameter'}},
    {{key:'dh', label:'\u03b4H (MPa\u00bd)', w:'78px', tip:'Hydrogen bonding parameter'}},
    {{key:'mw', label:'MW (g/mol)', w:'80px', tip:'Molecular weight'}},
    {{key:'bp', label:'BP (\u00b0C)', w:'70px', tip:'Boiling point'}},
    {{key:'density', label:'Density (g/mL)', w:'90px', tip:'Density (g/mL)'}},
    {{key:'ghs', label:'GHS Hazard', w:'120px'}},
    {{key:'cfclass', label:'Class', w:'160px', tip:'ClassyFire chemical classification (subclass preferred)'}},
];
var POLY_COLS = [
    {{key:'name', label:'Name', w:'250px'}},
    {{key:'cas', label:'CAS #', w:'110px'}},
    {{key:'dd', label:'\u03b4D (MPa\u00bd)', w:'78px', tip:'Dispersion parameter'}},
    {{key:'dp', label:'\u03b4P (MPa\u00bd)', w:'78px', tip:'Polarity parameter'}},
    {{key:'dh', label:'\u03b4H (MPa\u00bd)', w:'78px', tip:'Hydrogen bonding parameter'}},
    {{key:'r', label:'R\u2080 (MPa\u00bd)', w:'70px', tip:'Interaction radius'}},
];

// ===================== ACTIVE DATABASE EDITS =====================
function loadDbEdits() {{
    try {{
        var saved = localStorage.getItem('materialism_db_edits');
        if (saved) _dbEdits = JSON.parse(saved);
    }} catch(e) {{}}
    updateEditCount();
}}

function saveDbEdits() {{
    try {{
        localStorage.setItem('materialism_db_edits', JSON.stringify(_dbEdits));
    }} catch(e) {{}}
    updateEditCount();
    var ind = document.getElementById('save-ind');
    if (ind) {{ ind.classList.add('visible'); setTimeout(function() {{ ind.classList.remove('visible'); }}, 1500); }}
}}

function updateEditCount() {{
    var n = Object.keys(_dbEdits).length;
    var el = document.getElementById('edit-count');
    if (el) el.textContent = n ? n + ' edit' + (n > 1 ? 's' : '') : '';
}}

function getDbVal(type, idx, field) {{
    var k = type + ':' + idx + ':' + field;
    if (_dbEdits.hasOwnProperty(k)) return _dbEdits[k];
    var arr = type === 'solvents' ? SOLVENTS : POLYMERS;
    return arr[idx][field] || '';
}}

function setDbVal(type, idx, field, val) {{
    var k = type + ':' + idx + ':' + field;
    var arr = type === 'solvents' ? SOLVENTS : POLYMERS;
    var orig = arr[idx][field] || '';
    if (val === orig) {{ delete _dbEdits[k]; }} else {{ _dbEdits[k] = val; }}
    saveDbEdits();
}}

var _LOCK_ICON_LOCKED = '<path d="M12 17a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm6-9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2h1V6a5 5 0 0 1 10 0v2h1zM9 6v2h6V6a3 3 0 0 0-6 0z"/>';
var _LOCK_ICON_UNLOCKED = '<path fill-rule="evenodd" d="M12 17a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM6 10h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2z"/><path fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" d="M9 10V6a3 3 0 0 1 6 0"/>';

function toggleDbLock() {{
    _dbEditing = !_dbEditing;
    var btn = document.getElementById('title-lock-btn');
    var svg = document.getElementById('title-lock-svg');
    if (btn && svg) {{
        if (_dbEditing) {{
            svg.innerHTML = _LOCK_ICON_UNLOCKED;
            btn.style.color = '#e94560';
            btn.title = 'Click to lock';
        }} else {{
            svg.innerHTML = _LOCK_ICON_LOCKED;
            btn.style.color = '#b2bec3';
            btn.title = 'Click to unlock editing';
        }}
    }}
    renderContent();
}}

function _countForTab(tab) {{
    var data = tab === 'solvents' ? SOLVENTS : POLYMERS;
    var n = 0;
    for (var i = 0; i < data.length; i++) {{ if (_isDsActive(data[i].dsId)) n++; }}
    return n;
}}

// ===================== VIEW SWITCHING =====================
function selectActiveDb() {{
    _viewMode = 'active_db';
    _sortCol = null;
    _sortAsc = true;
    _filterText = '';
    _selCells = {{}};
    _dragStart = null;
    _lastRowNum = null;
    buildSidebar();
    renderContent();
}}

function selectDs(dsId) {{
    _viewMode = dsId;
    _filterText = '';
    _sortCol = null;
    _sortAsc = true;
    _mSelCells = {{}};
    _mDragStart = null;
    _mLastRowNum = null;
    buildSidebar();
    renderContent();
}}

function switchTab(tab) {{
    _activeDbTab = tab;
    _sortCol = null;
    _selCells = {{}};
    renderContent();
}}

// ===================== SIDEBAR =====================
function updateActiveDbCounts() {{
    var el = document.getElementById('active-db-counts');
    if (el) el.textContent = _countForTab('solvents') + ' solvents, ' + _countForTab('polymers') + ' polymers';
}}

function buildSidebar() {{
    // Update active db button
    var btn = document.getElementById('active-db-btn');
    if (btn) {{
        if (_viewMode === 'active_db') btn.classList.add('selected');
        else btn.classList.remove('selected');
    }}
    updateActiveDbCounts();

    // Build dataset list
    var sb = document.getElementById('ds-list');
    var dsKeys = Object.keys(DATASETS);
    if (dsKeys.length === 0) {{
        sb.innerHTML = '<div style="padding:10px 0;color:#636e72;font-size:0.82rem">No datasets yet. Use the import tools above.</div>';
        return;
    }}
    var html = '<div style="font-size:0.75rem;color:#636e72;text-transform:uppercase;letter-spacing:0.5px;margin:8px 0 6px">Datasets</div>';
    dsKeys.forEach(function(k) {{
        var ds = DATASETS[k];
        var m = ds.meta || {{}};
        var active = _activeDsets[k] !== false;
        var sel = _viewMode === k ? ' active' : '';
        var nc = (ds.chemicals || []).length;
        var np = (ds.polymers || []).length;
        html += '<div class="ds-card' + sel + '" onclick="selectDs(\\x27' + k + '\\x27)">';
        html += '<h3>' + (m.name || k) + '</h3>';
        html += '<div class="ds-counts">' + nc + ' chemicals, ' + np + ' polymers</div>';
        html += '<span class="ds-status ' + (active ? 'on' : 'off') + '">' + (active ? 'Active' : 'Inactive') + '</span>';
        html += '</div>';
    }});
    sb.innerHTML = html;
}}

// ===================== RENDER ACTIVE DATABASE =====================
function renderActiveDb() {{
    var ct = document.getElementById('content');
    var _prevWrap = ct.querySelector('.table-wrap');
    var _savedScroll = _prevWrap ? _prevWrap.scrollTop : 0;
    var cols = _activeDbTab === 'solvents' ? SOLV_COLS : POLY_COLS;
    var data = _activeDbTab === 'solvents' ? SOLVENTS : POLYMERS;
    var filter = _filterText.toLowerCase().trim();

    // Build toolbar
    var toolbar = '<div class="toolbar">';
    toolbar += '<div class="db-tabs">';
    toolbar += '<button id="tab-solv" class="db-tab' + (_activeDbTab === 'solvents' ? ' active' : '') + '" onclick="switchTab(\\x27solvents\\x27)">Solvents (' + _countForTab('solvents') + ')</button>';
    toolbar += '<button id="tab-poly" class="db-tab' + (_activeDbTab === 'polymers' ? ' active' : '') + '" onclick="switchTab(\\x27polymers\\x27)">Polymers (' + _countForTab('polymers') + ')</button>';
    toolbar += '</div>';
    toolbar += '<input type="text" id="db-filter" placeholder="Filter by name or CAS..." oninput="_filterText=this.value;renderContent()" value="' + (_filterText||'').replace(/"/g,'&quot;') + '">';
    toolbar += '<span class="edit-count" id="edit-count"></span>';
    toolbar += '<span class="save-indicator" id="save-ind">Saved</span>';
    var _dbSelN = Object.keys(_selCells).length;
    var _dbInferLabel = _dbSelN > 0 ? 'Infer Missing Values (' + _dbSelN + ' cell' + (_dbSelN > 1 ? 's' : '') + ')' : 'Infer Missing Values';
    toolbar += '<button class="infer-btn" id="db-infer-btn" onclick="inferActiveDb()"' + (_inferRunning ? ' disabled' : '') + '>' + _dbInferLabel + '</button>';
    toolbar += '<span class="sel-info" id="db-sel-info"></span>';
    toolbar += '</div>';
    toolbar += '<div class="infer-progress" id="infer-progress" style="display:none"></div>';

    // Build index array for filtering
    var indices = [];
    for (var i = 0; i < data.length; i++) {{
        if (!_isDsActive(data[i].dsId)) continue;
        if (filter) {{
            var name = getDbVal(_activeDbTab, i, 'name').toLowerCase();
            var cas = getDbVal(_activeDbTab, i, 'cas').toLowerCase();
            if (name.indexOf(filter) === -1 && cas.indexOf(filter) === -1) continue;
        }}
        indices.push(i);
    }}

    // Sort
    if (_sortCol !== null) {{
        var key = cols[_sortCol].key;
        indices.sort(function(a, b) {{
            var va = getDbVal(_activeDbTab, a, key);
            var vb = getDbVal(_activeDbTab, b, key);
            var na = parseFloat(va), nb = parseFloat(vb);
            if (!isNaN(na) && !isNaN(nb)) return _sortAsc ? na - nb : nb - na;
            return _sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
        }});
    }}

    _visibleIndices = indices;

    // Header
    var hdr = '<tr><th style="width:40px">#</th>';
    for (var ci = 0; ci < cols.length; ci++) {{
        var c = cols[ci];
        var cls = '';
        if (_sortCol === ci) cls = _sortAsc ? ' class="sort-asc"' : ' class="sort-desc"';
        hdr += '<th' + cls + ' data-col="' + c.key + '"' + (c.tip ? ' title="' + c.tip + '"' : '') + ' onclick="dbSortBy(' + ci + ')">' + c.label + '</th>';
    }}
    hdr += '</tr>';

    // Body
    var html = '';
    for (var ri = 0; ri < indices.length; ri++) {{
        var idx = indices[ri];
        html += '<tr>';
        html += '<td class="rownum-cell" data-rowidx="' + idx + '">' + (ri + 1) + '</td>';
        for (var ci = 0; ci < cols.length; ci++) {{
            var c = cols[ci];
            var val = getDbVal(_activeDbTab, idx, c.key);
            var editKey = _activeDbTab + ':' + idx + ':' + c.key;
            var isEdited = _dbEdits.hasOwnProperty(editKey);
            var cellId = idx + ':' + c.key;
            var cellSel = _selCells[cellId] ? ' cell-selected' : '';

            if (_dbEditing) {{
                html += '<td class="editing' + cellSel + '" data-row="' + idx + '" data-col="' + c.key + '"' + (isEdited ? ' style="background:#e8f8f0"' : '') + '>';
                html += '<input type="text" value="' + String(val).replace(/"/g, '&quot;') + '" onchange="setDbVal(\\x27' + _activeDbTab + '\\x27,' + idx + ',\\x27' + c.key + '\\x27,this.value)">';
                html += '</td>';
            }} else {{
                var display = val;
                if (c.key === 'name' && val) {{
                    display = '<span class="hoverable-name" onmouseenter="showStructure(event,\\x27' + encodeURIComponent(String(val)) + '\\x27)" onmouseleave="hideStructure()">' + val + '</span>';
                }}
                if (val !== '' && val != null) {{
                    if (c.key === 'dd' || c.key === 'dp' || c.key === 'dh' || c.key === 'mw' || c.key === 'r') {{
                        var n = parseFloat(val); if (!isNaN(n)) display = n.toFixed(1);
                    }} else if (c.key === 'bp') {{
                        var n = parseFloat(val); if (!isNaN(n)) display = n.toFixed(0);
                    }} else if (c.key === 'density') {{
                        var n = parseFloat(val); if (!isNaN(n)) display = n.toFixed(2);
                    }}
                }}
                if (c.key === 'cas') {{
                    if (val) {{
                        display = '<a class="cas-link" href="https://commonchemistry.cas.org/detail?cas_rn=' + encodeURIComponent(val) + '" target="_blank" rel="noopener">' + val + '</a>';
                    }} else {{
                        var matName = (_activeDbTab === 'solvents' ? SOLVENTS : POLYMERS)[idx].name;
                        if (CAS_CANDIDATES[matName]) {{
                            display = '<button class="cas-missing" onclick="openCrosslink(event,\\x27' + _activeDbTab + '\\x27,' + idx + ')" title="Find CAS #">?</button>';
                        }}
                    }}
                }}
                if (c.key === 'cfclass' && val) {{
                    var _cfMat = (_activeDbTab === 'solvents' ? SOLVENTS : POLYMERS)[idx];
                    var _cfLvl = _cfMat.cflevel || '';
                    if (_cfLvl === 'class') {{
                        display = val + '<sup class="cf-class-note" title="ClassyFire class used \u2014 no subclass available for this compound">\u2020</sup>';
                    }}
                }}
                // Per-cell source reference — stored as data attrs, shown on cell click
                var _mat = (_activeDbTab === 'solvents' ? SOLVENTS : POLYMERS)[idx];
                var _fieldSrc = _mat._src && _mat._src[c.key];
                var _refLabel = '', _refUrl = '';
                if (_fieldSrc && _fieldSrc.url) {{
                    _refLabel = _fieldSrc.label || _mat.src || 'Source';
                    _refUrl = _fieldSrc.url;
                }} else if (_mat.srcUrl && val !== '' && val != null) {{
                    _refLabel = _mat.src || 'Source';
                    _refUrl = _mat.srcUrl;
                }}
                var cellStyle = isEdited ? 'background:#e8f8f0' : '';
                var _srcAttrs = _refUrl ? ' data-src-lbl="' + _refLabel.replace(/"/g,'&quot;') + '" data-src-url="' + _refUrl.replace(/"/g,'&quot;') + '"' : '';
                html += '<td class="' + cellSel.trim() + '" data-row="' + idx + '" data-col="' + c.key + '"' + _srcAttrs + (cellStyle ? ' style="' + cellStyle + '"' : '') + '>' + display + '</td>';
            }}
        }}
        html += '</tr>';
    }}

    ct.innerHTML = toolbar + '<div class="table-wrap"><table id="db-table"><thead id="db-thead">' + hdr + '</thead><tbody id="db-tbody">' + html + '</tbody></table></div>';
    if (_savedScroll) {{ var _nw = ct.querySelector('.table-wrap'); if (_nw) _nw.scrollTop = _savedScroll; }}
    updateEditCount();
}}

function dbSortBy(col) {{
    if (_sortCol === col) _sortAsc = !_sortAsc;
    else {{ _sortCol = col; _sortAsc = true; }}
    renderContent();
}}

// ===================== RENDER DATASET DETAIL =====================
function renderDetail() {{
    var ct = document.getElementById('content');
    var _prevDC = ct.querySelector('.detail-content');
    var _savedDetailScroll = _prevDC ? _prevDC.scrollTop : 0;
    var dsId = _viewMode;
    var ds = DATASETS[dsId];
    if (!ds) {{
        ct.innerHTML = '<div class="detail-content"><div class="empty-state"><h2>Dataset not found</h2></div></div>';
        return;
    }}
    var m = ds.meta || {{}};
    var active = _activeDsets[dsId] !== false;
    var nc = (ds.chemicals || []).length;
    var np = (ds.polymers || []).length;

    var isEdit = !!_editMode[dsId];
    var html = '<div class="detail-content">';
    html += '<div class="ds-detail-header">';
    html += '<div class="ds-title-row">';
    html += '<h2>' + (m.name || dsId) + '</h2>';
    html += '<button class="delete-ds-btn" id="delete-ds-btn" onclick="deleteDsClick(\\x27' + dsId + '\\x27)">';
    html += '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>';
    html += 'Delete';
    html += '</button>';
    html += '</div>';
    html += '<div class="ds-meta">';
    if (m.source_url) html += 'Source: <a href="' + m.source_url + '" target="_blank">' + m.source_url + '</a><br>';
    if (m.imported_at) html += 'Imported: ' + m.imported_at.replace('T', ' ').replace(/\..*/,'') + '<br>';
    html += nc + ' chemicals, ' + np + ' polymers<br>';
    if (m.confidence_tier != null) html += 'Confidence tier: ' + m.confidence_tier + '<br>';
    if (m.quality_notes) html += 'Notes: ' + m.quality_notes + '<br>';
    if (m.fields_available) html += 'Fields: ' + m.fields_available.join(', ') + '<br>';
    html += '</div>';
    html += '<button class="toggle-btn ' + (active ? 'on' : 'off') + '" onclick="toggleDs(\\x27' + dsId + '\\x27)">' + (active ? 'Active (click to deactivate)' : 'Inactive (click to activate)') + '</button>';
    var _rowSelN = Object.keys(_mSelRows).length;
    var _selN = _mGetSelCount();
    var _rowSfx = _rowSelN > 0 ? ' (' + _rowSelN + ' row' + (_rowSelN > 1 ? 's' : '') + ')' : '';
    html += '<button class="infer-btn" id="solvent-infer-btn" onclick="inferMissing(\\x27' + dsId + '\\x27)"' + (_inferRunning ? ' disabled' : '') + '>Solvent Infer' + _rowSfx + '</button>';
    html += '<button class="infer-btn" id="poly-infer-btn" onclick="inferPolymer(\\x27' + dsId + '\\x27)"' + (_inferRunning ? ' disabled' : '') + '>Polymer Infer' + _rowSfx + '</button>';
    var _anySelN = _rowSelN > 0 ? _rowSelN : _selN;
    var _selInfoText = _rowSelN > 0 ? _rowSelN + ' row' + (_rowSelN > 1 ? 's' : '') + ' selected' : (_selN > 0 ? _selN + ' cell' + (_selN > 1 ? 's' : '') + ' selected' : '');
    html += '<span class="sel-info" id="sel-info"' + (_anySelN > 0 ? '' : ' style="display:none"') + '>' + (_anySelN > 0 ? _selInfoText + ' <button onclick="clearSelection()">Clear</button>' : '') + '</span>';
    html += '</div>';
    html += '<div class="infer-progress" id="infer-progress" style="display:none"></div>';

    html += '<div class="filter-row"><input type="text" id="manage-filter" placeholder="Filter by name or CAS..." oninput="_filterText=this.value;renderContent()" value="' + (_filterText||'').replace(/"/g,'&quot;') + '"></div>';

    // Determine what data to show
    var items, cols;
    if (nc > 0) {{
        items = ds.chemicals;
        cols = ['name','cas','dd','dp','dh','mw','bp','cat'];
    }} else {{
        items = ds.polymers;
        cols = ['name','cas','dd','dp','dh','r','cat'];
    }}
    // Append any extra fields present on imported entries (passthrough columns)
    if (items && items.length) {{
        var _stdSet = {{}};
        cols.forEach(function(c) {{ _stdSet[c] = true; }});
        var _extraKeys = [];
        var _seenExtra = {{}};
        items.forEach(function(item) {{
            Object.keys(item).forEach(function(k) {{
                if (!_stdSet[k] && !_seenExtra[k] && k[0] !== '_') {{
                    _seenExtra[k] = true;
                    _extraKeys.push(k);
                }}
            }});
        }});
        if (_extraKeys.length) cols = cols.concat(_extraKeys);
    }}

    if (!items || items.length === 0) {{
        html += '<p style="color:#636e72">No data in this dataset.</p>';
        html += '</div>';
        ct.innerHTML = html;
        if (_savedDetailScroll) {{ var _ndc2 = ct.querySelector('.detail-content'); if (_ndc2) _ndc2.scrollTop = _savedDetailScroll; }}
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
        name:'Name', cas:'CAS #',
        dd:'\u03b4D (MPa\u00bd)', dp:'\u03b4P (MPa\u00bd)', dh:'\u03b4H (MPa\u00bd)',
        mw:'MW (g/mol)', bp:'BP (\u00b0C)', cat:'Category',
        r:'R\u2080 (MPa\u00bd)', type:'Type',
        smiles:'SMILES', formula:'Formula', density:'Density (g/mL)',
        ghs:'GHS'
    }};

    items.forEach(function(item, idx) {{ item._oidx = idx; }});

    _mCurrentCols = cols;
    _mVisibleOidxs = [];

    html += '<table><thead><tr><th style="width:40px">#</th>';
    cols.forEach(function(c, i) {{
        html += '<th data-col="' + c + '" onclick="manageSort(' + i + ')">' + (colLabels[c]||c);
        if (_sortCol === i) html += _sortAsc ? ' \u25B2' : ' \u25BC';
        html += '</th>';
    }});
    html += '</tr></thead><tbody>';
    var dsSource = (m.name || dsId);
    var dsSourceUrl = m.source_url || '';
    var limit = Math.min(filtered.length, 2000);
    for (var i = 0; i < limit; i++) {{
        var r = filtered[i];
        _mVisibleOidxs.push(r._oidx);
        html += '<tr data-oidx="' + r._oidx + '">';
        html += '<td class="rownum-cell" data-rowidx="' + r._oidx + '">' + (i + 1) + '</td>';
        cols.forEach(function(c) {{
            var v = r[c]; if (v == null) v = '';
            var cellId = r._oidx + ':' + c;
            var cellSel = _mSelCells[cellId] ? ' cell-selected' : '';
            var srcInfo = r._src && r._src[c];
            var srcLabel = srcInfo ? srcInfo.label : dsSource;
            var srcUrl = srcInfo ? (srcInfo.url || '') : dsSourceUrl;
            var isInferred = !!srcInfo;
            var isUncertain = srcInfo && srcInfo.uncertain;
            var isNote = srcInfo && srcInfo.isNote;
            var cls = isInferred ? 'inferred' : '';
            if (isNote) {{ if (cls) cls += ' '; cls += 'cell-note'; }}
            if (cellSel) {{ if (cls) cls += ' '; cls += 'cell-selected'; }}
            var attrs = ' data-row="' + r._oidx + '" data-col="' + c + '"';
            attrs += ' data-src="' + srcLabel.replace(/"/g,'&quot;') + '"';
            if (srcUrl) attrs += ' data-src-url="' + srcUrl.replace(/"/g,'&quot;') + '"';
            if (isEdit && !isNote) {{
                attrs += ' contenteditable="true" data-ds="' + dsId + '" data-idx="' + r._oidx + '" data-field="' + c + '"';
                if (cls) cls += ' ';
                cls += 'editable';
            }}
            var catStyle = '';
            var display = v;
            if (c === 'name' && v) {{
                display = '<span class="hoverable-name" onmouseenter="showStructure(event,\\x27' + encodeURIComponent(String(v)) + '\\x27)" onmouseleave="hideStructure()">' + v + '</span>';
            }} else if (c === 'cat' && v) {{
                var _catMap = (nc > 0) ? CAT_COLORS : POLY_CAT_COLORS;
                var _catC = _catMap[v] || '#888';
                display = '<span style="display:inline-flex;align-items:center;gap:5px"><span style="width:8px;height:8px;border-radius:50%;flex-shrink:0;background:' + _catC + '"></span>' + v + '</span>';
            }}
            html += '<td' + (cls ? ' class="' + cls + '"' : '') + attrs + catStyle + '>' + display;
            html += '</td>';
        }});
        html += '</tr>';
    }}
    if (filtered.length > limit) {{
        html += '<tr><td colspan="' + (cols.length + 1) + '" style="color:#636e72;text-align:center">... and ' + (filtered.length - limit) + ' more rows</td></tr>';
    }}
    html += '</tbody></table>';
    html += '<div style="margin-top:8px;font-size:0.8rem;color:#636e72">Showing ' + Math.min(limit, filtered.length) + ' of ' + filtered.length + ' entries</div>';
    html += '</div>';

    var _prevFocus = document.activeElement;
    var _prevSel = null;
    if (_prevFocus && _prevFocus.id === 'manage-filter') {{
        _prevSel = {{ start: _prevFocus.selectionStart, end: _prevFocus.selectionEnd }};
    }}

    ct.innerHTML = html;
    if (_savedDetailScroll) {{ var _ndc = ct.querySelector('.detail-content'); if (_ndc) _ndc.scrollTop = _savedDetailScroll; }}

    if (_prevSel !== null) {{
        var inp = document.getElementById('manage-filter');
        if (inp) {{ inp.focus(); inp.selectionStart = _prevSel.start; inp.selectionEnd = _prevSel.end; }}
    }}
}}

function manageSort(col) {{
    if (_sortCol === col) _sortAsc = !_sortAsc;
    else {{ _sortCol = col; _sortAsc = true; }}
    renderContent();
}}

// ===================== MAIN RENDER =====================
function renderContent() {{
    if (_viewMode === 'active_db') {{
        renderActiveDb();
    }} else if (_viewMode === '_csv_import') {{
        _renderCsvImportPanel();
    }} else {{
        renderDetail();
    }}
}}

// ===================== DATASET MANAGEMENT =====================
function toggleDs(dsId) {{
    _activeDsets[dsId] = !(_activeDsets[dsId] !== false);
    _saveActiveDsets(_activeDsets);
    buildSidebar();
    renderContent();
}}

function toggleEditMode(dsId) {{
    _editMode[dsId] = !_editMode[dsId];
    renderContent();
}}

function _cellEdited(td, dsId, itemIdx, field) {{
    var newVal = td.textContent.trim();
    var ds = DATASETS[dsId];
    var items = (ds.chemicals && ds.chemicals.length > 0) ? ds.chemicals : ds.polymers || [];
    var item = items[itemIdx];
    if (!item) return;
    var numFields = ['dd','dp','dh','mw','bp','r','density'];
    if (numFields.indexOf(field) !== -1) {{
        if (newVal === '') {{ item[field] = ''; }}
        else {{
            var n = parseFloat(newVal);
            item[field] = isNaN(n) ? newVal : n;
        }}
    }} else {{
        item[field] = newVal;
    }}
    if (!item._src) item._src = {{}};
    item._src[field] = {{ label: 'Manual edit', url: '', uncertain: false }};
    _saveImportedDatasets();
    buildSidebar();
}}

var _deleteConfirmDs = null;
var _deleteConfirmTimer = null;

function deleteDsClick(dsId) {{
    var btn = document.getElementById('delete-ds-btn');
    if (_deleteConfirmDs === dsId) {{
        clearTimeout(_deleteConfirmTimer);
        _deleteConfirmDs = null;
        deleteDs(dsId);
        return;
    }}
    _deleteConfirmDs = dsId;
    if (btn) {{
        btn.classList.add('confirm');
        btn.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>Are you sure?';
    }}
    _deleteConfirmTimer = setTimeout(function() {{
        _deleteConfirmDs = null;
        if (btn) {{
            btn.classList.remove('confirm');
            btn.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>Delete';
        }}
    }}, 3000);
}}

function deleteDs(dsId) {{
    try {{
        var raw = localStorage.getItem('materialism_deleted_datasets');
        var deleted = raw ? JSON.parse(raw) : [];
        if (!Array.isArray(deleted)) deleted = [];
        if (deleted.indexOf(dsId) === -1) deleted.push(dsId);
        localStorage.setItem('materialism_deleted_datasets', JSON.stringify(deleted));
    }} catch(e) {{}}
    delete DATASETS[dsId];
    delete _activeDsets[dsId];
    _saveActiveDsets(_activeDsets);
    _saveImportedDatasets();
    delete _editMode[dsId];
    _mSelCells = {{}};
    _mDragStart = null;
    _mLastRowNum = null;
    selectActiveDb();
}}

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
        h += '</div>';
        if (o.iupac) h += '<div class="xl-opt-detail">IUPAC: ' + o.iupac + '</div>';
        h += '<div class="xl-opt-detail">' + o.reason + '</div>';
        h += '</div>';
    }}
    _xlPop.innerHTML = h;
    _xlPop.classList.add('visible');

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

    if (o.cas) setDbVal(_xlType, _xlIdx, 'cas', o.cas);
    if (o.name && o.name !== mat.name) setDbVal(_xlType, _xlIdx, 'name', o.name);
    if (_xlType === 'solvents' && o.mw) setDbVal(_xlType, _xlIdx, 'mw', String(o.mw));
    if (_xlType === 'solvents' && o.density) setDbVal(_xlType, _xlIdx, 'density', String(o.density));

    closeCrosslink();
    renderContent();
}}

// Close popover / source dropdown on outside click
document.addEventListener('click', function(e) {{
    if (_xlPop && _xlPop.classList.contains('visible') && !_xlPop.contains(e.target) && !e.target.classList.contains('cas-missing')) {{
        closeCrosslink();
    }}
    // close src popup on outside click
    if (_srcPop && _srcPop.style.display !== 'none' && !_srcPop.contains(e.target) && !e.target.closest('td[data-src-url]')) {{
        _closeSrcPop();
    }}
}});

// ===================== SOURCE REFERENCE POPUP =====================
var _srcPop = null;
var _srcPopRef = null; // the .cell-ref element that opened the popup
function _showSrcPop(el, label, url) {{
    if (_srcPop && _srcPopRef === el) {{
        // Second click on same ref → navigate
        window.open(url, '_blank', 'noopener');
        _closeSrcPop();
        return;
    }}
    _closeSrcPop();
    _srcPopRef = el;
    el.classList.add('active');
    if (!_srcPop) {{
        _srcPop = document.createElement('div');
        _srcPop.className = 'src-popup';
        document.body.appendChild(_srcPop);
    }}
    _srcPop.innerHTML = '<span class="src-popup-label">' + label.replace(/</g,'&lt;') + '</span>' +
        '<a class="src-popup-link" href="' + url + '" target="_blank" rel="noopener">Open source \u2197</a>';
    _srcPop.style.display = 'block';
    var rect = el.getBoundingClientRect();
    var popW = _srcPop.offsetWidth, popH = _srcPop.offsetHeight;
    var left = rect.left;
    var top = rect.bottom + 6;
    if (top + popH > window.innerHeight - 8) top = rect.top - popH - 6;
    if (left + popW > window.innerWidth - 8) left = window.innerWidth - popW - 8;
    if (left < 4) left = 4;
    _srcPop.style.left = left + 'px';
    _srcPop.style.top = top + 'px';
}}
function _closeSrcPop() {{
    if (_srcPopRef) {{ _srcPopRef.classList.remove('active'); _srcPopRef = null; }}
    if (_srcPop) {{ _srcPop.style.display = 'none'; }}
}}

// ===================== CELL SELECTION (ACTIVE DB) =====================
function _getCellFromEvent(e) {{
    var td = e.target.closest('#db-tbody td[data-row][data-col]');
    if (!td) return null;
    return {{ row: parseInt(td.getAttribute('data-row')), col: td.getAttribute('data-col'), el: td }};
}}

function _cellsBetween(a, b) {{
    var cols = _activeDbTab === 'solvents' ? SOLV_COLS : POLY_COLS;
    var colKeys = cols.map(function(c) {{ return c.key; }});
    var ci1 = colKeys.indexOf(a.col), ci2 = colKeys.indexOf(b.col);
    var vi1 = _visibleIndices.indexOf(a.row), vi2 = _visibleIndices.indexOf(b.row);
    if (vi1 === -1 || vi2 === -1) return {{}};
    var vMin = Math.min(vi1, vi2), vMax = Math.max(vi1, vi2);
    var cMin = Math.min(ci1, ci2), cMax = Math.max(ci1, ci2);
    var cells = {{}};
    for (var v = vMin; v <= vMax; v++) {{
        for (var c = cMin; c <= cMax; c++) {{
            cells[_visibleIndices[v] + ':' + colKeys[c]] = true;
        }}
    }}
    return cells;
}}

function _selectFullRow(rowIdx) {{
    var cols = _activeDbTab === 'solvents' ? SOLV_COLS : POLY_COLS;
    cols.forEach(function(c) {{ _selCells[rowIdx + ':' + c.key] = true; }});
}}

function _selectFullCol(colKey) {{
    _visibleIndices.forEach(function(idx) {{ _selCells[idx + ':' + colKey] = true; }});
}}

function _updateDbSelInfo() {{
    var el = document.getElementById('db-sel-info');
    if (!el) return;
    var n = Object.keys(_selCells).length;
    if (n === 0) {{ el.innerHTML = ''; }} else {{
        el.innerHTML = n + ' cell' + (n > 1 ? 's' : '') + ' selected <button onclick="clearCellSel()">Clear</button>';
    }}
    var ibtn = document.getElementById('db-infer-btn');
    if (ibtn && !_inferRunning) {{
        ibtn.textContent = n > 0 ? 'Infer Missing Values (' + n + ' cell' + (n > 1 ? 's' : '') + ')' : 'Infer Missing Values';
    }}
}}

function clearCellSel() {{
    _selCells = {{}};
    _lastRowNum = null;
    var tds = document.querySelectorAll('#db-tbody td.cell-selected');
    for (var i = 0; i < tds.length; i++) tds[i].classList.remove('cell-selected');
    _updateDbSelInfo();
}}

function _applyCellSelClasses() {{
    var tds = document.querySelectorAll('#db-tbody td[data-row][data-col]');
    for (var i = 0; i < tds.length; i++) {{
        var key = tds[i].getAttribute('data-row') + ':' + tds[i].getAttribute('data-col');
        if (_selCells[key]) tds[i].classList.add('cell-selected');
        else tds[i].classList.remove('cell-selected');
    }}
}}

// ===================== CELL SELECTION (DATASET DETAIL) =====================
function _mGetCellFromEvent(e) {{
    var td = e.target.closest('#content tbody td[data-row][data-col]');
    if (!td) return null;
    return {{ row: parseInt(td.getAttribute('data-row')), col: td.getAttribute('data-col') }};
}}

function _mCellsBetween(a, b) {{
    var ci1 = _mCurrentCols.indexOf(a.col), ci2 = _mCurrentCols.indexOf(b.col);
    var vi1 = _mVisibleOidxs.indexOf(a.row), vi2 = _mVisibleOidxs.indexOf(b.row);
    if (vi1 === -1 || vi2 === -1) return {{}};
    var vMin = Math.min(vi1, vi2), vMax = Math.max(vi1, vi2);
    var cMin = Math.min(ci1, ci2), cMax = Math.max(ci1, ci2);
    var cells = {{}};
    for (var v = vMin; v <= vMax; v++) {{
        for (var c = cMin; c <= cMax; c++) {{
            cells[_mVisibleOidxs[v] + ':' + _mCurrentCols[c]] = true;
        }}
    }}
    return cells;
}}

function _mSelectFullRow(oidx) {{
    _mCurrentCols.forEach(function(c) {{ _mSelCells[oidx + ':' + c] = true; }});
}}

function _mSelectFullCol(colKey) {{
    _mVisibleOidxs.forEach(function(idx) {{ _mSelCells[idx + ':' + colKey] = true; }});
}}

function _mGetSelCount() {{ return Object.keys(_mSelCells).length; }}
function _mGetRowSelCount() {{ return Object.keys(_mSelRows).length; }}

function _updateInferBtn() {{
    var rn = _mGetRowSelCount();
    var sfx = rn > 0 ? ' (' + rn + ' row' + (rn > 1 ? 's' : '') + ')' : '';
    var sb = document.getElementById('solvent-infer-btn');
    if (sb) sb.textContent = 'Solvent Infer' + sfx;
    var pb = document.getElementById('poly-infer-btn');
    if (pb) pb.textContent = 'Polymer Infer' + sfx;
    // active-db infer btn (unchanged)
    var btn = document.getElementById('db-infer-btn');
    if (!btn) return;
    var cn = _mGetSelCount();
    if (rn > 0) {{ btn.textContent = 'Infer ' + rn + ' Row' + (rn > 1 ? 's' : ''); }}
    else if (cn > 0) {{ btn.textContent = 'Infer Missing Values (' + cn + ' cell' + (cn > 1 ? 's' : '') + ')'; }}
    else {{ btn.textContent = 'Infer All Rows'; }}
}}

function _updateSelInfo() {{
    var el = document.getElementById('sel-info');
    var rn = _mGetRowSelCount();
    var cn = _mGetSelCount();
    if (el) {{
        if (rn > 0) {{
            el.innerHTML = rn + ' row' + (rn > 1 ? 's' : '') + ' selected <button onclick="clearSelection()">Clear</button>';
            el.style.display = '';
        }} else if (cn > 0) {{
            el.innerHTML = cn + ' cell' + (cn > 1 ? 's' : '') + ' selected <button onclick="clearSelection()">Clear</button>';
            el.style.display = '';
        }} else {{ el.style.display = 'none'; }}
    }}
    _updateInferBtn();
}}

function clearSelection() {{
    _mSelCells = {{}};
    _mSelRows = {{}};
    _mDragStart = null;
    _mLastRowNum = null;
    var tds = document.querySelectorAll('#content tbody td.cell-selected');
    for (var i = 0; i < tds.length; i++) tds[i].classList.remove('cell-selected');
    var trs = document.querySelectorAll('#content tbody tr.row-selected');
    for (var i = 0; i < trs.length; i++) trs[i].classList.remove('row-selected');
    _updateSelInfo();
}}

function _mApplyCellSelClasses() {{
    var tds = document.querySelectorAll('#content tbody td[data-row][data-col]');
    for (var i = 0; i < tds.length; i++) {{
        var key = tds[i].getAttribute('data-row') + ':' + tds[i].getAttribute('data-col');
        if (_mSelCells[key]) tds[i].classList.add('cell-selected');
        else tds[i].classList.remove('cell-selected');
    }}
}}

function _mApplyRowSelClasses() {{
    var trs = document.querySelectorAll('#content tbody tr[data-oidx]');
    for (var i = 0; i < trs.length; i++) {{
        var oidx = trs[i].getAttribute('data-oidx');
        if (_mSelRows[oidx]) trs[i].classList.add('row-selected');
        else trs[i].classList.remove('row-selected');
    }}
}}

// ===================== MOUSE EVENT HANDLERS =====================
document.addEventListener('mousedown', function(e) {{
    if (e.target.closest('input') || e.target.closest('a') || e.target.closest('button') || e.target.closest('td[contenteditable="true"]')) return;

    if (_viewMode === 'active_db') {{
        // Active DB cell selection
        var rnCell = e.target.closest('#db-tbody td.rownum-cell');
        if (rnCell) {{
            e.preventDefault();
            var rowIdx = parseInt(rnCell.getAttribute('data-rowidx'));
            if (e.shiftKey && _lastRowNum != null) {{
                var vi1 = _visibleIndices.indexOf(_lastRowNum);
                var vi2 = _visibleIndices.indexOf(rowIdx);
                if (vi1 !== -1 && vi2 !== -1) {{
                    var vMin = Math.min(vi1, vi2), vMax = Math.max(vi1, vi2);
                    _selCells = {{}};
                    for (var v = vMin; v <= vMax; v++) _selectFullRow(_visibleIndices[v]);
                }}
            }} else if (e.ctrlKey || e.metaKey) {{
                var cols = _activeDbTab === 'solvents' ? SOLV_COLS : POLY_COLS;
                var firstKey = rowIdx + ':' + cols[0].key;
                if (_selCells[firstKey]) {{
                    cols.forEach(function(c) {{ delete _selCells[rowIdx + ':' + c.key]; }});
                }} else {{ _selectFullRow(rowIdx); }}
                _lastRowNum = rowIdx;
            }} else {{
                _selCells = {{}};
                _selectFullRow(rowIdx);
                _lastRowNum = rowIdx;
                _dragRowNum = true;
                _dragRowStart = rowIdx;
            }}
            _applyCellSelClasses();
            _updateDbSelInfo();
            return;
        }}

        var th = e.target.closest('#db-thead th[data-col]');
        if (th && (e.ctrlKey || e.metaKey)) {{
            e.preventDefault();
            var colKey = th.getAttribute('data-col');
            if (_selCells[_visibleIndices[0] + ':' + colKey]) {{
                _visibleIndices.forEach(function(idx) {{ delete _selCells[idx + ':' + colKey]; }});
            }} else {{ _selectFullCol(colKey); }}
            _applyCellSelClasses();
            _updateDbSelInfo();
            return;
        }}

        var srcTd = e.target.closest('#db-tbody td[data-src-url]');
        if (srcTd) {{
            e.preventDefault();
            _showSrcPop(srcTd, srcTd.getAttribute('data-src-lbl') || '', srcTd.getAttribute('data-src-url') || '');
            return;
        }}

        var cell = _getCellFromEvent(e);
        if (!cell) return;
        e.preventDefault();
        if (e.shiftKey && _dragStart) {{
            _selCells = _cellsBetween(_dragStart, cell);
        }} else if (e.ctrlKey || e.metaKey) {{
            var key = cell.row + ':' + cell.col;
            if (_selCells[key]) delete _selCells[key];
            else _selCells[key] = true;
            _dragStart = cell;
        }} else {{
            _selCells = {{}};
            _selCells[cell.row + ':' + cell.col] = true;
            _dragStart = cell;
            _dragSel = true;
        }}
        _applyCellSelClasses();
        _updateDbSelInfo();
    }} else {{
        // Dataset detail row selection via gutter
        var rnCell = e.target.closest('#content tbody td.rownum-cell');
        if (rnCell) {{
            e.preventDefault();
            // Gutter clicks always use row selection, clear cell selection
            _mSelCells = {{}};
            var rowIdx = parseInt(rnCell.getAttribute('data-rowidx'));
            if (e.shiftKey && _mLastRowNum != null) {{
                var vi1 = _mVisibleOidxs.indexOf(_mLastRowNum);
                var vi2 = _mVisibleOidxs.indexOf(rowIdx);
                if (vi1 !== -1 && vi2 !== -1) {{
                    var vMin = Math.min(vi1, vi2), vMax = Math.max(vi1, vi2);
                    _mSelRows = {{}};
                    for (var v = vMin; v <= vMax; v++) _mSelRows[String(_mVisibleOidxs[v])] = true;
                }}
            }} else if (e.ctrlKey || e.metaKey) {{
                if (_mSelRows[String(rowIdx)]) {{ delete _mSelRows[String(rowIdx)]; }}
                else {{ _mSelRows[String(rowIdx)] = true; }}
                _mLastRowNum = rowIdx;
            }} else {{
                _mSelRows = {{}};
                _mSelRows[String(rowIdx)] = true;
                _mLastRowNum = rowIdx;
                _mDragRowNum = true;
                _mDragRowStart = rowIdx;
            }}
            _mApplyRowSelClasses();
            _updateSelInfo();
            return;
        }}

        var th = e.target.closest('#content thead th[data-col]');
        if (th && (e.ctrlKey || e.metaKey)) {{
            e.preventDefault();
            var colKey = th.getAttribute('data-col');
            if (_mVisibleOidxs.length > 0 && _mSelCells[_mVisibleOidxs[0] + ':' + colKey]) {{
                _mVisibleOidxs.forEach(function(idx) {{ delete _mSelCells[idx + ':' + colKey]; }});
            }} else {{ _mSelectFullCol(colKey); }}
            _mApplyCellSelClasses();
            _updateSelInfo();
            return;
        }}

        var srcTd = e.target.closest('#content tbody td[data-src-url]');
        if (srcTd) {{
            e.preventDefault();
            _showSrcPop(srcTd, srcTd.getAttribute('data-src') || '', srcTd.getAttribute('data-src-url') || '');
            return;
        }}

        var cell = _mGetCellFromEvent(e);
        if (!cell) return;
        e.preventDefault();
        if (e.shiftKey && _mDragStart) {{
            _mSelCells = _mCellsBetween(_mDragStart, cell);
        }} else if (e.ctrlKey || e.metaKey) {{
            var key = cell.row + ':' + cell.col;
            if (_mSelCells[key]) delete _mSelCells[key];
            else _mSelCells[key] = true;
            _mDragStart = cell;
        }} else {{
            _mSelCells = {{}};
            _mSelCells[cell.row + ':' + cell.col] = true;
            _mDragStart = cell;
            _mDragSel = true;
        }}
        _mApplyCellSelClasses();
        _updateSelInfo();
    }}
}});

document.addEventListener('mousemove', function(e) {{
    if (_viewMode === 'active_db') {{
        if (_dragRowNum && _dragRowStart != null) {{
            e.preventDefault();
            var rnCell = e.target.closest('#db-tbody td.rownum-cell');
            if (!rnCell) return;
            var rowIdx = parseInt(rnCell.getAttribute('data-rowidx'));
            var vi1 = _visibleIndices.indexOf(_dragRowStart);
            var vi2 = _visibleIndices.indexOf(rowIdx);
            if (vi1 === -1 || vi2 === -1) return;
            var vMin = Math.min(vi1, vi2), vMax = Math.max(vi1, vi2);
            _selCells = {{}};
            for (var v = vMin; v <= vMax; v++) _selectFullRow(_visibleIndices[v]);
            _applyCellSelClasses();
            _updateDbSelInfo();
            return;
        }}
        if (!_dragSel || !_dragStart) return;
        e.preventDefault();
        var cell = _getCellFromEvent(e);
        if (!cell) return;
        _selCells = _cellsBetween(_dragStart, cell);
        _applyCellSelClasses();
        _updateDbSelInfo();
    }} else {{
        if (_mDragRowNum && _mDragRowStart != null) {{
            e.preventDefault();
            var rnCell = e.target.closest('#content tbody td.rownum-cell');
            if (!rnCell) return;
            var rowIdx = parseInt(rnCell.getAttribute('data-rowidx'));
            var vi1 = _mVisibleOidxs.indexOf(_mDragRowStart);
            var vi2 = _mVisibleOidxs.indexOf(rowIdx);
            if (vi1 === -1 || vi2 === -1) return;
            var vMin = Math.min(vi1, vi2), vMax = Math.max(vi1, vi2);
            _mSelRows = {{}};
            for (var v = vMin; v <= vMax; v++) _mSelRows[String(_mVisibleOidxs[v])] = true;
            _mApplyRowSelClasses();
            _updateSelInfo();
            return;
        }}
        if (!_mDragSel || !_mDragStart) return;
        e.preventDefault();
        var cell = _mGetCellFromEvent(e);
        if (!cell) return;
        _mSelCells = _mCellsBetween(_mDragStart, cell);
        _mApplyCellSelClasses();
        _updateSelInfo();
    }}
}});

document.addEventListener('mouseup', function(e) {{
    _dragSel = false;
    _dragRowNum = false;
    _mDragSel = false;
    _mDragRowNum = false;
}});

document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') {{
        if (_viewMode === 'active_db' && Object.keys(_selCells).length > 0) clearCellSel();
        else if (_viewMode !== 'active_db' && _mGetSelCount() > 0) clearSelection();
    }}
}});

// Editable cell blur handler
document.addEventListener('blur', function(e) {{
    var td = e.target;
    if (td.tagName !== 'TD' || !td.hasAttribute('contenteditable')) return;
    var dsId = td.getAttribute('data-ds');
    var idx = parseInt(td.getAttribute('data-idx'), 10);
    var field = td.getAttribute('data-field');
    if (dsId && !isNaN(idx) && field) {{
        _cellEdited(td, dsId, idx, field);
    }}
}}, true);

// Prevent Enter from inserting newlines in cells
document.addEventListener('keydown', function(e) {{
    if (e.target.tagName === 'TD' && e.target.hasAttribute('contenteditable') && e.key === 'Enter') {{
        e.preventDefault();
        e.target.blur();
    }}
}});

// Cell tooltip for dataset detail view
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

// ===================== LOCALSTORAGE PERSISTENCE =====================
var _LS_IMPORTED_KEY = 'materialism_imported_datasets';

function _saveImportedDatasets() {{
    var toSave = {{}};
    Object.keys(DATASETS).forEach(function(k) {{
        if (DATASETS[k]._imported) toSave[k] = DATASETS[k];
    }});
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
            if (!DATASETS[k]) {{ DATASETS[k] = saved[k]; DATASETS[k]._imported = true; }}
        }});
    }} catch(e) {{}}
}}

// ===================== PUBCHEM + CAS LOOKUP =====================
function _delay(ms) {{ return new Promise(function(r) {{ setTimeout(r, ms); }}); }}

function _pubchemLookup(query, isCAS) {{
    var encoded = encodeURIComponent(query);
    var propUrl = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/' + encoded + '/property/MolecularWeight,MolecularFormula,CanonicalSMILES,IUPACName/JSON';
    return fetch(propUrl).then(function(r) {{ if (!r.ok) return null; return r.json(); }}).then(function(data) {{
        if (!data || !data.PropertyTable || !data.PropertyTable.Properties || !data.PropertyTable.Properties[0]) return null;
        var p = data.PropertyTable.Properties[0];
        var result = {{ mw: p.MolecularWeight || null, formula: p.MolecularFormula || '', smiles: p.CanonicalSMILES || '', iupac: p.IUPACName || '', cid: p.CID || null, source: 'PubChem', url: p.CID ? 'https://pubchem.ncbi.nlm.nih.gov/compound/' + p.CID : '' }};
        if (result.cid && !isCAS) {{
            return _delay(150).then(function() {{
                return fetch('https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/' + result.cid + '/synonyms/JSON');
            }}).then(function(r2) {{
                if (!r2.ok) return result;
                return r2.json().then(function(synData) {{
                    var syns = (synData.InformationList && synData.InformationList.Information && synData.InformationList.Information[0] && synData.InformationList.Information[0].Synonym) || [];
                    for (var i = 0; i < syns.length; i++) {{ if (/^\d{{2,7}}-\d{{2}}-\d$/.test(syns[i])) {{ result.cas = syns[i]; break; }} }}
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
        .then(function(data) {{ if (!data || !data.results || data.results.length === 0) return null; return data.results[0].rn; }})
        .catch(function() {{ return null; }});
}}

function _casChemDetail(casRn) {{
    return fetch('https://commonchemistry.cas.org/api/detail?cas_rn=' + encodeURIComponent(casRn))
        .then(function(r) {{ if (!r.ok) return null; return r.json(); }})
        .then(function(d) {{
            if (!d) return null;
            var nm = (d.name || '').replace(/<[^>]*>/g, '');
            var mwStr = (d.molecularMass || '').replace(/[^\d.]/g, '');
            return {{ name: nm, cas: d.rn || casRn, mw: mwStr ? parseFloat(mwStr) : null, formula: (d.molecularFormula || '').replace(/<[^>]*>/g, ''), smiles: d.smile || '', source: 'CAS Common Chemistry', url: 'https://commonchemistry.cas.org/detail?cas_rn=' + encodeURIComponent(casRn) }};
        }}).catch(function() {{ return null; }});
}}

function _mwClose(a, b) {{ if (a == null || b == null) return false; return Math.abs(a - b) / Math.max(a, b) < 0.01; }}

function _pubchemBP(cid) {{
    if (!cid) return Promise.resolve(null);
    var url = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/' + cid + '/JSON?heading=Boiling+Point';
    return fetch(url).then(function(r) {{ if (!r.ok) return null; return r.json(); }}).then(function(data) {{
        if (!data || !data.Record || !data.Record.Section) return null;
        var sections = data.Record.Section;
        for (var i = 0; i < sections.length; i++) {{
            var sub = sections[i].Section; if (!sub) continue;
            for (var j = 0; j < sub.length; j++) {{
                var info = sub[j].Information; if (!info) continue;
                for (var k = 0; k < info.length; k++) {{
                    var val = info[k].Value; if (!val) continue;
                    if (val.StringWithMarkup && val.StringWithMarkup[0]) {{
                        var s = val.StringWithMarkup[0].String || '';
                        var m = s.match(/([-]?[\d.]+)\s*[°]?\s*C/i);
                        if (m) return parseFloat(m[1]);
                        m = s.match(/^([-]?[\d.]+)$/);
                        if (m && val.Unit && val.Unit.toLowerCase().indexOf('c') !== -1) return parseFloat(m[1]);
                    }}
                    if (val.Number && val.Number.length > 0) {{
                        var unit = (val.Unit || '').toLowerCase();
                        if (unit.indexOf('c') !== -1 || unit === 'deg c' || unit === '\u00b0c') return val.Number[0];
                    }}
                }}
            }}
        }}
        return null;
    }}).catch(function() {{ return null; }});
}}

// ===================== CATEGORIZE SOLVENT =====================
function _categorizeSolvent(smiles, name) {{
    var s = (smiles || '').trim();
    var n = (name || '').toLowerCase().trim();
    if (s === 'O' || n === 'water') return 'Water';
    if (/C\(=O\)O[^C\(]|C\(=O\)O$/.test(s) || /\bac(id|etic|rylic)\b|\bformic\b/.test(n)) return 'Acid';
    if (/C\(=O\)N/.test(s) || /\b(dmf|dma|nmp|dmac|formamide|acetamide|pyrrolidone)\b/.test(n)) return 'Amide';
    if (/C#N/.test(s) || /nitrile|\bacn\b|acetonitrile|\bcyanide\b/.test(n)) return 'Nitrile';
    if (/S\(=O\)/.test(s) || /\b(dmso|sulfo|sulfoxide|sulfone|sulfolane)\b/.test(n)) return 'Sulfoxide/Sulfone';
    var ohCount = 0;
    if (s) {{ var stripped = s.replace(/C\(=O\)/g, ''); ohCount = (stripped.match(/O/g) || []).length; }}
    if (ohCount >= 2) return 'Glycol/Polyol';
    if (/C\(=O\)O[C]/.test(s) || /\b(acetate|ester|acrylate|butyrate|propionate)\b/.test(n)) return 'Ester';
    if (/C\(=O\)[^ONS]/.test(s) || /\b(ketone|acetone|mek|mibk|cyclohexanone)\b/.test(n)) return 'Ketone';
    if (/C=O/.test(s) && !/C\(=O\)/.test(s)) return 'Aldehyde';
    if (ohCount === 1) return 'Alcohol';
    if (/c1ccccc1|c1ccncc1|c1ccoc1|c1ccsc1/.test(s) || /\b(benzene|toluene|xylene|styrene|naphthalene|pyridine|furan|thiophene|phenyl)\b/.test(n)) return 'Aromatic';
    if (/Cl|Br|F(?=[^e])/.test(s) || /\b(chlor|dichlor|trichlor|tetrachlor|fluor|brom|freon|perc)\b/.test(n)) return 'Halogenated';
    if (s.indexOf('O') > -1 && ohCount === 0) return 'Ether';
    if (/^[CC()\d]+$/.test(s.replace(/[()]/g,'')) || /\b(hexane|heptane|octane|pentane|cyclohexane|decane|alkane|paraffin|naphtha)\b/.test(n)) return 'Hydrocarbon';
    return '';
}}

// ===================== INFER MISSING =====================
var _inferRunning = false;
var _inferCancelled = false;

async function inferMissing(dsId) {{
    if (_inferRunning) return;
    _inferRunning = true;
    _inferCancelled = false;
    var progEl = document.getElementById('infer-progress');
    if (progEl) {{ progEl.style.display = 'block'; progEl.innerHTML = '<div class="loading" style="padding:8px">Starting inference...</div>'; }}
    var btn = document.getElementById('solvent-infer-btn');
    if (btn) btn.disabled = true;
    var ds = DATASETS[dsId];
    var isSolvents = !!(ds.chemicals && ds.chemicals.length > 0);
    var items = isSolvents ? ds.chemicals : (ds.polymers || []);
    var fillable = isSolvents ? ['cas','mw','smiles','bp','cat'] : ['cas','mw','smiles'];
    var queue = [];
    var hasRowSel = Object.keys(_mSelRows).length > 0;
    // Cell-level selection (for targeted field inference when no row selection)
    var selFieldsByRow = {{}};
    if (!hasRowSel) {{
        Object.keys(_mSelCells).forEach(function(k) {{
            var parts = k.split(':'); selFieldsByRow[parts[0]] = selFieldsByRow[parts[0]] || {{}};
            selFieldsByRow[parts[0]][parts[1]] = true;
        }});
    }}
    var hasCellSel = Object.keys(selFieldsByRow).length > 0;
    items.forEach(function(item, idx) {{
        // Row selection: process only selected rows, all fillable fields
        if (hasRowSel) {{ if (!_mSelRows[String(idx)]) return; }}
        // Cell selection: process only rows with selected cells, only selected fields
        else if (hasCellSel) {{ if (!selFieldsByRow[String(idx)]) return; }}
        var rowFields = (!hasRowSel && hasCellSel) ? selFieldsByRow[String(idx)] : null;
        var fieldsToCheck = rowFields ? fillable.filter(function(f) {{ return rowFields[f]; }}) : fillable;
        var missing = fieldsToCheck.filter(function(f) {{ var v = item[f]; return v == null || v === '' || v === 0; }});
        if (missing.length > 0) queue.push({{ item: item, idx: idx, missing: missing }});
    }});
    if (queue.length === 0) {{
        _inferRunning = false;
        var bar = document.getElementById('infer-progress');
        if (bar) bar.innerHTML = '<span style="color:#27ae60;font-size:0.82rem">All fields already populated.</span>';
        return;
    }}
    var filled = 0, errors = 0;
    function _showStep(itemName, itemNum, total, stepText) {{
        var bar = document.getElementById('infer-progress');
        if (!bar) return;
        var pct = Math.round(100 * itemNum / total);
        var h = '<div style="font-size:0.82rem;color:#2d3436;font-weight:600;margin-bottom:4px">Processing <b>' + (itemName||'').substring(0,45) + '</b> (' + itemNum + '/' + total + ')</div>';
        h += '<div class="bar-bg"><div class="bar-fg" style="width:' + pct + '%"></div></div>';
        h += '<div class="infer-step-log" id="infer-step-log"><div class="infer-step active"><span class="step-icon">&#8987;</span> ' + stepText + '</div></div>';
        h += '<div style="display:flex;align-items:center;gap:10px;margin-top:6px"><button class="import-btn secondary" style="width:auto;padding:2px 10px;font-size:0.72rem" onclick="_inferCancelled=true">Cancel</button>';
        h += '<span style="font-size:0.72rem;color:#b2bec3">' + filled + ' values filled</span></div>';
        bar.innerHTML = h;
    }}
    function _setStep(itemName, itemNum, total, stepText, prevOk) {{
        var log = document.getElementById('infer-step-log');
        if (log) {{
            var active = log.querySelector('.infer-step.active');
            if (active) {{ active.classList.remove('active'); active.classList.add(prevOk ? 'ok' : 'warn'); active.querySelector('.step-icon').innerHTML = prevOk ? '&#10003;' : '&#10007;'; }}
            var div = document.createElement('div'); div.className = 'infer-step active';
            div.innerHTML = '<span class="step-icon">&#8987;</span> ' + stepText; log.appendChild(div);
        }} else _showStep(itemName, itemNum, total, stepText);
    }}

    for (var i = 0; i < queue.length; i++) {{
        if (_inferCancelled) break;
        var entry = queue[i];
        var item = entry.item;
        var _iName = (item.name || item.cas || 'Item ' + (i+1));
        if (!item._src) item._src = {{}};
        _showStep(_iName, i+1, queue.length, 'Searching PubChem...');
        try {{
            var pub = null, lookupByCAS = false;
            if (item.cas && item.cas.length > 3) {{ pub = await _pubchemLookup(item.cas, true); if (pub) lookupByCAS = true; }}
            if (!pub && item.name) {{ _setStep(_iName, i+1, queue.length, 'Retrying by name...', false); await _delay(200); pub = await _pubchemLookup(item.name, false); }}
            _setStep(_iName, i+1, queue.length, 'Searching CAS...', !!pub);
            var casChem = null, casRnToLookup = item.cas || (pub && pub.cas);
            if (casRnToLookup) {{ await _delay(200); casChem = await _casChemDetail(casRnToLookup); }}
            else if (item.name && !pub) {{ await _delay(200); var foundCas = await _casChemSearch(item.name); if (foundCas) {{ await _delay(200); casChem = await _casChemDetail(foundCas); }} }}
            var bpVal = null;
            if (entry.missing.indexOf('bp') !== -1 && pub && pub.cid) {{
                _setStep(_iName, i+1, queue.length, 'Looking up BP...', !!casChem);
                await _delay(200); bpVal = await _pubchemBP(pub.cid);
            }}
            _setStep(_iName, i+1, queue.length, 'Filling values...', true);
            entry.missing.forEach(function(field) {{
                if (field === 'cat') {{
                    var smi = item.smiles || (pub && pub.smiles) || '';
                    var cat = _categorizeSolvent(smi, item.name || '');
                    if (cat) {{ item.cat = cat; item._src.cat = {{ label: 'Auto-classified', url: '', uncertain: false }}; }}
                    else {{ item.cat = 'Unknown'; item._src.cat = {{ label: 'Could not classify', url: '', uncertain: true, isNote: true }}; }}
                    filled++; return;
                }}
                if (field === 'bp') {{
                    if (bpVal != null) {{ item.bp = Math.round(bpVal * 10) / 10; item._src.bp = {{ label: 'PubChem (experimental)', url: (pub && pub.url) || '', uncertain: false }}; }}
                    else {{ item.bp = 'Not found'; item._src.bp = {{ label: 'No BP data', url: '', uncertain: true, isNote: true }}; }}
                    filled++; return;
                }}
                var pubVal = null, casVal = null, pubUrl = '', casUrl = '';
                if (pub) {{ pubUrl = pub.url || ''; if (field === 'cas') pubVal = pub.cas; else if (field === 'mw') pubVal = pub.mw; else if (field === 'smiles') pubVal = pub.smiles; }}
                if (casChem) {{ casUrl = casChem.url || ''; if (field === 'cas') casVal = casChem.cas; else if (field === 'mw') casVal = casChem.mw; else if (field === 'smiles') casVal = casChem.smiles; }}
                var val = null, uncertain = false, srcLabel = '', srcUrl = '';
                if (pubVal && casVal) {{ var match = (field === 'mw') ? _mwClose(pubVal, casVal) : (String(pubVal) === String(casVal)); if (match) {{ val = pubVal; srcLabel = 'PubChem + CAS'; srcUrl = pubUrl; }} else {{ val = pubVal; srcLabel = 'PubChem (CAS disagrees)'; srcUrl = pubUrl; uncertain = true; }} }}
                else if (pubVal) {{ val = pubVal; srcLabel = 'PubChem'; srcUrl = pubUrl; if (!lookupByCAS) uncertain = true; }}
                else if (casVal) {{ val = casVal; srcLabel = 'CAS'; srcUrl = casUrl; if (!lookupByCAS) uncertain = true; }}
                if (val) {{ item[field] = val; item._src[field] = {{ label: srcLabel, url: srcUrl, uncertain: uncertain }}; }}
                else {{ item[field] = 'Not found'; item._src[field] = {{ label: 'Not found', url: '', uncertain: true, isNote: true }}; }}
                filled++;
            }});
        }} catch(e) {{ errors++; }}
        await _delay(250);
    }}
    _inferRunning = false;
    _saveImportedDatasets();
    var bar2 = document.getElementById('infer-progress');
    if (bar2) bar2.innerHTML = '<span style="color:#27ae60;font-size:0.82rem">Done! Filled <b>' + filled + '</b> values.' + (errors > 0 ? ' (' + errors + ' errors)' : '') + '</span>';
    renderContent();
}}

// ===================== POLYMER INFER (Trade Name Resolution) =====================

// Step T1 — detect whether a name is a trade/product name
var _KNOWN_BRANDS = ['Viton','Sylgard','Kraton','Elvax','Cellit','Ultem','Delrin','Udel','Nylon',
    'Kynar','Kevlar','Teflon','Hytrel','Santoprene','Pebax','Engage','Nordel','Versify',
    'Affinity','Exact','Surlyn','Nucrel','Bynel','Elvaloy','Vamac','Kalrez','Chemraz',
    'Tecnoflon','Fluorel','Dyneon','Solef','Hylar','Kynar','Neoprene','Buna','Thiokol',
    'Perbunan','Nitroflex','Urethane','Estane','Pellethane','Texin','Desmopan','Elastollan',
    'Covestro','Bayflex','Vulkollan','Adiprene','Vibrathane','Andur','Irogran','Avalon',
    'Isoplast','Makrolon','Lexan','Calibre','Cycoloy','Xenoy','Valox','Celanex','Rynite',
    'Dacron','Mylar','Melinex','Arnitel','Hytrel','Lomod','Riteflex','Ecdel','Tritan',
    'Eastman','Tenite','Durastar','PETG','PET','ABS','SBS','SEBS','TPU','TPE','TPV'];
var _IUPAC_TERMS = ['yl','ene','ane','ol','one','oate','ate','amine','ether','ester',
    'oxide','acid','nitrile','aldehyde','ketone','phenyl','methyl','ethyl','propyl',
    'butyl','vinyl','acrylic','styrene','urethane','siloxane'];

function _detectNameType(name, cas) {{
    if (!name) return 'unknown';
    var n = name.trim();
    // Has CAS and short clean name → chemical
    if (cas && cas.length > 3 && !/\d{{3,}}/.test(n)) return 'chemical_name';
    // Known brand prefix
    if (_KNOWN_BRANDS.some(function(b) {{ return n.toLowerCase().startsWith(b.toLowerCase()); }})) return 'trade_name';
    // Pattern: Word + alphanumeric grade code (e.g. "Kraton G1652", "Viton A", "Sylgard 184")
    if (/^[A-Z][a-zA-Z]+[\s-][A-Z0-9]/.test(n) && !/\(/.test(n)) return 'trade_name';
    // All-caps abbreviation likely to be trade or acronym
    if (/^[A-Z]{{3,}}$/.test(n)) return 'ambiguous';
    // Has IUPAC terms → chemical
    var nl = n.toLowerCase();
    if (_IUPAC_TERMS.some(function(t) {{ return nl.indexOf(t) !== -1; }})) return 'chemical_name';
    // Has a number that looks like a grade code (not a locant like 2-butanol)
    if (/\b\d{{2,}}\b/.test(n) && !/\d-[A-Za-z]/.test(n)) return 'trade_name';
    return 'ambiguous';
}}

// EPA CompTox Dashboard public API search
async function _comptoxSearch(name) {{
    try {{
        var url = 'https://comptox.epa.gov/dashboard/api/search/exactsearch?word=' + encodeURIComponent(name);
        var r = await fetch(url, {{ signal: AbortSignal.timeout(6000) }});
        if (!r.ok) return null;
        var data = await r.json();
        if (Array.isArray(data) && data.length > 0) {{
            var d = data[0];
            return {{ cas: d.casrn || null, name: d.preferredName || d.iupacName || null, url: 'https://comptox.epa.gov/dashboard/dsstoxdb/results?search=' + encodeURIComponent(name) }};
        }}
    }} catch(e) {{}}
    return null;
}}

// Shared progress helpers for inferPolymer
function _showPolyStep(itemName, itemNum, total, stepText) {{
    var bar = document.getElementById('infer-progress');
    if (!bar) return;
    var pct = Math.round(100 * itemNum / total);
    var h = '<div style="font-size:0.82rem;color:#2d3436;font-weight:600;margin-bottom:4px">Processing <b>' + (itemName||'').substring(0,45) + '</b> (' + itemNum + '/' + total + ')</div>';
    h += '<div class="bar-bg"><div class="bar-fg" style="width:' + pct + '%"></div></div>';
    h += '<div class="infer-step-log" id="poly-step-log"><div class="infer-step active"><span class="step-icon">&#8987;</span> ' + stepText + '</div></div>';
    h += '<div style="display:flex;align-items:center;gap:10px;margin-top:6px"><button class="import-btn secondary" style="width:auto;padding:2px 10px;font-size:0.72rem" onclick="_inferCancelled=true">Cancel</button></div>';
    bar.innerHTML = h;
}}
function _setPolyStep(itemName, itemNum, total, stepText, prevOk) {{
    var log = document.getElementById('poly-step-log');
    if (log) {{
        var active = log.querySelector('.infer-step.active');
        if (active) {{ active.classList.remove('active'); active.classList.add(prevOk ? 'ok' : 'warn'); active.querySelector('.step-icon').innerHTML = prevOk ? '&#10003;' : '&#10007;'; }}
        var div = document.createElement('div'); div.className = 'infer-step active';
        div.innerHTML = '<span class="step-icon">&#8987;</span> ' + stepText; log.appendChild(div);
    }} else _showPolyStep(itemName, itemNum, total, stepText);
}}
function _appendManualLinks(name, links) {{
    var log = document.getElementById('poly-step-log');
    if (!log) return;
    var div = document.createElement('div');
    div.className = 'infer-step';
    div.style.cssText = 'font-size:0.75rem;margin-top:4px;color:#636e72';
    div.innerHTML = 'Manual lookup: ' + links.map(function(l) {{
        return '<a href="' + l.url + '" target="_blank" rel="noopener" style="color:#0984e3;margin-right:8px">' + l.label + ' \u2197</a>';
    }}).join('');
    log.appendChild(div);
}}

async function inferPolymer(dsId) {{
    if (_inferRunning) return;
    _inferRunning = true;
    _inferCancelled = false;
    var progEl = document.getElementById('infer-progress');
    if (progEl) {{ progEl.style.display = 'block'; progEl.innerHTML = '<div class="loading" style="padding:8px">Starting trade name resolution...</div>'; }}
    var polyBtn = document.getElementById('poly-infer-btn');
    if (polyBtn) polyBtn.disabled = true;

    var ds = DATASETS[dsId];
    var isSolvents = !!(ds.chemicals && ds.chemicals.length > 0);
    var items = isSolvents ? ds.chemicals : (ds.polymers || []);

    var hasRowSel = Object.keys(_mSelRows).length > 0;
    var queue = [];
    items.forEach(function(item, idx) {{
        if (hasRowSel && !_mSelRows[String(idx)]) return;
        queue.push({{ item: item, idx: idx }});
    }});

    if (queue.length === 0) {{
        _inferRunning = false;
        if (progEl) progEl.innerHTML = '<span style="color:#27ae60;font-size:0.82rem">No rows to process.</span>';
        renderContent();
        return;
    }}

    var resolved = 0, errors = 0;
    for (var i = 0; i < queue.length; i++) {{
        if (_inferCancelled) break;
        var entry = queue[i];
        var item = entry.item;
        var name = item.name || '';
        if (!item._src) item._src = {{}};

        _showPolyStep(name, i+1, queue.length, 'Detecting name type...');
        var nameType = _detectNameType(name, item.cas);
        item._nameType = nameType;

        var results = {{}};

        // Source 1: PubChem name/synonym lookup
        _setPolyStep(name, i+1, queue.length, 'PubChem synonym search...', true);
        try {{
            await _delay(200);
            var pub = await _pubchemLookup(name, false);
            if (pub) results.pubchem = pub;
        }} catch(e) {{ errors++; }}

        // Source 2: CAS Common Chemistry
        if (!results.pubchem || !results.pubchem.cas) {{
            _setPolyStep(name, i+1, queue.length, 'CAS Common Chemistry search...', !!results.pubchem);
            try {{
                await _delay(200);
                var casRn = await _casChemSearch(name);
                if (casRn) {{
                    await _delay(200);
                    var casDetail = await _casChemDetail(casRn);
                    if (casDetail) results.cas_chem = casDetail;
                }}
            }} catch(e) {{ errors++; }}
        }}

        // Source 3: EPA CompTox
        _setPolyStep(name, i+1, queue.length, 'EPA CompTox search...', !!(results.pubchem || results.cas_chem));
        try {{
            await _delay(200);
            var comptox = await _comptoxSearch(name);
            if (comptox) results.comptox = comptox;
        }} catch(e) {{}}

        // Step T3 — consolidate
        _setPolyStep(name, i+1, queue.length, 'Consolidating results...', true);
        var resolvedCas = null, resolvedSmiles = null, resolvedMw = null, srcLabel = '', srcUrl = '', confidence = 0;

        if (results.pubchem && results.cas_chem) {{
            var pubCas = results.pubchem.cas, casCas = results.cas_chem.cas;
            if (pubCas && casCas && pubCas === casCas) {{
                resolvedCas = pubCas; srcLabel = 'PubChem + CAS Common Chemistry'; srcUrl = results.pubchem.url; confidence = 0.95;
            }} else if (pubCas) {{
                resolvedCas = pubCas; srcLabel = 'PubChem (CAS disagrees)'; srcUrl = results.pubchem.url; confidence = 0.70;
            }} else if (casCas) {{
                resolvedCas = casCas; srcLabel = 'CAS Common Chemistry'; srcUrl = results.cas_chem.url; confidence = 0.70;
            }}
        }} else if (results.pubchem && results.pubchem.cas) {{
            resolvedCas = results.pubchem.cas; srcLabel = 'PubChem'; srcUrl = results.pubchem.url || ''; confidence = 0.75;
            resolvedSmiles = results.pubchem.smiles; resolvedMw = results.pubchem.mw;
        }} else if (results.cas_chem && results.cas_chem.cas) {{
            resolvedCas = results.cas_chem.cas; srcLabel = 'CAS Common Chemistry'; srcUrl = results.cas_chem.url || ''; confidence = 0.70;
        }} else if (results.comptox && results.comptox.cas) {{
            resolvedCas = results.comptox.cas; srcLabel = 'EPA CompTox'; srcUrl = results.comptox.url || ''; confidence = 0.60;
        }}

        // Apply resolved values
        var uncertain = confidence < 0.80;
        if (resolvedCas && !item.cas) {{
            item.cas = resolvedCas;
            item._src.cas = {{ label: srcLabel, url: srcUrl, uncertain: uncertain }};
            resolved++;
        }}
        if (resolvedSmiles && !item.smiles) {{
            item.smiles = resolvedSmiles;
            item._src.smiles = {{ label: srcLabel, url: srcUrl, uncertain: false }};
        }}
        if (resolvedMw && !item.mw) {{
            item.mw = resolvedMw;
            item._src.mw = {{ label: srcLabel, url: srcUrl, uncertain: false }};
        }}

        // Step T4 — confidence score
        item._tradeResScore = confidence;

        var enc = encodeURIComponent(name);
        if (resolvedCas) {{
            _setPolyStep(name, i+1, queue.length, 'Resolved \u2192 CAS ' + resolvedCas + ' (' + Math.round(confidence*100) + '% confidence via ' + srcLabel + ')', true);
        }} else {{
            _setPolyStep(name, i+1, queue.length, 'Not resolved automatically \u2014 manual lookup links below', false);
            _appendManualLinks(name, [
                {{ label: 'SpecialChem', url: 'https://polymer.specialchem.com/tradename/' + enc }},
                {{ label: 'Sigma-Aldrich', url: 'https://www.sigmaaldrich.com/US/en/search#' + enc + '?focus=products' }},
                {{ label: 'EPA CompTox', url: 'https://comptox.epa.gov/dashboard/search?search=' + enc }},
                {{ label: 'ECHA', url: 'https://echa.europa.eu/search-for-chemicals?p_p_id=disssubstancesearch_WAR_disssubstances&_disssubstancesearch_WAR_disssubstances_searchop=search&_disssubstancesearch_WAR_disssubstances_trade_name=' + enc }},
            ]);
        }}

        await _delay(300);
    }}

    _inferRunning = false;
    _saveImportedDatasets();
    var bar2 = document.getElementById('infer-progress');
    if (bar2) bar2.innerHTML = '<span style="color:#27ae60;font-size:0.82rem">Done! Resolved <b>' + resolved + '</b> of <b>' + queue.length + '</b> identities.' + (errors > 0 ? ' (' + errors + ' lookup errors)' : '') + '</span>';
    renderContent();
}}

// ===================== INFER ACTIVE DB =====================
async function inferActiveDb() {{
    if (_inferRunning) return;
    _inferRunning = true;
    _inferCancelled = false;
    var progEl = document.getElementById('infer-progress');
    if (progEl) {{ progEl.style.display = 'block'; progEl.innerHTML = '<div class="loading" style="padding:8px">Starting inference...</div>'; }}
    var btn = document.getElementById('db-infer-btn');
    if (btn) btn.disabled = true;
    var data = _activeDbTab === 'solvents' ? SOLVENTS : POLYMERS;
    var isSolvents = _activeDbTab === 'solvents';
    var fillable = isSolvents ? ['cas','mw','smiles','bp','cat'] : ['cas'];
    var queue = [];
    // Parse cell selection into per-row field sets
    var selFieldsByRow = {{}};
    Object.keys(_selCells).forEach(function(k) {{
        var parts = k.split(':'); selFieldsByRow[parts[0]] = selFieldsByRow[parts[0]] || {{}};
        selFieldsByRow[parts[0]][parts[1]] = true;
    }});
    var hasSelection = Object.keys(selFieldsByRow).length > 0;
    // Build queue from visible, active items
    for (var i = 0; i < data.length; i++) {{
        if (!_isDsActive(data[i].dsId)) continue;
        if (hasSelection && !selFieldsByRow[String(i)]) continue;
        var rowFields = hasSelection ? selFieldsByRow[String(i)] : null;
        var fieldsToCheck = rowFields ? fillable.filter(function(f) {{ return rowFields[f]; }}) : fillable;
        var missing = fieldsToCheck.filter(function(f) {{
            var v = getDbVal(_activeDbTab, i, f);
            return v == null || v === '' || v === 0;
        }});
        if (missing.length > 0) queue.push({{ idx: i, item: data[i], missing: missing }});
    }}
    if (queue.length === 0) {{
        _inferRunning = false;
        if (progEl) progEl.innerHTML = '<span style="color:#27ae60;font-size:0.82rem">All fields already populated.</span>';
        if (btn) btn.disabled = false;
        return;
    }}
    var filled = 0, errors = 0;
    function _showStep(itemName, itemNum, total, stepText) {{
        var bar = document.getElementById('infer-progress');
        if (!bar) return;
        var pct = Math.round(100 * itemNum / total);
        var h = '<div style="font-size:0.82rem;color:#2d3436;font-weight:600;margin-bottom:4px">Processing <b>' + (itemName||'').substring(0,45) + '</b> (' + itemNum + '/' + total + ')</div>';
        h += '<div class="bar-bg"><div class="bar-fg" style="width:' + pct + '%"></div></div>';
        h += '<div class="infer-step-log" id="infer-step-log"><div class="infer-step active"><span class="step-icon">&#8987;</span> ' + stepText + '</div></div>';
        h += '<div style="display:flex;align-items:center;gap:10px;margin-top:6px"><button class="import-btn secondary" style="width:auto;padding:2px 10px;font-size:0.72rem" onclick="_inferCancelled=true">Cancel</button>';
        h += '<span style="font-size:0.72rem;color:#b2bec3">' + filled + ' values filled</span></div>';
        bar.innerHTML = h;
    }}
    function _setStep(itemName, itemNum, total, stepText, prevOk) {{
        var log = document.getElementById('infer-step-log');
        if (log) {{
            var active = log.querySelector('.infer-step.active');
            if (active) {{ active.classList.remove('active'); active.classList.add(prevOk ? 'ok' : 'warn'); active.querySelector('.step-icon').innerHTML = prevOk ? '&#10003;' : '&#10007;'; }}
            var div = document.createElement('div'); div.className = 'infer-step active';
            div.innerHTML = '<span class="step-icon">&#8987;</span> ' + stepText; log.appendChild(div);
        }} else _showStep(itemName, itemNum, total, stepText);
    }}

    for (var qi = 0; qi < queue.length; qi++) {{
        if (_inferCancelled) break;
        var entry = queue[qi];
        var item = entry.item;
        var itemIdx = entry.idx;
        var _iName = (item.name || item.cas || 'Item ' + (qi+1));
        _showStep(_iName, qi+1, queue.length, 'Searching PubChem...');
        try {{
            var pub = null, lookupByCAS = false;
            var curCas = getDbVal(_activeDbTab, itemIdx, 'cas');
            var curName = getDbVal(_activeDbTab, itemIdx, 'name');
            if (curCas && curCas.length > 3) {{ pub = await _pubchemLookup(curCas, true); if (pub) lookupByCAS = true; }}
            if (!pub && curName) {{ _setStep(_iName, qi+1, queue.length, 'Retrying by name...', false); await _delay(200); pub = await _pubchemLookup(curName, false); }}
            _setStep(_iName, qi+1, queue.length, 'Searching CAS...', !!pub);
            var casChem = null, casRnToLookup = curCas || (pub && pub.cas);
            if (casRnToLookup) {{ await _delay(200); casChem = await _casChemDetail(casRnToLookup); }}
            else if (curName && !pub) {{ await _delay(200); var foundCas = await _casChemSearch(curName); if (foundCas) {{ await _delay(200); casChem = await _casChemDetail(foundCas); }} }}
            var bpVal = null;
            if (entry.missing.indexOf('bp') !== -1 && pub && pub.cid) {{
                _setStep(_iName, qi+1, queue.length, 'Looking up BP...', !!casChem);
                await _delay(200); bpVal = await _pubchemBP(pub.cid);
            }}
            _setStep(_iName, qi+1, queue.length, 'Filling values...', true);
            entry.missing.forEach(function(field) {{
                var val = null;
                if (field === 'cat' && isSolvents) {{
                    var smi = getDbVal(_activeDbTab, itemIdx, 'smiles') || (pub && pub.smiles) || '';
                    val = _categorizeSolvent(smi, curName || '');
                    if (!val) val = 'other';
                }} else if (field === 'bp') {{
                    if (bpVal != null) val = Math.round(bpVal * 10) / 10;
                    else val = 'Not found';
                }} else {{
                    var pubVal = null, casVal = null;
                    if (pub) {{ if (field === 'cas') pubVal = pub.cas; else if (field === 'mw') pubVal = pub.mw; else if (field === 'smiles') pubVal = pub.smiles; }}
                    if (casChem) {{ if (field === 'cas') casVal = casChem.cas; else if (field === 'mw') casVal = casChem.mw; else if (field === 'smiles') casVal = casChem.smiles; }}
                    if (pubVal && casVal) {{
                        var match = (field === 'mw') ? _mwClose(pubVal, casVal) : (String(pubVal) === String(casVal));
                        val = match ? pubVal : pubVal;
                    }} else if (pubVal) {{ val = pubVal; }}
                    else if (casVal) {{ val = casVal; }}
                    else {{ val = 'Not found'; }}
                }}
                if (val != null) {{
                    setDbVal(_activeDbTab, itemIdx, field, String(val));
                    filled++;
                }}
            }});
        }} catch(e) {{ errors++; }}
        await _delay(250);
    }}
    _inferRunning = false;
    var bar2 = document.getElementById('infer-progress');
    if (bar2) bar2.innerHTML = '<span style="color:#27ae60;font-size:0.82rem">Done! Filled <b>' + filled + '</b> values.' + (errors > 0 ? ' (' + errors + ' errors)' : '') + '</span>';
    if (btn) btn.disabled = false;
    renderContent();
}}

// ===================== EXPORT =====================
function triggerRebuild() {{
    _viewMode = '_import';
    buildSidebar();
    var ct = document.getElementById('content');
    var dsKeys = Object.keys(DATASETS);
    if (dsKeys.length === 0) {{ ct.innerHTML = '<div class="detail-content"><div class="analysis-card"><h3>Nothing to Export</h3></div></div>'; return; }}
    var h = '<div class="detail-content"><div class="analysis-card"><h3>Export Datasets</h3><p>Download CSV files:</p>';
    dsKeys.forEach(function(k) {{
        var ds = DATASETS[k]; var nc = (ds.chemicals || []).length; var np = (ds.polymers || []).length;
        h += '<div style="margin:6px 0"><b>' + (ds.meta && ds.meta.name || k) + '</b> (' + nc + 'c, ' + np + 'p) ';
        if (nc > 0) h += '<button class="import-btn secondary" style="width:auto;padding:2px 10px;font-size:0.75rem" onclick="exportCSV(\\x27' + k + '\\x27,\\x27chemicals\\x27)">Chemicals CSV</button> ';
        if (np > 0) h += '<button class="import-btn secondary" style="width:auto;padding:2px 10px;font-size:0.75rem" onclick="exportCSV(\\x27' + k + '\\x27,\\x27polymers\\x27)">Polymers CSV</button>';
        h += '</div>';
    }});
    h += '</div></div>';
    ct.innerHTML = h;
}}

function exportCSV(dsId, type) {{
    var ds = DATASETS[dsId]; var items = ds[type] || [];
    if (items.length === 0) return;
    var cols = type === 'chemicals' ? ['name','cas','dd','dp','dh','mw','bp','cat','smiles','density','conf'] : ['name','cas','dd','dp','dh','r','type','conf'];
    var csv = cols.join(',') + '\\n';
    items.forEach(function(r) {{
        csv += cols.map(function(c) {{ var v = r[c]; v = v == null ? '' : String(v); return v.indexOf(',') > -1 ? '"' + v + '"' : v; }}).join(',') + '\\n';
    }});
    var blob = new Blob([csv], {{ type: 'text/csv' }});
    var a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = dsId + '_' + type + '.csv'; a.click();
}}

{_db_csv_import_js}

// ===================== INIT =====================
// Mark embedded datasets
Object.keys(DATASETS).forEach(function(k) {{ DATASETS[k]._embedded = true; }});
// Remove deleted datasets
(function() {{
    try {{
        var raw = localStorage.getItem('materialism_deleted_datasets');
        if (!raw) return;
        var deleted = JSON.parse(raw);
        if (!Array.isArray(deleted)) return;
        deleted.forEach(function(k) {{ delete DATASETS[k]; }});
    }} catch(e) {{}}
}})();
_loadImportedDatasets();
loadDbEdits();
buildSidebar();
renderContent();

// ---- Structure image tooltip ----
var _dbStructCache = {{}};
var _dbTooltip = {{ el: null, img: null, nameEl: null }};
function showStructure(event, encodedName) {{
    var name = decodeURIComponent(encodedName);
    if (!_dbTooltip.el) {{
        _dbTooltip.el = document.getElementById('db-struct-tooltip');
        _dbTooltip.img = document.getElementById('db-struct-img');
        _dbTooltip.nameEl = document.getElementById('db-struct-name');
    }}
    _dbTooltip.nameEl.textContent = name;
    _dbTooltip.el.style.display = 'block';
    var x = event.clientX + 15, y = event.clientY - 110;
    if (x + 220 > window.innerWidth) x = event.clientX - 225;
    if (y < 8) y = event.clientY + 20;
    _dbTooltip.el.style.left = x + 'px'; _dbTooltip.el.style.top = y + 'px';
    if (_dbStructCache[name] === 'error') {{ _dbTooltip.el.style.display = 'none'; return; }}
    var mat = (_solventMap && _solventMap.get) ? _solventMap.get(name) : null;
    if (!mat) {{ var arr = SOLVENTS.concat(POLYMERS); for (var i=0;i<arr.length;i++) {{ if (arr[i].name===name) {{ mat=arr[i]; break; }} }} }}
    var cas = mat && mat.cas;
    var smiles = mat && mat.smiles;
    var url = cas ? 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/' + encodeURIComponent(cas) + '/PNG?image_size=200x200'
                  : (smiles ? 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/' + encodeURIComponent(smiles) + '/PNG?image_size=200x200'
                            : 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/' + encodeURIComponent(name) + '/PNG?image_size=200x200');
    if (_dbStructCache[name]) {{
        _dbTooltip.img.src = _dbStructCache[name]; _dbTooltip.el.classList.remove('loading');
    }} else {{
        _dbTooltip.el.classList.add('loading'); _dbTooltip.img.src = url;
        _dbTooltip.img.onload = function() {{ _dbStructCache[name] = url; _dbTooltip.el.classList.remove('loading'); }};
        _dbTooltip.img.onerror = function() {{ _dbStructCache[name] = 'error'; _dbTooltip.el.style.display = 'none'; }};
    }}
}}
function hideStructure() {{
    if (_dbTooltip.el) _dbTooltip.el.style.display = 'none';
}}
</script>
<div id="db-struct-tooltip" class="struct-tooltip">
    <img id="db-struct-img" src="" alt="Structure">
    <div id="db-struct-name" class="struct-name"></div>
</div>
</body>
</html>"""

# ===================== WRITE DATABASE PAGE =====================
db_output_path = os.path.join(os.path.dirname(__file__), "database.html")
with open(db_output_path, "w") as f:
    f.write(database_html)
print(f"Generated: {db_output_path}")
print(f"Database page: {len(db_solvents)} solvents, {len(db_polymers)} polymers")
ds_total_chems = sum(len(d.get("chemicals", [])) for d in per_dataset_data.values())
ds_total_polys = sum(len(d.get("polymers", [])) for d in per_dataset_data.values())
print(f"Datasets: {len(per_dataset_data)} datasets, {ds_total_chems} chemicals, {ds_total_polys} polymers")

# ===================== IMPORT PAGE =====================
import_html = generate_import_html()
import_output_path = os.path.join(os.path.dirname(__file__), "import.html")
with open(import_output_path, "w") as f:
    f.write(import_html)
print(f"Generated: {import_output_path}")
