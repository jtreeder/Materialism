#!/usr/bin/env python3
"""
pipeline_hansen_a2.py — Materialism HSP Database
=================================================
Polymer enrichment pipeline for Hansen Table A.2 (466 rows).
Source: data/processed/table_a2.csv

Applies:
  Step 0B  — OCR corrections (FIX GROUPS 1-6)
  Step 0   — Pre-classification routing
  Step 1   — Load and audit
  Step 2   — HSP plausibility flags
  Step 3   — Name resolution (knowledge table + brand map)
  Step 4   — CAS resolution (PubChem)
  Step 9   — Classification (13-class scheme)
  Step 10B — URL assignment for generic polymers (PubChem / Wikipedia)

Output: data/datasets/hansen_a2_enriched/polymers_enriched.csv
Checkpoint: data/datasets/hansen_a2_enriched/checkpoint.json

Usage:
    python3 pipeline_hansen_a2.py            # full run
    python3 pipeline_hansen_a2.py --resume   # continue from checkpoint
    python3 pipeline_hansen_a2.py --sample 50
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
SOURCE_CSV = BASE_DIR / "data" / "processed" / "table_a2.csv"
OUT_DIR    = BASE_DIR / "data" / "datasets" / "hansen_a2_enriched"
ENRICHED_CSV  = OUT_DIR / "polymers_enriched.csv"
CHECKPOINT    = OUT_DIR / "checkpoint.json"
PUBCHEM_BASE  = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

OUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Step 0B FIX GROUP 2 — Column-shift repairs ───────────────────────────────
# Key = row number (1-indexed), value = corrected record dict
COLUMN_SHIFT_FIXES = {
    238: {"polymer_name": "MAA/MA/VA 15/27.5/57.5", "dispersion": 28.50, "polar": 15.70, "hydrogen_bonding": 18.10, "interaction_radius": 21.50},
    239: {"polymer_name": "MAA/MA/VA 15/17.5/67.5", "dispersion": 25.50, "polar": 15.70, "hydrogen_bonding": 18.10, "interaction_radius": 21.50},
    369: {"polymer_name": "LDPE PERM<0.8",           "dispersion": 15.30, "polar":  5.30, "hydrogen_bonding":  2.50, "interaction_radius": 10.10},
}

# ─── Step 0B FIX GROUP 3 — Ro floating-point artifact strips ─────────────────
RO_ARTIFACT_FIXES = {
    31: 9.62,  55: 9.20,  89: 16.80, 128: 22.70,
   170: 13.70, 212: 3.90, 257: 11.60, 302: 5.40,
   346: 20.90, 382: 19.00, 426: 7.30, 459: 4.70,
   466: 3.90,
}

# ─── Step 0B FIX GROUP 4 — Word-split name corrections ───────────────────────
NAME_SPLIT_FIXES = {
    61:  "BUTVAR B 76",
    156: "PE? CR QUESTIONABLE VALUES",
    204: "PVAC",
    214: "VCVA COPOLY",
    238: "MAA/MA/VA 15/27.5/57.5",   # also in column-shift
    239: "MAA/MA/VA 15/17.5/67.5",   # also in column-shift
    269: "VAREZ 123",
    300: "ELVAX 250",
    301: "ELVAX 150",
    302: "ELVAX EOD 3602-1",
    310: "FORMVAR 7/70E PVFORMAL",
    311: "FORMVAR 15/95E",
    322: "VINYLITE AYAA PVAC",
    334: "PEO 4000 ? SAMPLES HEATED",
    339: "ESTANE X-7 ?? DIOXANE ONLY",
    387: "R Q SILICONE (0.748 DATA FIT)",
}

# ─── Step 0B FIX GROUP 5 — Double-space collapses ────────────────────────────
DOUBLE_SPACE_ROWS = {48, 56, 122}  # handled by general pass

# ─── Step 0B FIX GROUP 6 — Source document errors ────────────────────────────
SOURCE_ERROR_FIXES = {
     5:  "ARALDITE DY-025",
    35:  "LUTONAL I60",
   294:  "STYRON 440M-27 MOD PS",
   439: "LUMIFLON LF-200 (10%)",
   440: "LUMIFLON LF-200 (30%)",
   441: "LUMIFLON LF-916 (10%)",
   442: "LUMIFLON LF-916 (30%)",
}

# ─── Step 0B: Apply all OCR / source corrections ─────────────────────────────
def apply_ocr_corrections(rows):
    """Apply FIX GROUPS 2-6 to the loaded rows. row_no is 1-indexed."""
    corrected = []
    for row in rows:
        row_no = int(row.get("number", 0))
        notes = []

        # FIX GROUP 2 — Column shift repairs
        if row_no in COLUMN_SHIFT_FIXES:
            fix = COLUMN_SHIFT_FIXES[row_no]
            old_name = row["polymer_name"]
            row.update(fix)
            notes.append(f"[OCR] column-shift fixed; was: {old_name!r}")

        # FIX GROUP 3 — Ro artifact strip
        if row_no in RO_ARTIFACT_FIXES:
            old_ro = row.get("interaction_radius")
            row["interaction_radius"] = RO_ARTIFACT_FIXES[row_no]
            notes.append(f"[OCR] Ro artifact stripped; was: {old_ro}")

        # FIX GROUP 4 — Word-split name corrections
        if row_no in NAME_SPLIT_FIXES:
            old_name = row["polymer_name"]
            if row["polymer_name"] != NAME_SPLIT_FIXES[row_no]:
                row["polymer_name"] = NAME_SPLIT_FIXES[row_no]
                notes.append(f"[OCR] word-split fixed; was: {old_name!r}")

        # FIX GROUP 5 — Collapse double spaces (general pass)
        name = row.get("polymer_name", "")
        if "  " in name:
            row["polymer_name"] = re.sub(r"\s{2,}", " ", name).strip()
            notes.append("[OCR] double space collapsed")

        # FIX GROUP 6 — Source document errors
        if row_no in SOURCE_ERROR_FIXES:
            old_name = row["polymer_name"]
            if row["polymer_name"] != SOURCE_ERROR_FIXES[row_no]:
                row["polymer_name"] = SOURCE_ERROR_FIXES[row_no]
                notes.append(f"[OCR] source error fixed; was: {old_name!r}")

        row["_ocr_notes"] = "; ".join(notes)
        corrected.append(row)
    return corrected


# ─── Step 0B: Brand prefix → class mapping ────────────────────────────────────
BRAND_MAP = [
    ("DESMOPHEN",       "Polyurethane",              "Thermoset/Crosslinked", "polyurethane polyol",         "polyurethane polyol",   "Polyol"),
    ("DESMOLAC",        "Polyurethane",              "Thermoset/Crosslinked", "polyurethane lacquer resin",  "polyurethane resin",    "PU lacquer"),
    ("DESMODUR",        "Polyurethane",              "Thermoset/Crosslinked", "polyisocyanate crosslinker",  "polyisocyanate",        "Polyisocyanate"),
    ("EPIKOTE",         "Epoxy Resin",               "Thermoset/Crosslinked", "bisphenol A diglycidyl ether epoxy resin", "epoxy resin", "Bisphenol A epoxy"),
    ("EPON",            "Epoxy Resin",               "Thermoset/Crosslinked", "bisphenol A diglycidyl ether epoxy resin", "epoxy resin", "Bisphenol A epoxy"),
    ("ARALDITE",        "Epoxy Resin",               "Thermoset/Crosslinked", "epoxy resin",                 "epoxy resin",           "Epoxy"),
    ("PKHH",            "Epoxy Resin",               "Thermoset/Crosslinked", "poly(hydroxy ether of bisphenol A)", "phenoxy resin",   "Phenoxy resin"),
    ("VERSAMID",        "Polyamide",                 "Thermoplastic",         "dimer acid-based polyamide",  "polyamide resin",       "Dimer acid polyamide"),
    ("CYMEL",           "Amino Resin",               "Thermoset/Crosslinked", "melamine-formaldehyde resin", "melamine resin",        "Melamine resin"),
    ("PHENODUR",        "Amino Resin",               "Thermoset/Crosslinked", "phenol-modified amino resin", "amino resin",           "Phenol-amino resin"),
    ("BEETLE",          "Amino Resin",               "Thermoset/Crosslinked", "urea-formaldehyde resin",     "urea resin",            "Urea resin"),
    ("ALKYDAL",         "Polyester & Alkyd",         "Thermoset/Crosslinked", "alkyd resin",                 "alkyd resin",           "Alkyd resin"),
    ("ALFTALAT",        "Polyester & Alkyd",         "Thermoset/Crosslinked", "saturated polyester resin",   "polyester resin",       "Saturated polyester"),
    ("DYNAPOL",         "Polyester & Alkyd",         "Thermoset/Crosslinked", "saturated linear polyester",  "polyester resin",       "Linear polyester"),
    ("BUTVAR",          "Vinyl Polymer",             "Thermoplastic",         "poly(vinyl butyral)",         "polyvinyl butyral",     "PVB"),
    ("MOWITAL",         "Vinyl Polymer",             "Thermoplastic",         "poly(vinyl butyral)",         "polyvinyl butyral",     "PVB"),
    ("MOWILITH",        "Vinyl Polymer",             "Thermoplastic",         "poly(vinyl acetate)",         "polyvinyl acetate",     "PVAc"),
    ("ELVAX",           "Vinyl Polymer",             "Thermoplastic",         "poly(ethylene-co-vinyl acetate)", "EVA copolymer",     "EVA"),
    ("VINYLITE",        "Vinyl Polymer",             "Thermoplastic",         "vinyl chloride-vinyl acetate copolymer", "vinyl resin","VC/VAc copolymer"),
    ("FORMVAR",         "Vinyl Polymer",             "Thermoplastic",         "poly(vinyl formal)",          "polyvinyl formal",      "PVF"),
    ("LAROFLEX",        "Vinyl Polymer",             "Thermoplastic",         "vinyl chloride copolymer",    "vinyl copolymer",       "Vinyl copolymer"),
    ("LUTONAL",         "Vinyl Polymer",             "Thermoplastic",         "poly(vinyl isobutyl ether)",  "polyvinyl ether",       "Vinyl ether"),
    ("LUTANAL",         "Vinyl Polymer",             "Thermoplastic",         "poly(vinyl isobutyl ether)",  "polyvinyl ether",       "Vinyl ether"),
    ("PARALOID",        "Acrylic",                   "Thermoplastic",         "acrylic copolymer resin",     "acrylic resin",         "Acrylic copolymer"),
    ("ACRYLOID",        "Acrylic",                   "Thermoplastic",         "acrylic copolymer resin",     "acrylic resin",         "Acrylic copolymer"),
    ("MACRYNAL",        "Acrylic",                   "Thermoplastic",         "acrylic resin (hydroxyl-functional)", "hydroxy acrylic", "Hydroxy acrylic"),
    ("PLEXIGUM",        "Acrylic",                   "Thermoplastic",         "poly(methyl methacrylate) copolymer", "acrylic resin","PMMA copolymer"),
    ("LUMIFLON",        "Fluoropolymer",             "Thermoplastic",         "fluoroethylene-vinyl ether alternating copolymer", "FEVE resin", "FEVE copolymer"),
    ("STYRON",          "Styrenic",                  "Thermoplastic",         "high-impact polystyrene",     "HIPS",                  "HIPS"),
    ("VITON",           "Elastomer",                 "Elastomer",             "poly(vinylidene fluoride-co-hexafluoropropylene)", "FKM fluoroelastomer", "FKM"),
    ("HYCAR",           "Elastomer",                 "Elastomer",             "poly(acrylonitrile-co-butadiene)", "nitrile rubber",    "NBR"),
    ("CARIFLEX",        "Elastomer",                 "Elastomer",             "poly(styrene-co-isoprene)",   "styrene-isoprene block copolymer", "SIS"),
    ("NEOPRENE",        "Elastomer",                 "Elastomer",             "poly(2-chloro-1,3-butadiene)","neoprene",              "Chloroprene rubber"),
    ("ALLOPRENE",       "Elastomer",                 "Elastomer",             "chlorinated natural rubber",  "chlorinated rubber",    "Chlorinated rubber"),
    ("ALLOPREN",        "Elastomer",                 "Elastomer",             "chlorinated natural rubber",  "chlorinated rubber",    "Chlorinated rubber"),
    ("PERGUT",          "Elastomer",                 "Elastomer",             "chlorinated rubber",          "chlorinated rubber",    "Chlorinated rubber"),
    ("PARLON",          "Elastomer",                 "Elastomer",             "chlorinated rubber",          "chlorinated rubber",    "Chlorinated rubber"),
    ("POLYSAR",         "Elastomer",                 "Elastomer",             "styrene-butadiene rubber",    "SBR",                   "SBR"),
    ("CELLIT",          "Cellulosic Polymer",        "Thermoplastic",         "cellulose acetopropionate",   "cellulose ester",       "Cellulose ester"),
    ("CELLIDORA",       "Cellulosic Polymer",        "Thermoplastic",         "cellulose acetate butyrate",  "cellulose acetate butyrate", "CAB"),
    ("ETHOCEL",         "Cellulosic Polymer",        "Thermoplastic",         "ethyl cellulose",             "ethyl cellulose",       "Ethyl cellulose"),
    ("PENTALYN",        "Natural & Petroleum Resin", "Natural & Petroleum Resin","rosin ester resin",        "rosin ester",           "Rosin ester"),
    ("PICCOPALE",       "Natural & Petroleum Resin", "Natural & Petroleum Resin","aliphatic hydrocarbon resin","hydrocarbon resin",   "Aliphatic HC resin"),
    ("PICCORONE",       "Natural & Petroleum Resin", "Natural & Petroleum Resin","cyclopentadiene resin",    "cyclopentadiene resin", "C5/C9 resin"),
    ("PLIOLYTE",        "Natural & Petroleum Resin", "Natural & Petroleum Resin","styrene-butadiene resin",  "SB resin",              "Styrene-butadiene resin"),
    ("PLIOLITE",        "Natural & Petroleum Resin", "Natural & Petroleum Resin","styrene-butadiene resin",  "SB resin",              "Styrene-butadiene resin"),
    ("SUPER BECKACITE", "Phenolic Resin",            "Thermoset/Crosslinked", "oil-modified phenolic resin", "phenolic resin",        "Oil-modified phenolic"),
    ("ESTANE",          "Polyurethane",              "Thermoset/Crosslinked", "polyurethane elastomer",      "polyurethane elastomer","PU elastomer"),
    ("VAREZ",           "Vinyl Polymer",             "Thermoplastic",         "vinyl polymer",               "vinyl resin",           "Vinyl resin"),
    ("VYHH",            "Vinyl Polymer",             "Thermoplastic",         "vinyl chloride-vinyl acetate copolymer", "vinyl resin","VC/VAc copolymer"),
    ("VCVA",            "Vinyl Polymer",             "Thermoplastic",         "vinyl chloride-vinyl acetate copolymer", "vinyl resin","VC/VAc copolymer"),
]
BRAND_MAP.sort(key=lambda x: -len(x[0]))

# ─── Polymer knowledge table ──────────────────────────────────────────────────
K = {}  # key (uppercase) → dict with iupac, common, common_all, acronyms, cls, sub, cas

def _k(key, iupac, common, common_all, acronyms, cls, sub, cas=None):
    K[key.upper()] = dict(iupac=iupac, common=common, common_all=common_all,
                          acronyms=acronyms, cls=cls, sub=sub, cas=cas)

# Acrylics
_k("PMMA","poly(methyl methacrylate)","poly(methyl methacrylate)","poly(methyl methacrylate); acrylic glass; Plexiglas","PMMA","Acrylic","Methacrylate polymer","9011-14-7")
_k("PEMA","poly(ethyl methacrylate)","poly(ethyl methacrylate)","poly(ethyl methacrylate)","PEMA","Acrylic","Methacrylate polymer","25608-33-7")
_k("PBMA","poly(butyl methacrylate)","poly(butyl methacrylate)","poly(butyl methacrylate)","PBMA","Acrylic","Methacrylate polymer","9003-63-8")
_k("PIBMA","poly(isobutyl methacrylate)","poly(isobutyl methacrylate)","poly(isobutyl methacrylate)","PIBMA","Acrylic","Methacrylate polymer")
_k("PAN","polyacrylonitrile","polyacrylonitrile","polyacrylonitrile; Orlon","PAN","Acrylic","Polyacrylonitrile","25014-41-9")
_k("POLYACRYLONITRILE","polyacrylonitrile","polyacrylonitrile","polyacrylonitrile","PAN","Acrylic","Polyacrylonitrile","25014-41-9")
# Vinyl
_k("PVC","poly(vinyl chloride)","polyvinyl chloride","polyvinyl chloride; PVC","PVC","Vinyl Polymer","Vinyl chloride polymer","9002-86-2")
_k("PVAC","poly(vinyl acetate)","polyvinyl acetate","polyvinyl acetate; PVAc","PVAc; PVAC","Vinyl Polymer","Vinyl acetate polymer","9003-20-7")
_k("PVAc","poly(vinyl acetate)","polyvinyl acetate","polyvinyl acetate; PVAc","PVAc; PVAC","Vinyl Polymer","Vinyl acetate polymer","9003-20-7")
_k("PVB","poly(vinyl butyral)","polyvinyl butyral","polyvinyl butyral; PVB","PVB","Vinyl Polymer","Vinyl butyral polymer","63148-65-2")
_k("PVDC","poly(vinylidene chloride)","polyvinylidene chloride","polyvinylidene chloride; Saran","PVDC","Vinyl Polymer","Vinylidene chloride polymer","9002-85-1")
_k("PVOH","poly(vinyl alcohol)","polyvinyl alcohol","polyvinyl alcohol; PVOH; PVA","PVOH; PVA","Vinyl Polymer","Vinyl alcohol polymer","9002-89-5")
_k("EVA","poly(ethylene-co-vinyl acetate)","ethylene-vinyl acetate copolymer","ethylene-vinyl acetate copolymer; EVA","EVA; EVAC","Vinyl Polymer","EVA copolymer")
_k("EVOH","poly(ethylene-co-vinyl alcohol)","ethylene vinyl alcohol copolymer","ethylene vinyl alcohol copolymer; EVOH; EVAL","EVOH; EVAL","Vinyl Polymer","EVOH copolymer")
_k("POLYVINYLPYRROLIDONE","poly(1-vinyl-2-pyrrolidinone)","polyvinylpyrrolidone","polyvinylpyrrolidone; povidone; PVP","PVP","Vinyl Polymer","Vinyl lactam polymer","9003-39-8")
# Styrenic
_k("PS","polystyrene","polystyrene","polystyrene","PS","Styrenic","Polystyrene","9003-53-6")
_k("POLYSTYRENE","polystyrene","polystyrene","polystyrene","PS","Styrenic","Polystyrene","9003-53-6")
_k("SAN","poly(styrene-co-acrylonitrile)","styrene-acrylonitrile copolymer","styrene-acrylonitrile copolymer; SAN resin","SAN","Styrenic","SAN copolymer","9003-54-7")
_k("ABS","poly(acrylonitrile-co-butadiene-co-styrene)","acrylonitrile butadiene styrene","acrylonitrile butadiene styrene; ABS plastic","ABS","Styrenic","ABS terpolymer","9003-56-9")
# Polyolefin
_k("HDPE","polyethylene, high density","high-density polyethylene","high-density polyethylene; HDPE","HDPE","Polyolefin","Polyethylene","9002-88-4")
_k("LDPE","polyethylene, low density","low-density polyethylene","low-density polyethylene; LDPE","LDPE","Polyolefin","Polyethylene","9002-88-4")
_k("PE","polyethylene","polyethylene","polyethylene","PE","Polyolefin","Polyethylene","9002-88-4")
_k("POLYETHYLENE","polyethylene","polyethylene","polyethylene","PE","Polyolefin","Polyethylene","9002-88-4")
_k("PP","polypropylene","polypropylene","polypropylene","PP","Polyolefin","Polypropylene","9003-07-0")
_k("POLYPROPYLENE","polypropylene","polypropylene","polypropylene","PP","Polyolefin","Polypropylene")
_k("PIB","polyisobutylene","polyisobutylene","polyisobutylene; butyl rubber precursor","PIB","Polyolefin","Polyisobutylene")
_k("POLYISOBUTYLENE","polyisobutylene","polyisobutylene","polyisobutylene","PIB","Polyolefin","Polyisobutylene")
_k("TPX","poly(4-methyl-1-pentene)","poly(4-methyl-1-pentene)","poly(4-methyl-1-pentene); TPX","TPX","Polyolefin","Poly(methylpentene)")
# Fluoropolymers
_k("PTFE","poly(tetrafluoroethylene)","polytetrafluoroethylene","polytetrafluoroethylene; Teflon; PTFE","PTFE","Fluoropolymer","PTFE","9002-84-0")
_k("TEFLON","poly(tetrafluoroethylene)","polytetrafluoroethylene","polytetrafluoroethylene; Teflon","PTFE","Fluoropolymer","PTFE","9002-84-0")
_k("PVDF","poly(vinylidene fluoride)","polyvinylidene fluoride","polyvinylidene fluoride; Kynar; PVDF","PVDF","Fluoropolymer","PVDF","24937-79-9")
_k("FEP","poly(tetrafluoroethylene-co-hexafluoropropylene)","fluorinated ethylene propylene","fluorinated ethylene propylene; FEP","FEP","Fluoropolymer","FEP copolymer")
_k("PCTFE","poly(chlorotrifluoroethylene)","polychlorotrifluoroethylene","polychlorotrifluoroethylene; Kel-F","PCTFE","Fluoropolymer","PCTFE","9002-83-9")
_k("PECTFE","poly(chlorotrifluoroethylene)","polychlorotrifluoroethylene","polychlorotrifluoroethylene; Kel-F","PCTFE","Fluoropolymer","PCTFE","9002-83-9")
_k("PFA","perfluoroalkoxy polymer","perfluoroalkoxy alkane","perfluoroalkoxy polymer; PFA","PFA","Fluoropolymer","PFA")
# Elastomers
_k("NBR","poly(acrylonitrile-co-butadiene)","nitrile rubber","nitrile rubber; acrylonitrile butadiene rubber; NBR rubber","NBR; nitrile","Elastomer","Nitrile rubber")
_k("NITRILE","poly(acrylonitrile-co-butadiene)","nitrile rubber","nitrile rubber; acrylonitrile butadiene rubber","NBR","Elastomer","Nitrile rubber")
_k("EPDM","poly(ethylene-co-propylene-co-diene)","ethylene propylene diene monomer rubber","EPDM rubber; ethylene propylene diene rubber","EPDM","Elastomer","EPDM rubber")
_k("NATURAL RUBBER","poly(cis-1,4-isoprene)","natural rubber","natural rubber; latex; cis-polyisoprene","NR","Elastomer","Natural rubber")
_k("NAT RUBBER","poly(cis-1,4-isoprene)","natural rubber","natural rubber; cis-polyisoprene","NR","Elastomer","Natural rubber")
_k("POLYISOPRENE","poly(isoprene)","polyisoprene","polyisoprene; synthetic rubber","PI; IR","Elastomer","Polyisoprene")
_k("SILICONE","polydimethylsiloxane","silicone rubber","silicone rubber; PDMS; polydimethylsiloxane","SI; Q; VMQ","Elastomer","Silicone rubber")
_k("SBR","poly(styrene-co-butadiene)","styrene-butadiene rubber","styrene-butadiene rubber; SBR","SBR","Elastomer","SBR")
_k("CHLORINATED RUBBER","chlorinated poly(cis-1,4-isoprene)","chlorinated rubber","chlorinated rubber","CR","Elastomer","Chlorinated rubber")
_k("BROMOBUTYL RUBBER","poly(isobutylene-co-isoprene), brominated","bromobutyl rubber","bromobutyl rubber; BIIR","BIIR","Elastomer","Bromobutyl rubber")
_k("BUTYL","poly(isobutylene-co-isoprene)","butyl rubber","butyl rubber; IIR; isobutylene-isoprene rubber","IIR","Elastomer","Butyl rubber")
# Polyesters & Alkyds
_k("PET","poly(ethylene terephthalate)","polyethylene terephthalate","polyethylene terephthalate; Mylar; Dacron","PET; PETP","Polyester & Alkyd","PET","25038-59-9")
_k("PETP","poly(ethylene terephthalate)","polyethylene terephthalate","polyethylene terephthalate; Mylar","PET; PETP","Polyester & Alkyd","PET","25038-59-9")
_k("PBT","poly(butylene terephthalate)","polybutylene terephthalate","polybutylene terephthalate","PBT","Polyester & Alkyd","PBT","26062-94-2")
_k("PETG","poly(ethylene terephthalate-co-1,4-cyclohexanedimethanol terephthalate)","polyethylene terephthalate glycol","polyethylene terephthalate glycol; PETG copolyester","PETG; PET-G","Polyester & Alkyd","PET copolymer")
_k("MYLAR","poly(ethylene terephthalate)","polyethylene terephthalate","polyethylene terephthalate; Mylar","PET","Polyester & Alkyd","PET")
_k("ALKYD","alkyd resin","alkyd resin","alkyd resin","ALK","Polyester & Alkyd","Alkyd resin")
_k("VITEL","copolyester resin","Vitel polyester","Vitel polyester resin","","Polyester & Alkyd","Copolyester")
# Polyamides
_k("PA6","poly(caprolactam)","nylon 6","nylon 6; polyamide 6; polycaprolactam","PA6; PA-6; Nylon 6","Polyamide","Nylon 6","25038-54-4")
_k("PA66","poly(hexamethylene adipamide)","nylon 66","nylon 66; nylon 6,6; polyamide 66","PA66; PA-66; Nylon 66","Polyamide","Nylon 6,6","32131-17-2")
_k("PA11","poly(11-aminoundecanoic acid)","nylon 11","nylon 11; polyamide 11; Rilsan","PA11; PA-11; Nylon 11","Polyamide","Nylon 11")
_k("PA12","poly(laurolactam)","nylon 12","nylon 12; polyamide 12","PA12; PA-12; Nylon 12","Polyamide","Nylon 12")
_k("NYLON","polyamide","nylon","nylon; polyamide","PA","Polyamide","")
_k("NYLON 66","poly(hexamethylene adipamide)","nylon 66","nylon 66; polyamide 66","PA66","Polyamide","Nylon 6,6")
_k("POLYAMIDE","polyamide","polyamide","polyamide","PA","Polyamide","")
# Polyurethane
_k("PUR","polyurethane","polyurethane","polyurethane; PUR; PU","PU; PUR","Polyurethane","")
_k("POLYURETHANE","polyurethane","polyurethane","polyurethane","PU; PUR","Polyurethane","")
# Cellulosic
_k("CELLULOSE ACETATE","cellulose acetate","cellulose acetate","cellulose acetate; CA","CA","Cellulosic Polymer","Cellulose acetate","9004-35-7")
_k("CELLULOSE NITRATE","cellulose nitrate","nitrocellulose","nitrocellulose; cellulose nitrate; guncotton","NC","Cellulosic Polymer","Cellulose nitrate")
_k("NITROCELLULOSE","cellulose nitrate","nitrocellulose","nitrocellulose; cellulose nitrate","NC","Cellulosic Polymer","Cellulose nitrate")
_k("ETHYL CELLULOSE","ethyl cellulose","ethyl cellulose","ethyl cellulose; EC","EC","Cellulosic Polymer","Ethyl cellulose","9004-57-3")
_k("CELLOPHANE","regenerated cellulose film","cellophane","cellophane; regenerated cellulose","","Cellulosic Polymer","Regenerated cellulose")
_k("CELLULOSE","cellulose","cellulose","cellulose; cellophane","","Cellulosic Polymer","Regenerated cellulose")
_k("HPMC","hydroxypropyl methylcellulose","hydroxypropyl methylcellulose","hydroxypropyl methylcellulose; HPMC; hypromellose","HPMC","Cellulosic Polymer","Mixed cellulose ether")
# Epoxy
_k("EPOXY","epoxy resin","epoxy resin","epoxy resin","EP","Epoxy Resin","")
_k("PHENOXY","poly(hydroxy ether of bisphenol A)","phenoxy resin","phenoxy resin; PKHH","","Epoxy Resin","Phenoxy resin")
_k("PKHH","poly(hydroxy ether of bisphenol A)","phenoxy resin","phenoxy resin","","Epoxy Resin","Phenoxy resin")
# Fluoropolymers extra
_k("PVF","poly(vinyl fluoride)","polyvinyl fluoride","polyvinyl fluoride; Tedlar","PVF","Fluoropolymer","PVF")
# Natural & Petroleum
_k("SHELLAC","shellac resin","shellac","shellac; lac resin; button lac","","Natural & Petroleum Resin","Lac resin")
_k("DAMMAR","dammar resin","dammar gum","dammar gum; damar gum; dammar resin","","Natural & Petroleum Resin","Dammar resin")
_k("DAMMAR GUM","dammar resin","dammar gum","dammar gum; damar resin; dammar","","Natural & Petroleum Resin","Dammar resin")
_k("GILSONITE","gilsonite (natural asphaltite)","gilsonite","gilsonite; uintahite; natural asphalt","","Natural & Petroleum Resin","Asphaltite")
_k("KAURI GUM","kauri resin (agathis australis)","kauri gum","kauri gum; kauri resin; copal","","Natural & Petroleum Resin","Kauri resin")
_k("COAL TAR PITCH","coal tar pitch","coal tar pitch","coal tar pitch","","Natural & Petroleum Resin","Pitch")
_k("KETONE RESIN","cyclohexanone-formaldehyde resin","ketone resin","ketone resin; cyclohexanone resin","","Natural & Petroleum Resin","Ketone resin")
_k("VINSOL ROSIN","hydrogenated wood rosin","vinsol resin","vinsol resin; rosin-phenolic","","Natural & Petroleum Resin","Rosin derivative")
# Polysulfone/PES/PPS
_k("PSU","polysulfone","polysulfone","polysulfone; polysulphone","PSU; PSF","Polysulfone / PES / PPS","Polysulfone")
_k("PES","poly(ether sulfone)","polyethersulfone","polyethersulfone; polyether sulfone","PES; PESU","Polysulfone / PES / PPS","PES")
_k("PPS","poly(phenylene sulfide)","polyphenylene sulfide","polyphenylene sulfide","PPS","Polysulfone / PES / PPS","PPS")
# Polyacetal/PEI/PC
_k("PC","poly(bisphenol A carbonate)","polycarbonate","polycarbonate; Lexan; Makrolon","PC","Polyacetal / PEI / PC","Polycarbonate","25037-45-0")
_k("POLYCARBONATE","poly(bisphenol A carbonate)","polycarbonate","polycarbonate; Lexan; Makrolon","PC","Polyacetal / PEI / PC","Polycarbonate")
_k("PEI","polyetherimide","polyetherimide","polyetherimide; Ultem","PEI","Polyacetal / PEI / PC","Polyetherimide")
_k("POM","polyoxymethylene","polyoxymethylene","polyoxymethylene; acetal resin; Delrin","POM","Polyacetal / PEI / PC","Polyacetal")
_k("POMH","polyoxymethylene","polyoxymethylene","polyoxymethylene homopolymer; Delrin","POM","Polyacetal / PEI / PC","Polyacetal homopolymer")
_k("POMC","polyoxymethylene copolymer","polyoxymethylene copolymer","polyoxymethylene copolymer; acetal copolymer; Celcon","POM-C","Polyacetal / PEI / PC","Polyacetal copolymer")
_k("PPO","poly(2,6-dimethyl-1,4-phenylene oxide)","polyphenylene oxide","polyphenylene oxide; PPO; Noryl","PPO; PPE","Polyacetal / PEI / PC","Polyphenylene oxide")
_k("POLYIMIDE","polyimide","polyimide","polyimide; PI; Kapton","PI","Polyacetal / PEI / PC","Polyimide")
_k("ACETAL","polyoxymethylene","polyoxymethylene","polyoxymethylene; acetal resin","POM","Polyacetal / PEI / PC","Polyacetal")
# Amino Resins
_k("MELAMINE","melamine-formaldehyde resin","melamine resin","melamine resin; MF resin","MF","Amino Resin","Melamine resin")
# Phenolic
_k("PHENOLIC","phenol-formaldehyde resin","phenolic resin","phenolic resin; Bakelite","PF","Phenolic Resin","Phenol-formaldehyde")
_k("PHENOLICS","phenol-formaldehyde resin","phenolic resin","phenolic resin","PF","Phenolic Resin","Phenol-formaldehyde")
# Biological & Other
_k("CHLOROPHYLL","chlorophyll","chlorophyll","chlorophyll","","Biological & Other","Pigment")
_k("BLOOD SERUM","blood serum protein","blood serum","blood serum","","Biological & Other","Biological fluid")
_k("UREA","urea","urea","urea; carbamide","","Biological & Other","Small molecule")
_k("SUCROSE","sucrose","sucrose","sucrose; table sugar","","Biological & Other","Disaccharide")
_k("PSORIASIS SCALES","psoriasis scale protein","psoriasis scales","psoriasis scales","","Biological & Other","Biological material")
_k("CHOLESTEROL","cholesterol","cholesterol","cholesterol","","Biological & Other","Sterol")
_k("LARD","lard (rendered pig fat)","lard","lard; pig fat","","Biological & Other","Animal fat")
_k("PALM OIL","palm oil","palm oil","palm oil; palmolein","","Biological & Other","Vegetable oil")
_k("CARBON-60","buckminsterfullerene","fullerene C60","fullerene C60; buckminsterfullerene; C60","C60","Biological & Other","Fullerene")
# misc
_k("VYHH","vinyl chloride-vinyl acetate copolymer","vinyl resin","vinyl chloride-vinyl acetate copolymer","","Vinyl Polymer","VC/VAc copolymer")
_k("CZ RESIN","cyclopentadiene hydrocarbon resin","CZ resin","CZ resin; hydrocarbon resin","","Natural & Petroleum Resin","Hydrocarbon Resin")
_k("POLYAMIDEIMIDE","poly(amide-co-imide)","polyamide-imide","polyamide-imide; PAI","PAI","Polyamide","Polyamide-imide")
_k("FURAN","poly(furfuryl alcohol)","furan resin","furan resin; furfuryl alcohol polymer","","Phenolic Resin","Furan resin")
_k("BETHOXAZIN","poly(1,3-benzoxazine)","benzoxazine resin","benzoxazine resin; polybenzoxazine","","Phenolic Resin","Benzoxazine")

OUT_OF_SCOPE = {"BLOOD SERUM","UREA","SUCROSE","PSORIASIS SCALES","CHOLESTEROL","LARD","PALM OIL","CARBON-60","CHLOROPHYLL"}

# ─── Classification regex rules ───────────────────────────────────────────────
RULES = [
    (r'\bPUR?\b(?!\s*\d)|POLYURETHANE|URETHANE|ISOCYANATE',                                       "Polyurethane", ""),
    (r'\bEPOXY\b|PHENOXY|\bEP\b(?!DM)|EPIKOTE|EPON|ARALDITE',                                    "Epoxy Resin", ""),
    (r'\bMMA\b|\bPMMA\b|\bPEMA\b|\bPBMA\b|\bPIBMA\b|\bPBA\b(?!\d)|\bPNBMA\b|\bPMAA\b',           "Acrylic", "Methacrylate polymer"),
    (r'POLY\(?METHYL METHACRYLATE|METHACRYLATE|ACRYLATE(?!.*RUBBER)|POLYACRYLATE',                 "Acrylic", "Acrylate polymer"),
    (r'\bMMA/EA\b|\bBMA/AN\b|\bMAA/EA\b|\bMAA/MA\b|\bMMA/CYCLOL\b|\bCYCLOL\b',                  "Acrylic", "Acrylic copolymer"),
    (r'\bPAN\b|POLYACRYLONITRILE',                                                                  "Acrylic", "Polyacrylonitrile"),
    (r'\bPTFE\b|TEFLON|\bPVDF\b|KYNAR|\bFEP\b|\bPCTFE\b|PECTFE|\bFQ\b',                          "Fluoropolymer", ""),
    (r'\bFKM\b|\bVITON\b|FLUOROELASTOMER',                                                         "Elastomer", "FKM"),
    (r'FLUOROPOLY|FLUORINATED|FLUORO(?:ELASTOMER|RUBBER|POLYMER)',                                  "Fluoropolymer", ""),
    (r'\bPVC\b|VINYL CHLORIDE|PVAC|\bEVA\b|\bEVOH\b|VINYL ACETATE|PVOH|VINYL ALCOHOL',            "Vinyl Polymer", ""),
    (r'\bPVDC\b|VINYLIDENE CHLORIDE|POLYVINYL|VINYLITE|VIPLA|LAROFLEX|CHLOROPAR|CERECLOR',        "Vinyl Polymer", ""),
    (r'\bVYHH\b|\bVAGD\b|\bVAGH\b|\bVMCA\b|\bVMCC\b|\bVMCH\b|\bVYLF\b|\bVXCC\b|\bAYAA\b',       "Vinyl Polymer", "VC/VAc copolymer"),
    (r'\bVBE\b|\bPVBE\b|\bPVEE\b|\bVINYL.*ETHER|POLYVINYLBUTYL',                                  "Vinyl Polymer", "Vinyl ether polymer"),
    (r'\bLUTONAL\b|\bLUTANAL\b',                                                                   "Vinyl Polymer", "Polyvinyl ether"),
    (r'\bSARAN\b|\bVDC\b|\bSARANEX\b',                                                             "Vinyl Polymer", "Vinylidene chloride"),
    (r'\bPS\b(?!\s*$|\s*\d)|POLYSTYRENE|\bSAN\b|\bABS\b|STYRON|PLIOLYTE|PLIOLITE',               "Styrenic", ""),
    (r'\bSTY\b(?:/|\s)|STYRENE.MALEATE|STYRENE.BUTENOL|\bLYTRON\b|\bMARBON\b|\bSMA\b|\bBUTON\b',"Styrenic", "Styrene copolymer"),
    (r'\bHDPE\b|\bLDPE\b|POLYETHYLENE|\bPE\b(?!\s*\w)|POLYOLEFIN|\bPIB\b',                       "Polyolefin", "Polyethylene"),
    (r'\bPP\b(?!\w)|POLYPROPYLENE|\bTPX\b',                                                        "Polyolefin", "Polypropylene"),
    (r'PARAFFIN WAX|PARAFFIN\b',                                                                    "Polyolefin", "Paraffin wax"),
    (r'\bNBR\b|\bNITRILE\b(?!.*RESIN)',                                                             "Elastomer", "Nitrile rubber"),
    (r'\bSBR\b|\bBUNA\b|STYRENE.*BUTADIENE(?!.*RESIN)',                                             "Elastomer", "SBR"),
    (r'\bEPDM\b|ETHYLENE PROPYLENE DIENE',                                                          "Elastomer", "EPDM rubber"),
    (r'NATURAL RUBBER|NAT RUBBER|POLYISOPRENE',                                                     "Elastomer", "Natural rubber"),
    (r'NEOPRENE|CHLOROPRENE|POLYCHLOROPRENE',                                                      "Elastomer", "Chloroprene rubber"),
    (r'\bBUTYL\b(?!.*ETHER)|POLYISOBUTYLENE(?!.*ACRYL)|\bIIR\b|BROMOBUTYL',                      "Elastomer", "Butyl rubber"),
    (r'CHLOROSULFONATED|HYPALON|\bCSM\b',                                                           "Elastomer", "CSM"),
    (r'CHLORINATED RUBBER|ALLOPRENE|ALLOPREN|PARLON|PERGUT',                                       "Elastomer", "Chlorinated rubber"),
    (r'\bSI\b(?!\w)|SILICONE|PDMS|POLYDIMETHYLSILOXANE|\bVMQ\b',                                   "Elastomer", "Silicone rubber"),
    (r'HYTREL|POLYESTER.*ELASTOMER',                                                                "Elastomer", "TPE-E"),
    (r'\bT SULPHIDE\b|\bPOLYSULFIDE\b',                                                            "Elastomer", "Polysulfide rubber"),
    (r'RUBBER|ELASTOMER',                                                                            "Elastomer", ""),
    (r'\bPA\s*\d+|\bNYLON\b|POLYAMIDE|POLYAMIDE.IMIDE',                                            "Polyamide", ""),
    (r'\bPSU\b|POLYSULPH|POLYSULFO|\bPES\b(?!\s*L)|\bPPS\b|POLYPHENYLENE SULFIDE',                "Polysulfone / PES / PPS", ""),
    (r'\bPOM\b|POLYOXYMETHYLENE|ACETAL',                                                            "Polyacetal / PEI / PC", "Polyacetal"),
    (r'\bPEI\b(?!\s*\d{3})|POLYETHERIMIDE',                                                        "Polyacetal / PEI / PC", "Polyetherimide"),
    (r'\bPC\b(?!\s*\d)|\bPOLYCARBONATE\b',                                                        "Polyacetal / PEI / PC", "Polycarbonate"),
    (r'\bPPO\b|POLYPHENYLENE OXIDE',                                                                "Polyacetal / PEI / PC", "Polyphenylene oxide"),
    (r'POLYIMIDE|\bR POLYIMIDE',                                                                    "Polyacetal / PEI / PC", "Polyimide"),
    (r'\bPET\b|\bPETP\b|\bPBT\b|POLYESTER|TEREPHTHALATE|ALFTALAT|ALKYDAL|DYNAPOL|MYLAR|VITEL',   "Polyester & Alkyd", ""),
    (r'ALKYD|ADIPATE|ISOPHTHALIC|TEREPHTALIC|PHTHALATE',                                           "Polyester & Alkyd", "Polyester"),
    (r'DEG ISOPH|DEG PHTH|DPG PHTH|DOW ADIP|PLEXAL|PLASTOKYD|DUROFTAL|SOALKYD',                   "Polyester & Alkyd", ""),
    (r'CELLULOSE|CELLIT|CELLIDORA|ETHOCEL|NITROCELLULOSE|CELLOPHANE|\bHPMC\b',                     "Cellulosic Polymer", ""),
    (r'\bCA\b(?:B|P)?\s*\d|ACETYL.*CELLULOSE|CARBOXYMETHYL CELLULOSE',                             "Cellulosic Polymer", ""),
    (r'ROSIN|TERPENE|PENTALYN|PICCOPALE|PICCORONE|DAMMAR|SHELLAC|GILSONITE|KAURI|VINSOL',         "Natural & Petroleum Resin", ""),
    (r'HYDROCARBON RESIN|CZ RESIN|KETONE RESIN|BECKOLIN|PETROLEUM PITCH|COAL TAR|ASPHALT',        "Natural & Petroleum Resin", ""),
    (r'ESTER GUM|CELLOLYN|SANTOLITE|CONOCO|PARAPOL|PICCOFLEX',                                     "Natural & Petroleum Resin", ""),
    (r'HEXADECYL MONOESTER|HYDR SPERM OIL|SPERM OIL',                                              "Natural & Petroleum Resin", "Animal wax/oil"),
    (r'MELAMINE|UREA.FORMALDEHYDE|AMINO RESIN|\bMF\b|\bUF\b|SULFONAMIDE|BEETLE\b',               "Amino Resin", ""),
    (r'PHENOLIC|PHENOL.FORMALDEHYDE|NOVOLAC|BAKELITE|SUPER BECKACITE|BENZOXAZIN|FURAN',           "Phenolic Resin", ""),
    (r'BLOOD|SERUM|SUCROSE|CHOLESTEROL|LARD|PALM OIL|CHLOROPHYLL|PSORIASIS|CASEIN|LIGNIN',        "Biological & Other", ""),
    (r'^\d+%\s*IN WATER|IN WATER.*AMINE',                                                          "Biological & Other", "Aqueous system"),
    (r'PARALOID|ACRYLOID|LUCITE|PLEXIGUM|MACRYNAL|BAREX|MODAFLOW',                                "Acrylic", "Acrylic resin"),
    (r'\bACRYLAMIDE\b|POLYACRYLAMIDE',                                                              "Acrylic", "Acrylamide polymer"),
    (r'\bPVF\b',                                                                                    "Fluoropolymer", "PVF"),
    (r'\bEPOCRYL\b',                                                                               "Epoxy Resin", "Acrylate-modified epoxy"),
    (r'\bHET RESIN\b',                                                                             "Epoxy Resin", "Halogenated epoxy"),
    (r'ZINK SILICATE|ZINC SILICATE',                                                               "Epoxy Resin", "Zinc silicate coating"),
    (r'^CH\s+\d{4}',                                                                               "Epoxy Resin", "Coal tar epoxy coating"),
    (r'\bDEGMP\b|\bCARB DEG\b',                                                                   "Polyester & Alkyd", "Polyester"),
    (r'ETHYLENE.*PROPYLENE|PROPYLENE.*ETHYLENE',                                                   "Elastomer", "EPDM rubber"),
    (r'\bEBONITE\b',                                                                               "Elastomer", "Ebonite"),
    (r'\bULTRASON\b',                                                                              "Polysulfone / PES / PPS", "Polysulfone"),
    (r'ISOB MALANH|ISOB MAL',                                                                      "Polyester & Alkyd", "Polyester"),
]


# ─── Step 0: Pre-classification helpers ──────────────────────────────────────
TIME_RE  = re.compile(r'\b(\d+)\s*(MIN|HR|HOUR|HRS)\b', re.IGNORECASE)
CONC_RE  = re.compile(r'\((\d+)%\)\s*$')
COPOLY_RE = re.compile(r'^[A-Z]{1,8}/[A-Z]{1,8}', re.IGNORECASE)
R_PREFIX_RE = re.compile(r'^R\s+\S', re.IGNORECASE)

def route_entry(nu):
    for kw in OUT_OF_SCOPE:
        if kw in nu:
            return 'flag_out_of_scope'
    if CONC_RE.search(nu):
        return 'concentration_series'
    if TIME_RE.search(nu):
        return 'time_series'
    if R_PREFIX_RE.match(nu):
        return 'resistance_data'
    if COPOLY_RE.match(nu.strip()):
        return 'copolymer'
    for prefix, *_ in BRAND_MAP:
        if nu.startswith(prefix.upper()):
            return 'trade_name'
    return 'standard'

def get_brand_info(nu):
    for prefix, cls, lvl1, iupac_h, common_h, sub_h in BRAND_MAP:
        if nu.startswith(prefix.upper()):
            return cls, sub_h, iupac_h, common_h
    return None, None, None, None

def classify_fallback(nu):
    for pattern, cls, sub in RULES:
        if re.search(pattern, nu, re.IGNORECASE):
            return cls, sub
    return "Vinyl Polymer", "[needs-review]"

def clean_name_for_lookup(name):
    n = name.strip().upper()
    n = re.sub(r'\s*(SOL|CR|AT HIGH TEMP\.?|SOLUBILITY|LG|SOL\.|CHEMICAL RES\.?|PERM[<>][\d.]*|PERM.*)\s*$', '', n)
    n = re.sub(r'\s+[A-Z]{1,3}\d*\s*$', '', n)
    n = re.sub(r'\?+', '', n).strip()
    return n

def _smart_title(name_orig):
    """Apply title case to a name from an all-caps source.
    Rules:
    - First word: capitalize first letter, rest lowercase (brand name).
    - Subsequent pure-letter tokens of 1-5 chars: keep ALL CAPS (grade codes,
      abbreviations: BP, STD, HE, LF, STD, MOD, etc.)
    - Subsequent longer letter tokens (>5 chars): capitalize first letter only.
    - Tokens with digits or hyphens: keep as-is from original.
    """
    tokens = name_orig.split()
    out = []
    for i, tok in enumerate(tokens):
        letters_only = re.sub(r'[^A-Za-z]', '', tok)
        has_digit = bool(re.search(r'\d', tok))
        has_hyphen = '-' in tok
        if i == 0:
            # First token: brand name, capitalize first letter
            out.append(tok[0].upper() + tok[1:].lower() if len(tok) > 1 else tok.upper())
        elif has_digit or has_hyphen:
            # Grade codes like "828", "B-76", "1700", "HE10" — keep original
            out.append(tok)
        elif len(letters_only) <= 5:
            # Short all-letter tokens stay ALL CAPS (BP, STD, MOD, HE, LF, etc.)
            out.append(tok.upper())
        else:
            # Longer words: capitalize first letter
            out.append(tok[0].upper() + tok[1:].lower() if len(tok) > 1 else tok.upper())
    return ' '.join(out)

def make_name_clean(name_input, route, is_trade=False):
    """Step 3: Generate display name_clean."""
    name = name_input.strip()
    # Strip asterisk uncertainty marker
    name = name.replace("*", "").strip()
    # Strip trailing question mark parenthetical e.g. "(QUESTIONABLE VALUES)"
    name = re.sub(r'\s*\(QUESTIONABLE\s+VALUES?\)\s*$', '', name, flags=re.IGNORECASE).strip()
    # Collapse multiple spaces
    name = re.sub(r"\s{2,}", " ", name)
    nu = name.upper()
    if name == name.upper() and len(name) > 4 and not re.match(r'^[A-Z]{1,6}$', name):
        # Check if it's a known brand - apply manufacturer rules
        for prefix, cls, lvl1, iupac_h, common_h, sub_h in BRAND_MAP:
            if nu.startswith(prefix.upper()):
                # EPIKOTE/EPON/ELVAX stay ALL CAPS per spec
                if prefix.upper() in ("EPIKOTE", "EPON", "ELVAX"):
                    break
                # Apply smart title case preserving grade codes
                name = _smart_title(name)
                break
        else:
            # Standard: if all-caps, apply smart title case
            if name == name.upper():
                name = _smart_title(name)
    elif name == name.lower() and len(name) > 1:
        name = name.capitalize()
    return name

def resolve_name(name_in, route, notes):
    """Returns (iupac, common, common_all, acronyms, cls, sub, cas_hint)."""
    nu = name_in.upper()
    clean = clean_name_for_lookup(name_in)
    info = K.get(clean) or K.get(nu.strip())

    if not info:
        for kkey, kinfo in K.items():
            if kkey in nu or nu in kkey:
                info = kinfo
                break

    if route == 'flag_out_of_scope':
        kinfo = K.get(clean) or K.get(nu)
        if kinfo:
            return kinfo['iupac'], kinfo['common'], kinfo['common_all'], kinfo['acronyms'], kinfo['cls'], kinfo['sub'], kinfo.get('cas')
        return "", name_in.title(), name_in.title(), "", "Biological & Other", "", None

    if route == 'time_series':
        m = TIME_RE.search(nu)
        cond = m.group(0) if m else ""
        base = TIME_RE.sub('', name_in).strip().rstrip('-').strip()
        notes.append(f"[PRE-CLASSIFY] time_series; condition: {cond}; base: {base}")
        base_info = K.get(base.upper()) or K.get(clean_name_for_lookup(base).upper())
        if base_info:
            return base_info['iupac'], base_info['common'], base_info['common_all'], base_info['acronyms'], base_info['cls'], base_info['sub'], base_info.get('cas')
        cls, sub = classify_fallback(base.upper())
        return "", base.title(), base.title(), "", cls, sub, None

    if route == 'concentration_series':
        m = CONC_RE.search(name_in)
        pct = m.group(1) if m else ""
        base = CONC_RE.sub('', name_in).strip()
        notes.append(f"[PRE-CLASSIFY] concentration_series; concentration: {pct}%")
        base_info = K.get(clean_name_for_lookup(base).upper())
        if base_info:
            return base_info['iupac'], base_info['common'], base_info['common_all'], base_info['acronyms'], base_info['cls'], base_info['sub'], base_info.get('cas')
        brand_cls, brand_sub, brand_iupac, brand_common = get_brand_info(base.upper())
        if brand_cls:
            return brand_iupac or "", brand_common or base, brand_common or base, "", brand_cls, brand_sub, None
        cls, sub = classify_fallback(base.upper())
        return "", base.title(), base.title(), "", cls, sub, None

    if route == 'resistance_data':
        base = re.sub(r'^R\s+', '', name_in, flags=re.IGNORECASE).strip()
        notes.append(f"[PRE-CLASSIFY] resistance_data; base: {base}")
        base_info = K.get(clean_name_for_lookup(base).upper())
        if base_info:
            return base_info['iupac'], base_info['common'], base_info['common_all'], base_info['acronyms'], base_info['cls'], base_info['sub'], base_info.get('cas')
        cls, sub = classify_fallback(base.upper())
        return "", base.title(), base.title(), "", cls, sub, None

    if route == 'copolymer':
        notes.append("[PRE-CLASSIFY] copolymer; monomer ratio notation preserved")
        cls, sub = classify_fallback(nu)
        common = f"copolymer ({name_in})"
        return "", common, common, "", cls, sub, None

    if route == 'trade_name':
        brand_cls, brand_sub, brand_iupac, brand_common = get_brand_info(nu)
        if info:
            return info['iupac'], info['common'], info['common_all'], info['acronyms'], info['cls'], info['sub'], info.get('cas')
        iupac = brand_iupac or ""
        common_n = brand_common or name_in.title()
        return iupac, common_n, common_n, "", brand_cls or "", brand_sub or "", None

    # standard
    if info:
        return info['iupac'], info['common'], info['common_all'], info['acronyms'], info['cls'], info['sub'], info.get('cas')
    for kkey, kinfo in K.items():
        if nu.startswith(kkey) or kkey.startswith(nu.split()[0] if nu.split() else nu):
            if len(kkey) >= 2:
                info = kinfo
                break
    if info:
        return info['iupac'], info['common'], info['common_all'], info['acronyms'], info['cls'], info['sub'], info.get('cas')
    cls, sub = classify_fallback(nu)
    return "", name_in.title(), name_in.title(), "", cls, sub, None


# ─── PubChem CAS lookup ───────────────────────────────────────────────────────
def pubchem_get(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
        except Exception:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return None

CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")

def get_cas_and_url_from_pubchem(name):
    """Returns (cas, cid, pubchem_url) or (None, None, None)."""
    encoded = urllib.parse.quote(name, safe='')
    url = f"{PUBCHEM_BASE}/compound/name/{encoded}/JSON"
    data = pubchem_get(url)
    if not data:
        return None, None, None
    try:
        cid = data["PC_Compounds"][0]["id"]["id"]["cid"]
    except (KeyError, IndexError):
        return None, None, None
    pubchem_url = f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"
    syn_url = f"{PUBCHEM_BASE}/compound/cid/{cid}/synonyms/JSON"
    syn_data = pubchem_get(syn_url)
    if not syn_data:
        return None, cid, pubchem_url
    for syn in syn_data.get("InformationList", {}).get("Information", [{}])[0].get("Synonym", []):
        if CAS_RE.match(syn.strip()):
            return syn.strip(), cid, pubchem_url
    return None, cid, pubchem_url


# ─── Main pipeline ────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Hansen A.2 polymer enrichment pipeline")
    parser.add_argument("--resume",  action="store_true", help="Resume from checkpoint")
    parser.add_argument("--sample",  type=int, default=0, help="Process only first N rows")
    args = parser.parse_args()

    # ── Step 1: Load source CSV ──
    rows = []
    with open(SOURCE_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(dict(row))
    print(f"Loaded {len(rows)} rows from {SOURCE_CSV}")

    # ── Step 0B: Apply OCR corrections ──
    rows = apply_ocr_corrections(rows)
    print("Applied OCR corrections (FIX GROUPS 2-6)")

    if args.sample:
        rows = rows[:args.sample]
        print(f"Sample mode: processing first {args.sample} rows")

    total = len(rows)

    # ── Load checkpoint ──
    checkpoint = {}
    if args.resume and CHECKPOINT.exists():
        with open(CHECKPOINT) as f:
            checkpoint = json.load(f)
        start_row = checkpoint.get("last_completed_row", 0)
        print(f"Resuming from row {start_row} ({len(checkpoint.get('done', {}))} rows done)")
    done_keys = checkpoint.get("done", {})

    # ── Open output CSV (append mode for resume, write mode for fresh) ──
    write_header = not (args.resume and ENRICHED_CSV.exists())
    out_mode = "a" if (args.resume and ENRICHED_CSV.exists()) else "w"
    FIELDS = [
        'name_input', 'name_clean', 'name_iupac', 'name_common', 'name_common_all',
        'name_acronyms', 'cas', 'product_url', 'tds_url', 'sds_url',
        'dD', 'dP', 'dH', 'radius', 'class', 'subclass', 'processing_notes'
    ]

    cas_found = 0
    cas_skipped = 0
    batch = []

    with open(ENRICHED_CSV, out_mode, newline='', encoding='utf-8') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=FIELDS, extrasaction='ignore')
        if write_header:
            writer.writeheader()

        for i, row in enumerate(rows):
            row_no = row.get("number", str(i+1))
            name_in = row.get("polymer_name", "").strip()
            if not name_in:
                continue

            # Skip if already done (resume mode)
            if str(row_no) in done_keys:
                continue

            try:
                dD = float(row.get("dispersion", 0))
                dP = float(row.get("polar", 0))
                dH = float(row.get("hydrogen_bonding", 0))
                radius = float(row.get("interaction_radius", 0))
            except (ValueError, TypeError):
                continue

            ocr_notes = row.get("_ocr_notes", "")
            notes = [ocr_notes] if ocr_notes else []
            nu = name_in.upper()

            # ── Step 0: Route ──
            route = route_entry(nu)

            # ── Step 2: HSP plausibility flags ──
            if dD < 10:
                notes.append("[HSP] dD unusually low (<10)")
            if dD > 28:
                notes.append("[HSP] dD unusually high (>28)")
            if dP < 0:
                notes.append("[HSP] dP negative (fitting artifact)")
            if dH < 0:
                notes.append("[HSP] dH negative (fitting artifact)")
            if radius > 30:
                notes.append("[HSP] radius unusually large (>30)")
            if abs(dP) < 1.0 and abs(dH) < 1.0 and 'HYDROCARBON' not in nu and 'PARAFFIN' not in nu and 'SILICONE' not in nu:
                notes.append("[HSP] near-nonpolar")

            # ── Step 3: Name resolution ──
            name_iupac, name_common, name_common_all, name_acronyms, cls, sub, cas_hint = \
                resolve_name(name_in, route, notes)
            name_clean = make_name_clean(name_in, route, is_trade=(route == 'trade_name'))

            # ── Step 4: CAS resolution (PubChem) ──
            cas = cas_hint or ""
            product_url = ""
            tds_url = ""
            sds_url = ""

            if str(row_no) in done_keys:
                cached = done_keys[str(row_no)]
                cas = cached.get('cas', cas)
                product_url = cached.get('product_url', product_url)
            elif route == 'flag_out_of_scope':
                notes.append("[CAS] CAS lookup skipped: out of scope")
                cas_skipped += 1
            elif not cas:
                lookup_name = name_common or name_in
                if route == 'time_series':
                    lookup_name = TIME_RE.sub('', name_in).strip()
                elif route == 'concentration_series':
                    lookup_name = CONC_RE.sub('', name_in).strip()
                elif route == 'resistance_data':
                    lookup_name = re.sub(r'^R\s+', '', name_in, flags=re.IGNORECASE).strip()

                found_cas, cid, purl = get_cas_and_url_from_pubchem(lookup_name)
                time.sleep(0.22)
                if found_cas:
                    cas = found_cas
                    notes.append(f"[CAS] found via PubChem name search: {found_cas}")
                    cas_found += 1
                else:
                    notes.append("[CAS] not found via PubChem")

                # Step 10B: product_url for generic polymers
                if purl:
                    product_url = purl
                    notes.append(f"[URL] product_url = PubChem CID {cid}")

            # ── Step 9: Classify ──
            if not cls:
                brand_cls, brand_sub, _, _ = get_brand_info(nu)
                if brand_cls:
                    cls = brand_cls
                    sub = brand_sub or sub
                else:
                    cls, sub = classify_fallback(nu)

            if route == 'trade_name':
                notes.append(f"[CLASS] trade_name route; class: {cls}")
            else:
                notes.append(f"[CLASS] class: {cls}")

            rec = {
                'name_input':       name_in,
                'name_clean':       name_clean,
                'name_iupac':       name_iupac,
                'name_common':      name_common,
                'name_common_all':  name_common_all,
                'name_acronyms':    name_acronyms,
                'cas':              cas,
                'product_url':      product_url,
                'tds_url':          tds_url,
                'sds_url':          sds_url,
                'dD':               dD,
                'dP':               dP,
                'dH':               dH,
                'radius':           radius,
                'class':            cls,
                'subclass':         sub,
                'processing_notes': "; ".join(n for n in notes if n),
            }

            batch.append(rec)
            done_keys[str(row_no)] = {'cas': cas, 'product_url': product_url}

            # ── Write batch and checkpoint every 50 rows ──
            if len(batch) >= 50:
                writer.writerows(batch)
                f_out.flush()
                batch.clear()
                checkpoint = {
                    "last_completed_row": i + 1,
                    "total_rows": total,
                    "output_file": str(ENRICHED_CSV),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "done": done_keys,
                }
                with open(CHECKPOINT, 'w') as ckf:
                    json.dump(checkpoint, ckf, indent=2)
                print(f"  Checkpoint: {i+1}/{total} rows (CAS found: {cas_found})")

        # Write remaining batch
        if batch:
            writer.writerows(batch)
            f_out.flush()

    # ── Final checkpoint ──
    checkpoint = {
        "last_completed_row": total,
        "total_rows": total,
        "output_file": str(ENRICHED_CSV),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "done": done_keys,
    }
    with open(CHECKPOINT, 'w') as ckf:
        json.dump(checkpoint, ckf, indent=2)

    # ── Write metadata.json ──
    meta = {
        "id": "hansen_a2_enriched",
        "name": "Hansen A.2 Polymers — Enriched",
        "source": "data/processed/table_a2.csv",
        "description": "Hansen Solubility Parameters Table A.2 polymer dataset, enriched with name resolution, CAS, classification, and URL fields.",
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "polymer_count": total,
        "cas_found": cas_found,
        "cas_skipped": cas_skipped,
        "fields": FIELDS,
        "pipeline_version": "pipeline_hansen_a2.py v1",
    }
    with open(OUT_DIR / "metadata.json", 'w') as mf:
        json.dump(meta, mf, indent=2)

    print(f"\nDone. Output: {ENRICHED_CSV}")
    print(f"  Rows processed : {total}")
    print(f"  CAS found      : {cas_found}")
    print(f"  CAS skipped    : {cas_skipped}")
    print(f"  CAS not found  : {total - cas_found - cas_skipped}")


if __name__ == "__main__":
    main()
