#!/usr/bin/env python3
"""
process_polymers_5.py — HSP Polymer pipeline v5
Generates data/datasets/hsp_polymers_5/polymers_enriched.csv
and data/datasets/hsp_polymers_5/polymers.csv

Improvements over v4:
- Adds name_clean as explicit output column (per pipeline spec)
- Comprehensive IUPAC name knowledge table (expanded coverage)
- Better name_common / name_common_all for all polymer types
- name_clean as primary display name in polymers.csv (replaces name_common)
- PubChem CAS lookup with rate-limiting
- Product URL assignment: PubChem CID for generics, manufacturer for trade names
- More precise subclass assignments
- Reuses v4 CAS checkpoint to avoid redundant API calls
"""

import os
import re
import time
import json
import requests
import pandas as pd
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE        = Path(__file__).parent
RAW_CSV     = BASE / "datasets/hspip_polymers/raw/HSPiP_polymers.csv"
OUT_DIR     = BASE / "datasets/hsp_polymers_5"
OUT_DIR.mkdir(parents=True, exist_ok=True)
ENRICHED    = OUT_DIR / "polymers_enriched.csv"
DB_CSV      = OUT_DIR / "polymers.csv"
V4_CKPT     = BASE / "datasets/hsp_polymers_4/checkpoint.json"

# ─── Out-of-scope terms ───────────────────────────────────────────────────────
OUT_OF_SCOPE = [
    "BLOOD SERUM","UREA","SUCROSE","PSORIASIS SCALES",
    "CHOLESTEROL","LARD","PALM OIL","CARBON-60","CHLOROPHYLL",
]

# ─── Brand prefix → class ─────────────────────────────────────────────────────
BRAND_CLASS_MAP = {
    "DESMOPHEN":  "Polyurethane",
    "DESMOLAC":   "Polyurethane",
    "DESMODUR":   "Polyurethane",
    "EPIKOTE":    "Epoxy Resin",
    "EPON":       "Epoxy Resin",
    "ARALDITE":   "Epoxy Resin",
    "VERSAMID":   "Polyamide",
    "CYMEL":      "Amino Resin",
    "PHENODUR":   "Amino Resin",
    "ALKYDAL":    "Polyester & Alkyd",
    "ALFTALAT":   "Polyester & Alkyd",
    "DYNAPOL":    "Polyester & Alkyd",
    "BUTVAR":     "Vinyl Polymer",
    "MOWITAL":    "Vinyl Polymer",
    "ELVAX":      "Vinyl Polymer",
    "PARALOID":   "Acrylic",
    "ACRYLOID":   "Acrylic",
    "MACRYNAL":   "Acrylic",
    "LUMIFLON":   "Fluoropolymer",
    "STYRON":     "Styrenic",
    "VITON":      "Elastomer",
    "HYCAR":      "Elastomer",
    "CELLIT":     "Cellulosic Polymer",
    "ETHOCEL":    "Cellulosic Polymer",
    "CELLIDORA":  "Cellulosic Polymer",
    "PICCOPALE":  "Natural & Petroleum Resin",
    "PICCORONE":  "Natural & Petroleum Resin",
    "PENTALYN":   "Natural & Petroleum Resin",
}

# ─── Brand capitalization rules ───────────────────────────────────────────────
BRAND_CAPS = {
    "DESMOPHEN": "Desmophen", "DESMODUR": "Desmodur", "DESMOLAC": "Desmolac",
    "EPIKOTE": "EPIKOTE", "EPON": "EPON",
    "ARALDITE": "Araldite",
    "VERSAMID": "Versamid",
    "CYMEL": "Cymel", "PHENODUR": "Phenodur",
    "ALKYDAL": "Alkydal", "ALFTALAT": "Alftalat",
    "DYNAPOL": "DYNAPOL",
    "BUTVAR": "Butvar", "MOWITAL": "Mowital",
    "ELVAX": "ELVAX",
    "PARALOID": "Paraloid", "ACRYLOID": "Acryloid", "MACRYNAL": "Macrynal",
    "LUMIFLON": "Lumiflon",
    "STYRON": "Styron",
    "VITON": "Viton", "HYCAR": "Hycar",
    "CELLIT": "Cellit", "ETHOCEL": "Ethocel", "CELLIDORA": "Cellidora",
    "PICCOPALE": "Piccopale", "PICCORONE": "Piccorone", "PENTALYN": "Pentalyn",
}

# Preserved acronyms (never apply title-case transforms)
PRESERVE_AS_IS = {
    "PMMA","PVC","PS","HDPE","LDPE","EPDM","NBR","SBR","SAN","ABS",
    "PTFE","PVDF","PEI","PVAC","TPX","PKHH","PIB","POM","PPO","PSU",
    "PES","PPS","PET","PBT","PETG","EVA","EVOH","PVDC","PAN","PEI",
    "PBMA","PEMA","PIBMA","PA","PU","EP","PE","PP","PC","HPMC","PVP",
    "PVOH","PVAL","NBR",
}

# ─── Acronym seed table: acronym → (IUPAC, [common names], pubchem_cid_or_None) ─
ACRONYM_TABLE = {
    "PMMA":  ("Poly(methyl methacrylate)",            ["acrylic glass","acrylic","plexiglass","perspex"], 6328),
    "PVC":   ("Poly(vinyl chloride)",                  ["polyvinyl chloride","vinyl plastic","PVC"], 6338),
    "PS":    ("Polystyrene",                            ["polystyrene","styrofoam"], 6353),
    "HDPE":  ("Polyethylene, high density",             ["high-density polyethylene","HDPE"], 9795),
    "LDPE":  ("Polyethylene, low density",              ["low-density polyethylene","LDPE"], 9795),
    "PP":    ("Polypropylene",                          ["polypropylene"], 9857),
    "PE":    ("Polyethylene",                           ["polyethylene","PE"], 9795),
    "PIB":   ("Polyisobutylene",                        ["polyisobutylene","butyl rubber base"], 31218),
    "PTFE":  ("Polytetrafluoroethylene",                ["PTFE","Teflon","polytetrafluoroethylene"], 9903),
    "PVDF":  ("Poly(vinylidene fluoride)",              ["PVDF","polyvinylidene fluoride","Kynar"], 6365),
    "NBR":   ("Poly(acrylonitrile-co-butadiene)",       ["nitrile rubber","nitrile-butadiene rubber","Buna-N"], None),
    "SBR":   ("Poly(styrene-co-butadiene)",             ["styrene-butadiene rubber","SBR","Buna-S"], None),
    "EPDM":  ("Poly(ethylene-co-propylene-co-diene)",  ["EPDM rubber","ethylene propylene diene rubber"], None),
    "SAN":   ("Poly(styrene-co-acrylonitrile)",         ["SAN","styrene-acrylonitrile copolymer"], None),
    "ABS":   ("Poly(acrylonitrile-co-butadiene-co-styrene)", ["ABS","acrylonitrile butadiene styrene"], None),
    "HPMC":  ("Hydroxypropyl methylcellulose",          ["HPMC","hypromellose"], 57503),
    "PVP":   ("Poly(vinylpyrrolidone)",                 ["PVP","polyvinylpyrrolidone","povidone"], 6356),
    "EVA":   ("Poly(ethylene-co-vinyl acetate)",        ["EVA","ethylene-vinyl acetate copolymer"], None),
    "EVOH":  ("Poly(ethylene-co-vinyl alcohol)",        ["EVOH","ethylene-vinyl alcohol copolymer"], None),
    "PVOH":  ("Poly(vinyl alcohol)",                    ["PVOH","PVA","polyvinyl alcohol"], 11199),
    "PVAL":  ("Poly(vinyl alcohol)",                    ["PVOH","PVA","polyvinyl alcohol"], 11199),
    "PKHH":  ("Poly(hydroxy ether of bisphenol A)",    ["phenoxy resin","PKHH","phenoxy polymer"], None),
    "PAN":   ("Polyacrylonitrile",                      ["PAN","polyacrylonitrile"], 9904),
    "PEMA":  ("Poly(ethyl methacrylate)",               ["PEMA"], None),
    "PBMA":  ("Poly(butyl methacrylate)",               ["PBMA"], None),
    "PIBMA": ("Poly(isobutyl methacrylate)",            ["PIBMA"], None),
    "PEI":   ("Polyetherimide",                         ["PEI","polyetherimide","Ultem"], None),
    "PSU":   ("Polysulfone",                            ["PSU","polysulfone","Udel"], None),
    "PES":   ("Polyethersulfone",                       ["PES","polyethersulfone"], None),
    "PPS":   ("Poly(phenylene sulfide)",                ["PPS","polyphenylene sulfide","Ryton"], None),
    "PC":    ("Polycarbonate",                          ["polycarbonate","PC","Makrolon","Lexan"], None),
    "POM":   ("Polyoxymethylene",                       ["POM","polyacetal","acetal","Delrin","Celcon"], None),
    "PPO":   ("Poly(phenylene oxide)",                  ["PPO","polyphenylene oxide","Noryl"], None),
    "PET":   ("Poly(ethylene terephthalate)",           ["polyester","PET","Mylar","Dacron"], None),
    "PBT":   ("Poly(butylene terephthalate)",           ["PBT","polybutylene terephthalate"], None),
    "PETG":  ("Poly(ethylene terephthalate-co-1,4-cyclohexanedimethanol terephthalate)",
              ["PETG","polyethylene terephthalate glycol","PETG copolyester"], None),
    "TPX":   ("Poly(4-methylpentene-1)",               ["TPX","poly(4-methylpentene)","PMP"], None),
    "PVAC":  ("Poly(vinyl acetate)",                    ["PVAc","polyvinyl acetate"], None),
    "PVDC":  ("Poly(vinylidene chloride)",              ["PVDC","polyvinylidene chloride","Saran"], None),
}

# ─── Comprehensive IUPAC / common-name knowledge table ────────────────────────
# Keyed on canonical uppercase name fragment → (iupac, common, [common_all], subclass_hint)
POLYMER_KNOWLEDGE = {
    # Cellulosics
    "CELLIT BP-300":   ("Cellulose acetopropionate",     "cellulose acetopropionate", ["cellulose ester","CAP"], "CAP"),
    "CELLIDORA A":     ("Cellulose acetate butyrate",    "cellulose acetate butyrate",["CAB","cellulose ester"], "CAB"),
    "ETHOCEL":         ("Ethyl cellulose",               "ethyl cellulose",           ["EC","ethylcellulose"], "Ethyl cellulose"),
    "NITROCELLULOSE":  ("Cellulose nitrate",             "nitrocellulose",            ["NC","guncotton","cellulose nitrate"], "Nitrocellulose"),
    "1/2-SEC.-NITRO CELLULOSE":("Cellulose nitrate, 1/2-second grade","nitrocellulose",["NC","cellulose nitrate"],"Nitrocellulose"),
    "HPMC":            ("Hydroxypropyl methylcellulose", "hypromellose",              ["HPMC","methylhydroxypropyl cellulose"], "HPMC"),
    # Epoxy resins
    "PKHH":            ("Poly(hydroxy ether of bisphenol A)", "phenoxy resin",        ["phenoxy polymer","PKHH"], "Phenoxy resin"),
    "EPIKOTE 828":     ("Bisphenol A diglycidyl ether",  "DGEBA epoxy resin",        ["DGEBA","bisphenol-A epoxy","liquid epoxy resin"], "DGEBA epoxy"),
    "EPIKOTE 1001":    ("Bisphenol A diglycidyl ether, MW ~1000", "solid epoxy resin",["BPA epoxy","DGEBA","solid epoxy"], "BPA epoxy solid"),
    "EPIKOTE 1004":    ("Bisphenol A diglycidyl ether, MW ~1600", "solid epoxy resin",["BPA epoxy","solid epoxy resin"], "BPA epoxy solid"),
    "EPIKOTE 1007":    ("Bisphenol A diglycidyl ether, MW ~2900", "high-MW solid epoxy resin",["DGEBA","solid epoxy"], "BPA epoxy solid"),
    "EPIKOTE 1009":    ("Bisphenol A diglycidyl ether, MW ~3750", "high-MW solid epoxy resin",["DGEBA","solid epoxy"], "BPA epoxy solid"),
    "ARALDITE DY O25": ("Diglycidyl ether of polypropylene glycol","flexible epoxy diluent",["reactive epoxy diluent"],"Flexible epoxy"),
    "ARALDITE DY-025": ("Diglycidyl ether of polypropylene glycol","flexible epoxy diluent",["reactive epoxy diluent"],"Flexible epoxy"),
    # Polyurethanes
    "DESMOPHEN 651":   ("Polyester polyol",              "polyurethane polyol",       ["PU polyol","polyester polyol"], "Polyester polyol"),
    "DESMOPHEN 800":   ("Polyester polyol",              "polyurethane polyol",       ["PU polyol","polyester polyol"], "Polyester polyol"),
    "DESMOPHEN 850":   ("Polyether polyol",              "polyurethane polyol",       ["PU polyol","polyether polyol"], "Polyether polyol"),
    "DESMOPHEN 1100":  ("Polyester polyol",              "polyurethane polyol",       ["PU polyol","polyester polyol"], "Polyester polyol"),
    "DESMOPHEN 1150":  ("Polycarbonate polyol",          "polycarbonate diol",        ["polycarbonate polyol","PU polyol"], "Polycarbonate polyol"),
    "DESMOPHEN 1200":  ("Polyester polyol",              "polyurethane polyol",       ["PU polyol"], "Polyester polyol"),
    "DESMOPHEN 1700":  ("Polyester polyol, low viscosity","polyurethane polyol",      ["PU polyol","polyester polyol"], "Polyester polyol"),
    "DESMOLAC 4200":   ("Polyurethane lacquer resin",    "polyurethane lacquer resin",["PU lacquer","two-component PU"], "PU lacquer"),
    # Polyamides
    "VERSAMID 100":    ("Dimer acid-based polyamide",    "polyamide resin",           ["dimer acid polyamide","reactive polyamide"], "Dimer acid polyamide"),
    "VERSAMID 115":    ("Dimer acid-based polyamide",    "polyamide resin",           ["dimer acid polyamide","reactive polyamide"], "Dimer acid polyamide"),
    "VERSAMID 125":    ("Dimer acid-based polyamide",    "polyamide resin",           ["dimer acid polyamide","reactive polyamide"], "Dimer acid polyamide"),
    "VERSAMID 140":    ("Dimer acid-based polyamide",    "polyamide resin",           ["dimer acid polyamide","reactive polyamide"], "Dimer acid polyamide"),
    "VERSAMID 930":    ("Dimer acid-based polyamide, low viscosity","polyamide resin",["reactive polyamide"], "Dimer acid polyamide"),
    "NYLON 6":         ("Poly(caprolactam)",              "nylon 6",                  ["PA6","polyamide 6","polycaprolactam"], "PA6"),
    "NYLON 6,6":       ("Poly(hexamethylene adipamide)", "nylon 6,6",                ["PA66","polyamide 6,6"], "PA66"),
    "NYLON 11":        ("Poly(11-aminoundecanoic acid)", "nylon 11",                  ["PA11","polyamide 11"], "PA11"),
    "NYLON 12":        ("Poly(laurolactam)",              "nylon 12",                 ["PA12","polyamide 12"], "PA12"),
    "NYLON 6-6":       ("Poly(hexamethylene adipamide)", "nylon 6,6",                ["PA66","polyamide 6,6"], "PA66"),
    # Acrylics
    "MACRYNAL SM 510N":("Hydroxy-functional acrylic resin", "hydroxy acrylic resin", ["hydroxy acrylic","thermoset acrylic"], "Hydroxy acrylic"),
    "PARALOID B-72":   ("Poly(methyl acrylate-co-ethyl methacrylate)","Paraloid B-72",["acrylic copolymer","conservation resin"],"Acrylate copolymer"),
    "PARALOID B-44":   ("Poly(methyl methacrylate-co-ethyl acrylate)","Paraloid B-44",["acrylic copolymer"],"MMA/EA copolymer"),
    "PARALOID B-48N":  ("Poly(methyl methacrylate-co-ethyl acrylate)","Paraloid B-48N",["acrylic copolymer"],"MMA/EA copolymer"),
    "ACRYLOID B-44":   ("Poly(methyl methacrylate-co-ethyl acrylate)","Acryloid B-44",["acrylic copolymer"],"MMA/EA copolymer"),
    "MODAFLOW":        ("Poly(2-ethylhexyl acrylate-co-ethyl acrylate)","acrylic flow modifier",["polyacrylate flow additive"],"Flow modifier"),
    # Styrenic
    "STYRON 475M-27":  ("High-impact polystyrene",       "HIPS",                     ["high-impact polystyrene","HIPS"], "HIPS"),
    "PLIOLYTE S-100":  ("Styrene-butadiene copolymer resin","SB resin",              ["styrene-butadiene resin"], "SB resin"),
    # Natural & petroleum resins
    "PICCOPALE 110":   ("Aliphatic C5 hydrocarbon resin","aliphatic hydrocarbon resin",["C5 resin","aliphatic resin"], "C5 HC resin"),
    "PICCORONE 450L":  ("Cyclopentadiene/aromatic hydrocarbon resin","C5/C9 resin",  ["cyclopentadiene resin"], "C5/C9 resin"),
    "PENTALYN 255":    ("Glycerol ester of hydrogenated rosin","rosin ester",        ["hydrogenated rosin ester","Pentalyn"], "Rosin ester"),
    "CELLOLYN 102":    ("Pentaerythritol ester of rosin modified with cellulose","rosin-modified cellulose ester",["rosin ester"],"Rosin ester"),
    "SHELLAC":         ("Shellac resin",                  "shellac",                 ["lac","shellac varnish"], "Shellac"),
    "DAMMAR":          ("Dammar resin",                   "dammar",                  ["dammar varnish","dammer resin"], "Dammar"),
    "KAURI RESIN":     ("Kauri copal resin",              "kauri resin",             ["New Zealand kauri resin"], "Natural resin"),
    "GILSONITE":       ("Uintaite",                       "gilsonite",               ["natural asphalt","uintaite"], "Bituminous resin"),
    # Vinyl polymers
    "VIPLA KR":        ("Poly(vinyl chloride)",           "polyvinyl chloride",      ["PVC"], "PVC"),
    "CERECLOR 70":     ("Chlorinated paraffin",           "chlorinated paraffin",    ["chloroparaffin","CP70"], "Chlorinated paraffin"),
    "CHLOROPAR 40":    ("Chlorinated paraffin",           "chlorinated paraffin",    ["chloroparaffin","CP40"], "Chlorinated paraffin"),
    "LUTONAL IC":      ("Poly(isobutyl vinyl ether)",     "polyvinyl isobutyl ether",["PIB-VE","PVIBE"], "Polyvinyl ether"),
    "LUTANAL":         ("Poly(n-butyl vinyl ether)",      "polyvinyl n-butyl ether", ["PnBVE","PVBE"], "Polyvinyl ether"),
    "POLYVINYLBUTYL ETHER":("Poly(butyl vinyl ether)",   "polyvinyl butyl ether",   ["PVBE"], "Polyvinyl ether"),
    "BUTVAR B-76":     ("Poly(vinyl butyral)",            "polyvinyl butyral",       ["PVB","Butvar"], "PVB"),
    "MOWITAL B 30 H":  ("Poly(vinyl butyral)",            "polyvinyl butyral",       ["PVB","Mowital"], "PVB"),
    # Fluoropolymers
    "LUMIFLON LF-200": ("Fluoroethylene-alkyl vinyl ether copolymer","Lumiflon fluoropolymer resin",["FEVE resin","Lumiflon"],"FEVE"),
    "LUMIFLON LF-916": ("Fluoroethylene-alkyl vinyl ether copolymer","Lumiflon fluoropolymer resin",["FEVE resin"],"FEVE"),
    "KYNAR":           ("Poly(vinylidene fluoride)",      "PVDF",                    ["polyvinylidene fluoride","Kynar"], "PVDF"),
    "TEFLON PTFE":     ("Polytetrafluoroethylene",        "PTFE",                    ["Teflon","polytetrafluoroethylene"], "PTFE"),
    # Elastomers
    "NATURAL RUBBER":  ("Polyisoprene, natural",          "natural rubber",           ["NR","natural rubber","gum rubber"], "Natural rubber"),
    "NAT. RUBBER":     ("Polyisoprene, natural",          "natural rubber",           ["NR","natural rubber"], "Natural rubber"),
    "NAT RUB":         ("Polyisoprene, natural",          "natural rubber",           ["NR","natural rubber"], "Natural rubber"),
    "NEOPRENE":        ("Polychloroprene",                "neoprene",                 ["CR","polychloroprene","chloroprene rubber"], "Neoprene"),
    "CARIFLEX IR 305": ("Polyisoprene, synthetic",        "synthetic polyisoprene",   ["IR","synthetic rubber"], "Synthetic polyisoprene"),
    "HYCAR 1052":      ("Poly(acrylonitrile-co-butadiene)","nitrile rubber",         ["NBR","nitrile rubber"], "NBR"),
    "VITON A":         ("Poly(vinylidene fluoride-co-hexafluoropropylene)","Viton fluoroelastomer",["FKM","fluoroelastomer","Viton"],"FKM"),
    "HYPALON 20":      ("Chlorosulfonated polyethylene",  "chlorosulfonated PE",      ["CSM","CSPE"], "CSM"),
    "HYPALON 30":      ("Chlorosulfonated polyethylene",  "chlorosulfonated PE",      ["CSM","CSPE"], "CSM"),
    "ALLOPREN R10":    ("Chlorinated natural rubber",     "chlorinated rubber",       ["CR","chlorinated rubber"], "Chlorinated rubber"),
    "PARLON P 10":     ("Chlorinated rubber",             "chlorinated rubber",       ["CR","chloroprene rubber"], "Chlorinated rubber"),
    "POLYSAR 5630":    ("Poly(styrene-co-butadiene)",     "styrene-butadiene rubber", ["SBR"], "SBR"),
    "BUNA HULS B10":   ("Poly(butadiene-co-styrene)",     "SBR / butadiene rubber",   ["SBR","synthetic rubber"], "SBR"),
    # Polyesters & alkyds
    "SUPER BECKACITE 1001":("Alkyd resin",               "alkyd resin",              ["oil-modified alkyd"], "Alkyd"),
    # Amino resins
    "PHENODUR 373U":   ("Phenol-modified melamine resin", "amino resin",              ["phenol-amino resin","Phenodur"], "Phenol-amino resin"),
    # Biological & natural
    "LIGNIN":          ("Lignin",                         "lignin",                   ["lignosulfonate","technical lignin"], "Lignin"),
    "SHELLAC":         ("Shellac resin",                  "shellac",                  ["lac resin","bleached shellac"], "Shellac"),
    # Polyolefins
    "ALPEX":           ("Poly(ethylene-co-propylene)",    "ethylene-propylene copolymer",["EP copolymer","polyolefin wax"],"EP copolymer"),
}

# ─── Rule-based classifier ────────────────────────────────────────────────────
VALID_CLASSES = {
    "Vinyl Polymer","Acrylic","Elastomer","Polyester & Alkyd",
    "Styrenic","Epoxy Resin","Natural & Petroleum Resin","Polyurethane",
    "Biological & Other","Cellulosic Polymer","Polyolefin","Fluoropolymer",
    "Polyamide","Amino Resin","Polysulfone / PES / PPS",
    "Polyacetal / PEI / PC","Phenolic Resin",
}

RULE_BASED_CLASSES = [
    (r'FLUORO|PTFE|TEFLON|PVDF|POLYVINYLIDENE FLUORIDE|VITON|LUMIFLON|LUMFLON|KYNAR|HALAR|PCTFE|FEP\b|PFA\b|FKM\b', "Fluoropolymer", None),
    (r'POLYETHYLENE(?!\s*OXIDE)|\bHDPE\b|\bLDPE\b|\bLLDPE\b|POLYPROPYLENE|\bPIB\b|POLYISOBUTYLENE|POLYBUTENE(?!\s*TEREPHTH)|ALATHON|HOSTALEN|LUPOLEN', "Polyolefin", None),
    (r'\bTPX\b|POLY.4.METHYLPENT', "Polyolefin", "Poly(4-methylpentene)"),
    (r'SILICONE|BAYSILON|SILICON RESIN|POLY.DIMETHYLSILOXANE|PDMS', "Elastomer", "Silicone"),
    (r'\bRUBBER\b(?!\s+HYDROCARBON)|ELASTOMER|\bNBR\b|\bSBR\b|NEOPRENE|CHLOROPRENE|BUTYL RUBBER|ISOPRENE(?!.*ESTER)|POLYISOPRENE|POLYBUTADIENE|HYCAR|HYPALON|BUNA|KRATON|SANTOPRENE|THIOKOL|ALLOPRENE|BROMOBUTYL|POLYSAR|PLIOLYTE|\bEPDM\b', "Elastomer", None),
    (r'CHLORINATED RUBBER|CHLOROPAR|CERECLOR|PERGUT|ALLOPREN|PARLON|CHLORO.*POLYETHYLENE|CSM\b|CHLOROSULFONATED', "Elastomer", "Chlorinated/Halogenated Rubber"),
    (r'POLYURETHANE|URETHANE|\bTPU\b|DESMOPHEN|DESMODUR|DESMOLAC|ADIPRENE|PELLETHANE', "Polyurethane", None),
    (r'POLYAMIDE|\bNYLON\b|VERSAMID|POLYPHTHALAMIDE|KEVLAR|TORLON|ZYTEL|GRILON|\bPA 6\b|\bPA 12\b|\bPA66\b|\bPA11\b', "Polyamide", None),
    (r'EPOXY|\bEPIKOTE\b|\bEPON\b|\bARALDITE\b|BISPHENOL.*DIGLYCID|PHENOXY|\bPKHH\b|PAPHEN|NOVOLAC.*EPOXY', "Epoxy Resin", None),
    (r'ALKYD|ALKYDAL|ALFTALAT|DYNAPOL|GLYPTAL|BECKACITE|SUPER BECKACITE|URALAC|SYNRESIN|PLEXAL|VESTURIT|DUROFTAL|POLYESTER ALKYD|BECKOLIN|PLASTOKYD', "Polyester & Alkyd", "Alkyd"),
    (r'\bPET\b|\bPBT\b|\bPETG\b|POLY.ETHYLENE TEREPHTH|POLY.BUTYLENE TEREPHTH|DACRON|MYLAR|ARNITEL|PETP\b', "Polyester & Alkyd", "Saturated Polyester"),
    (r'POLYESTER(?!.*ALKYD)', "Polyester & Alkyd", None),
    (r'ACRYLIC|ACRYLATE|METHACRYLATE|\bPMMA\b|POLY.METHYL METHACRYLATE|PERSPEX|PLEXIGLAS|LUCITE|MACRYNAL|PARALOID|ACRYLOID|ELVACITE|PLEXIGUM|LAROFLEX|MODAFLOW', "Acrylic", None),
    (r'STYRENE|POLYSTYRENE|\bABS\b|\bSAN\b|\bSBS\b|\bSEBS\b|STYRON|LUSTRAN|CYCOLAC|\bHIPS\b', "Styrenic", None),
    (r'POLYVINYL|VINYL ACETATE|VINYL ALCOHOL|VINYL CHLORIDE|\bPVC\b|\bPVAC\b|\bPVAL\b|PVDC|POLYVINYLIDENE CHLORIDE|BUTVAR|MOWITAL|VINNOL|RHODOPAS|\bELVAX\b|VINYLITE|LUTONAL|LUTANAL|VIPLA|VILIT|EVOH|CHLOROPAR|CERECLOR', "Vinyl Polymer", None),
    (r'CELLUL|CELLIT\b|ETHOCEL|CELLIDORA|NITROCELLULOSE|CARBOXYMETHYL|HYDROXYETHYL|HYDROXYPROPYL|\bHPMC\b|METHYL CELLULOSE|CELLOLYN|ESTER GUM|CELLOPHAN', "Cellulosic Polymer", None),
    (r'MELAMINE|UREA.FORMALDEHYDE|AMINO RESIN|CYMEL|PHENODUR|METHOXYMETHYL|DYNOMIN|SOAMIN|PLASTOPAL|UFORMITE|URACRON', "Amino Resin", None),
    (r'PHENOL.FORMALDEHYDE|PHENOLIC|NOVOLAC|RESOLE|BAKELITE|BECKOPOX', "Phenolic Resin", None),
    (r'ROSIN|TERPENE|PETROLEUM RESIN|COUMARONE|INDENE|KAURI|DAMMAR|SHELLAC|COPAL|PICCO|PENTALYN|REGALITE|ARKON|WINGTACK|COAL TAR|TALL OIL|LIGNIN|WOOD RESIN|COLOPHONY|GILSONITE|SPERM OIL|DRYING OIL|LINSEED|TUNG OIL|SOYBEAN OIL', "Natural & Petroleum Resin", None),
    (r'POLYSULFONE|POLYETHERSULFONE|\bPPS\b|\bPSF\b|UDEL|RADEL|RYTON', "Polysulfone / PES / PPS", None),
    (r'POLYCARBONATE|\bPOM\b|POLYACETAL|POLYOXYMETHYLENE|DELRIN|CELCON|POLYETHERIMIDE|\bULTEM\b|LEXAN|MAKROLON|\bPPO\b|NORYL', "Polyacetal / PEI / PC", None),
    (r'\bPVP\b|PYRROLIDONE', "Vinyl Polymer", "PVP"),
    (r'\bEVA\b|\bEVA \d|\bELVAX\b', "Vinyl Polymer", "EVA"),
    (r'\bEVOH\b', "Vinyl Polymer", "EVOH"),
    (r'\bPAN\b|POLYACRYLONITRILE', "Acrylic", "PAN"),
    (r'\bPBMA\b', "Acrylic", "PBMA"),
    (r'\bPEMA\b', "Acrylic", "PEMA"),
    (r'\bPIBMA\b', "Acrylic", "PIBMA"),
    (r'FORMALDEH|SULFONAMIDE.*FORMALD|pTOLSULFON|SANTOLITE', "Amino Resin", None),
    (r'HYDROCARBON M|CONOCO H-|PARAPOL|PLIOLITE|LYTRON|CZ RESIN\b', "Natural & Petroleum Resin", None),
    (r'KETONE RESIN', "Natural & Petroleum Resin", "Ketone Resin"),
    (r'\bFURAN\b|FURF|FURFURYL|FURANE\b', "Phenolic Resin", "Furan Resin"),
    (r'\bDEG\b|\bDPG\b|\bTEG\b|ISOPH|TEREPH|MALEATE|PHTHAL|GLYPTAL', "Polyester & Alkyd", None),
    (r'FORMV AR|PVFORMAL|POLYVINYL FORMAL|FORMVAR', "Vinyl Polymer", "PVFormal"),
    (r'\bGEON\b|\bEXON\b|\bVYHH\b', "Vinyl Polymer", "PVC"),
    (r'\bMARBON\b', "Styrenic", None),
    (r'\bEPOCRYL\b', "Acrylic", "Epoxy Acrylate"),
    (r'CYCLOL|POLYCYCLOL', "Acrylic", None),
    (r'\bACID DEG\b|\bACID DPG\b|\bDODA\b', "Polyester & Alkyd", None),
    (r'\bBUTON\b', "Styrenic", "SBS"),
    (r'\bV AREZ\b|\bVAREZ\b|\bVCVA\b|\bVCV A\b|\bBUTV AR\b', "Vinyl Polymer", None),
    (r'\bELV AX\b|\bEV\s+A\b', "Vinyl Polymer", "EVA"),
    (r'^\s*NITRILE\b', "Elastomer", "NBR"),
    (r'^\s*CH \d{4}', "Elastomer", None),
    (r'^\s*BUTYL\s+\d', "Elastomer", "Butyl Rubber"),
    (r'^\s*PA6\b|^\s*PA 6\b', "Polyamide", None),
    (r'\bPEI\b|\bPEI\b.*PSI', "Polyacetal / PEI / PC", "PEI"),
    (r'\bPSU\b|\bPES\b', "Polysulfone / PES / PPS", None),
    (r'\bPC\b(?!\s*\d)', "Polyacetal / PEI / PC", "Polycarbonate"),
    (r'\bPOM\b|ACETAL\b', "Polyacetal / PEI / PC", "Polyacetal"),
    (r'\bPS\b(?!\s*\d)', "Styrenic", "Polystyrene"),
    (r'\bPP\b(?!\s*\d)', "Polyolefin", "Polypropylene"),
    (r'\bPE\b(?!\s*\d)', "Polyolefin", None),
    (r'MMA/|/MMA|METHYL METHACRYLATE|PLEXIGUM|PLEXIGLAS|PEMA\b|PBMA\b|PIBMA\b|POLYMETHACRYL', "Acrylic", None),
    (r'STY/|/STY\b|SMA\b', "Styrenic", None),
    (r'V A/|VA/|/V A|VINYL ACETATE/', "Vinyl Polymer", "PVAc"),
    (r'VDC/|VCL2/', "Vinyl Polymer", "PVDC"),
    (r'VBE/|PVBE\b|VINYL.*ETHER', "Vinyl Polymer", "PVE"),
    (r'\bPVF\b|POLY.VINYL FLUORIDE', "Fluoropolymer", None),
    (r'\bPVOH\b|\bPVAL\b', "Vinyl Polymer", "PVOH"),
    (r'\bR BUTYL\b|\bR CSM\b|\bR ACM\b|\bR EPDM\b|\bR FKM\b|\bR NR\b', "Elastomer", None),
    (r'^R\s+.*RUBBER|^R\s+.*BUTYL|^R\s+.*EPDM|^R\s+.*FKM|^R\s+.*CSM', "Elastomer", None),
    (r'^R\s+.*POLYURETHANE|^R\s+.*\bPU\b|\bR AU\b|\bR PEU\b', "Polyurethane", None),
    (r'^R\s+.*POLYSULFONE|^R\s+.*PSU|\bR POLYSULPHONE\b', "Polysulfone / PES / PPS", None),
    (r'^R\s+.*POLYAMIDE|^R\s+.*PA\d|\bR PA12\b', "Polyamide", None),
    (r'^R\s+.*POLYESTER|^R\s+.*TEREPHTH|\bR ISOPHTHALIC\b|\bR TEREPHTALIC\b', "Polyester & Alkyd", None),
    (r'^R\s+.*POLYCARBONATE|^R\s+.*PPO|\bR POLYPHENYLENEOXIDE\b', "Polyacetal / PEI / PC", None),
    (r'^R\s+.*POLYSULPHIDE|\bR T SULPHIDE\b', "Polysulfone / PES / PPS", "Polysulfide"),
    (r'^R\s+.*FLUOROCARBON|^R\s+.*TETFL|^R\s+.*FQ FL|\bR FQ\b|\bR TFP\b', "Fluoropolymer", None),
    (r'\bR TPX\b|TPX\b', "Polyolefin", "Poly(4-methylpentene)"),
    (r'\bR EBONITE\b', "Elastomer", "Ebonite"),
    (r'R\+H\b', "Acrylic", None),
    (r'^MAA/', "Acrylic", None),
    (r'^BMA/', "Acrylic", None),
    (r'^V\s+A/', "Vinyl Polymer", "PVAc copolymer"),
    (r'ZINK SILICATE|ZINC SILICATE', "Biological & Other", "Inorganic"),
    (r'IN WATER|WATER\s*\+', "Biological & Other", "Aqueous"),
    (r'MONOMER\b', "Biological & Other", "Monomer"),
    (r'ACRYLAMIDE', "Acrylic", "Polyacrylamide"),
    (r'\bPECTFE\b|\bPCTFE\b', "Fluoropolymer", None),
    (r'POLYETHYLENEOXIDE|POLYETHYLENE OXIDE|PEO\b', "Polyolefin", "PEO"),
    (r'\bECO\b.*RUBBER|\bR ECO\b', "Elastomer", "ECO"),
    (r'BETHOXAZIN|BENZOXAZIN', "Phenolic Resin", "Benzoxazine"),
    (r'\bAMOCO\b|\bTOPAS\b', "Polyolefin", None),
    (r'CELL\.\s*ACET|\bETHCEL\b|\bCELLOPHAN\b', "Cellulosic Polymer", None),
    (r'KOPPERS', "Phenolic Resin", None),
    (r'\bSINCLAIR\b|\bCRYPLEX\b|\bVYSET\b', "Acrylic", None),
    (r'^\bBE \d', "Epoxy Resin", None),
    (r'SHELL X-\d|SHELL POLYALD', "Polyacetal / PEI / PC", "Polyaldehyde"),
    (r'\bPOMH\b|\bPOMC\b', "Polyacetal / PEI / PC", "Polyacetal"),
    (r'\bSHELL POLYALD\b', "Polyacetal / PEI / PC", "Polyaldehyde"),
    (r'POLYIMIDE|\bPI\b|KAPTON', "Polysulfone / PES / PPS", "Polyimide"),
    (r'\bCRODA\b', "Acrylic", "Thermoset Acrylic"),
    (r'\bBAREx\b', "Acrylic", None),
    (r'\bFURANE\b', "Phenolic Resin", "Furan Resin"),
    (r'NATURAL RUBBER|NAT\.\s*RUBBER|NAT\s+RUB|GUM RUBBER', "Elastomer", "Natural rubber"),
    (r'\bCARIFLEX\b', "Elastomer", "Synthetic polyisoprene"),
    (r'\bNEOPRENE\b', "Elastomer", "Neoprene"),
    (r'\bMOPLEN\b|\bZEONEX\b|\bSURLYN\b', "Polyolefin", None),
    (r'\bHYTREL\b(?!.*POLYESTER)', "Elastomer", "TPE-E"),
    (r'\bESTANE\b', "Polyurethane", "TPU"),
    (r'\bKRATON\b', "Styrenic", "SEBS/SBS"),
    (r'\bTOLONATE\b|\bSUPRASEC\b', "Polyurethane", None),
    (r'\bLIGNIN\b', "Natural & Petroleum Resin", "Lignin"),
    (r'\bZEIN\b', "Biological & Other", "Protein"),
    (r'\bCASEIN\b', "Biological & Other", "Protein"),
    (r'\bALPEX\b', "Natural & Petroleum Resin", None),
    (r'\bPLIOLYTE\b', "Natural & Petroleum Resin", None),
    # PUR / PU variants (polyurethane abbreviations)
    (r'^\s*PUR\b|^\s*PU\b|\bPUR\s+CR\b|\bPUR\s+SOL\b|\bPU\s+CR\b', "Polyurethane", None),
    # PV AC, PVEE, PVIBE (vinyl ether / acetate abbreviations)
    (r'^\s*PV\s+AC\b', "Vinyl Polymer", "PVAc"),
    (r'\bPVEE\b', "Vinyl Polymer", "PVEE"),
    (r'\bPVIBE\b', "Vinyl Polymer", "PVIBE"),
    # PVETHYLETHER → vinyl ether polymer
    (r'PVETHYL.*ETHER|POLYVINYLETHYLETHER', "Vinyl Polymer", "Polyvinyl ethyl ether"),
    # SARANEX — PVDC/LDPE film
    (r'\bSARANEX\b|\bSARAN\b', "Vinyl Polymer", "PVDC"),
    # ACETALHOMO-DUO → polyacetal
    (r'ACETALHOMO|ACETAL.*DUO', "Polyacetal / PEI / PC", "Polyacetal"),
    # Polyester monomers / intermediate names containing known motifs
    (r'ADIP.*TEREP|TEREP.*ADIP|VITEL|HYD BIS|PENTA.*BENZ.*MAL|HEXADECYL.*TRIME|ACID DEG|ACID DPG', "Polyester & Alkyd", None),
    (r'FUM.*ISPH|ISPH.*FUM|BIS A.*FUM|FUM.*BIS A', "Polyester & Alkyd", "Unsaturated Polyester"),
    # STY MAL ANH → styrenic (styrene-maleic anhydride)
    (r'STY.*MAL|MAL.*ANH.*STY|STYRENE.*MALEI', "Styrenic", "SMA"),
    # BAREX → acrylonitrile copolymer (acrylic)
    (r'\bBAREX\b', "Acrylic", "Acrylonitrile copolymer"),
    # R ETHYLENE/PROPYLENE → elastomer (EPDM)
    (r'^R\s+ETHYLENE.*PROPYLENE|^R\s+PROP.*ETHYLENE', "Elastomer", "EPDM"),
    # R HET RESIN → phenolic/epoxy (HET resin = chlorendic acid based)
    (r'\bHET RESIN\b|^R\s+HET', "Phenolic Resin", "HET resin"),
    # ESTIMATE DRIED OIL → natural resin
    (r'DRIED OIL|ESTIMATE DRIED', "Natural & Petroleum Resin", "Drying oil"),
]

# ─── PubChem CAS lookup (with cache) ─────────────────────────────────────────
_pubchem_cache = {}


def pubchem_cas_lookup(name: str, delay: float = 0.3) -> tuple[str | None, str | None]:
    """Return (cas, cid_str) from PubChem by compound name. Returns (None, None) on miss."""
    if name in _pubchem_cache:
        return _pubchem_cache[name]

    time.sleep(delay)
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{requests.utils.quote(name)}/JSON"
    try:
        r = requests.get(url, timeout=12)
        if r.status_code != 200:
            _pubchem_cache[name] = (None, None)
            return None, None
        data = r.json()
        cid = None
        for c in data.get("PC_Compounds", []):
            cid = c.get("id", {}).get("id", {}).get("cid")
            if cid:
                break
        if not cid:
            _pubchem_cache[name] = (None, None)
            return None, None

        # Get CAS from synonyms
        time.sleep(delay)
        syn_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/synonyms/JSON"
        sr = requests.get(syn_url, timeout=12)
        cas = None
        if sr.status_code == 200:
            syns = sr.json().get("InformationList", {}).get("Information", [])
            for entry in syns:
                for s in entry.get("Synonym", []):
                    if re.match(r'^\d{1,7}-\d{2}-\d$', s):
                        cas = s
                        break
                if cas:
                    break
        result = (cas, str(cid))
        _pubchem_cache[name] = result
        return result
    except Exception:
        _pubchem_cache[name] = (None, None)
        return None, None


# ─── STEP 0: PRE-CLASSIFICATION ───────────────────────────────────────────────

def pre_classify(name: str) -> dict:
    name_upper = name.upper().strip()
    result = {"route": "standard", "class_predicted": None, "brand_prefix": None}

    for term in OUT_OF_SCOPE:
        if term in name_upper:
            result["route"] = "flag_out_of_scope"
            result["class_predicted"] = "Biological & Other"
            return result

    if name_upper.startswith("R "):
        result["route"] = "resistance_data"
        return result

    if re.search(r'\d+%\s*$', name_upper):
        result["route"] = "concentration_series"

    if re.search(r'\b(\d+)\s*(MIN|HR|HOUR)', name_upper):
        result["route"] = "time_series"
        return result

    if re.match(r'^[A-Z]{1,6}/[A-Z]{1,6}', name_upper):
        result["route"] = "copolymer"
        return result

    for prefix, cls in BRAND_CLASS_MAP.items():
        if name_upper.startswith(prefix):
            result["route"] = "trade_name"
            result["class_predicted"] = cls
            result["brand_prefix"] = prefix
            return result

    return result


# ─── STEP 2: HSP ANOMALY FLAGS ────────────────────────────────────────────────

def hsp_anomaly_flags(row: dict) -> list:
    flags = []
    try:
        dd = float(row.get("dD") or 0)
        dp = float(row.get("dP") or 0)
        dh = float(row.get("dH") or 0)
        r  = float(row.get("radius") or 0)
    except (ValueError, TypeError):
        return flags
    if dp < 0:   flags.append("[HSP] hsp_flag_dp_negative")
    if dh < 0:   flags.append("[HSP] hsp_flag_dh_negative")
    if dd < 10:  flags.append("[HSP] hsp_flag_dd_low")
    if dd > 28:  flags.append("[HSP] hsp_flag_dd_high")
    if r > 30:   flags.append("[HSP] hsp_flag_r_large")
    if abs(dp) < 1.0 and abs(dh) < 1.0:
        flags.append("[HSP] near-nonpolar")
    return flags


# ─── STEP 3: NAME CLEANING & RESOLUTION ──────────────────────────────────────

def resolve_name(name: str, pre: dict) -> dict:
    """Produce name_clean, name_iupac, name_common, name_common_all, name_acronyms."""
    original = name.strip()
    name_upper = original.upper()

    # --- name_clean: strip uncertainty markers, normalize whitespace, apply caps ---
    name_clean = re.sub(r'\s+', ' ', original).strip()
    source_uncertainty = False
    if '?' in name_clean or 'QUESTIONABLE' in name_clean.upper():
        source_uncertainty = True
        name_clean = re.sub(r'\?', '', name_clean)
        name_clean = re.sub(r'\(QUESTIONABLE VALUES?\)', '', name_clean, flags=re.IGNORECASE).strip()
        name_clean = re.sub(r'\s+', ' ', name_clean).strip()

    name_clean = re.sub(r'\s*\+/-\s*(OK|NOT OK)\s*$', '', name_clean, flags=re.IGNORECASE).strip()
    name_clean = re.sub(r'\s*\(NOT GOOD[^)]*\)', '', name_clean, flags=re.IGNORECASE).strip()

    # Extract parenthetical synonyms (text only, not %, not numeric)
    extra_synonyms = []
    paren_m = re.search(r'\(([^)]+)\)', name_clean)
    if paren_m:
        inner = paren_m.group(1).strip()
        if re.match(r'^[A-Za-z]', inner) and '%' not in inner and not re.match(r'^\d', inner):
            extra_synonyms.append(inner)
            name_clean = re.sub(r'\s*\([^)]+\)\s*', ' ', name_clean).strip()

    # Detect if it's a preserved abbreviation
    name_clean_upper = name_clean.upper()
    if name_clean_upper in PRESERVE_AS_IS:
        name_clean = name_clean_upper  # preserve all-caps
    elif pre.get("brand_prefix") and pre["brand_prefix"] in BRAND_CAPS:
        bp = pre["brand_prefix"]
        display_prefix = BRAND_CAPS[bp]
        suffix = name_clean[len(bp):].strip() if name_clean.upper().startswith(bp) else name_clean[len(bp):].strip()
        # Re-apply from original to preserve grade numbers correctly
        orig_upper = original.upper()
        if orig_upper.startswith(bp):
            suffix_raw = original[len(bp):].strip()
            # Remove uncertainty chars from suffix
            suffix_raw = re.sub(r'\?', '', suffix_raw).strip()
        else:
            suffix_raw = suffix
        name_clean = f"{display_prefix} {suffix_raw}".strip()
    # else: leave as-is (trade names with no brand match keep original capitalisation style)

    # --- name_iupac, name_common, name_common_all, name_acronyms ---
    name_iupac     = None
    name_common    = None
    name_common_all = []
    name_acronyms  = []

    # 1. Check the comprehensive knowledge table
    for key, val in POLYMER_KNOWLEDGE.items():
        if key in name_upper:
            name_iupac, name_common, name_common_all, _sc = val
            break

    # 2. Check the acronym table (exact match on cleaned upper name)
    nc_upper = name_clean_upper.strip()
    if nc_upper in ACRONYM_TABLE:
        iupac, commons, _ = ACRONYM_TABLE[nc_upper]
        name_iupac = name_iupac or iupac
        if not name_common_all:
            name_common = commons[0] if commons else name_clean
            name_common_all = list(commons)
        if nc_upper not in name_acronyms:
            name_acronyms.append(nc_upper)

    # 3. Brand-prefix → generic acronym
    brand_acronym_map = {
        "DESMOPHEN": "PU", "DESMODUR": "PU", "DESMOLAC": "PU",
        "EPIKOTE": "EP", "EPON": "EP", "ARALDITE": "EP",
        "VERSAMID": "PA",
    }
    bp = pre.get("brand_prefix")
    if bp and bp in brand_acronym_map:
        acr = brand_acronym_map[bp]
        if acr not in name_acronyms:
            name_acronyms.append(acr)

    # 4. Fallback for any entry still missing name_iupac / name_common
    if not name_iupac:
        if re.match(r'^poly\(', name_clean.lower()):
            name_iupac = name_clean  # already a systematic name
        elif pre.get("route") == "systematic_chemical":
            name_iupac = name_clean

    if not name_common:
        name_common = name_clean

    # Add extra synonyms from parenthetical
    for s in extra_synonyms:
        if s.lower() not in [x.lower() for x in name_common_all]:
            name_common_all.append(s)

    # Dedup name_common_all
    seen = set()
    deduped = []
    for v in name_common_all:
        vn = v.lower().strip()
        if vn and vn not in seen:
            seen.add(vn)
            deduped.append(v)
    name_common_all_str = "; ".join(deduped) if deduped else name_common or name_clean

    return {
        "name_clean": name_clean,
        "name_iupac": name_iupac or "",
        "name_common": name_common or name_clean,
        "name_common_all": name_common_all_str,
        "name_acronyms": "; ".join(name_acronyms) if name_acronyms else "",
        "source_uncertainty": source_uncertainty,
    }


# ─── STEP 9: CLASSIFICATION ───────────────────────────────────────────────────

def classify(name_upper: str, class_predicted: str = None) -> dict:
    """Rule-based classification, respecting brand-predicted class."""
    if class_predicted and class_predicted in VALID_CLASSES:
        return {"class": class_predicted, "subclass": None,
                "notes": "class from brand prefix mapping"}

    # Strip condition modifiers for matching
    s = re.sub(r'\s+(CR|SOL|SW)\s*$', '', name_upper).strip()
    s = re.sub(r'\s+\d+\s*(MIN|HR|HOUR).*$', '', s).strip()
    s = re.sub(r'\s*\(\d+%\)\s*$', '', s).strip()
    s = re.sub(r'\s*\d+%\s*$', '', s).strip()

    for pattern, cls, subclass in RULE_BASED_CLASSES:
        if re.search(pattern, s) or re.search(pattern, name_upper):
            return {"class": cls, "subclass": subclass,
                    "notes": f"rule: {pattern[:40]}"}

    return {"class": "Biological & Other", "subclass": None,
            "notes": "no rule matched"}


# ─── STEP 10: PRODUCT URL ─────────────────────────────────────────────────────

def product_url_for(name_upper: str, name_type: str, cas: str, pubchem_cid: str) -> str:
    """Return a product URL for the entry."""
    if pubchem_cid:
        return f"https://pubchem.ncbi.nlm.nih.gov/compound/{pubchem_cid}"
    return ""


# ─── LOAD V4 CAS CHECKPOINT ──────────────────────────────────────────────────

def load_v4_cas() -> dict:
    """Load CAS results from v4 checkpoint to avoid re-querying PubChem."""
    if not V4_CKPT.exists():
        return {}
    with open(V4_CKPT) as f:
        d = json.load(f)
    # v4 checkpoint stores processed_rows as a list; build name→cas map
    cas_map = {}
    cas_cache = d.get("cas_cache", {})
    for name, cas in cas_cache.items():
        if cas:
            cas_map[name.upper()] = cas
    # Also extract from processed rows
    for row in d.get("processed_rows", []):
        if isinstance(row, dict) and row.get("cas"):
            cas_map[row.get("name_input","").upper()] = row["cas"]
    return cas_map


# ─── MAIN PIPELINE ────────────────────────────────────────────────────────────

def run():
    print("=" * 60)
    print("HSP Polymer Pipeline v5")
    print("=" * 60)

    # Step 1: Load
    df = pd.read_csv(RAW_CSV)
    print(f"Loaded {len(df)} rows, columns: {list(df.columns)}")

    # Rename columns
    col_map = {c.lower(): c for c in df.columns}
    rename = {}
    for old, new in [("material","name"),("d","dD"),("p","dP"),("h","dH"),("ro","radius")]:
        if old in col_map:
            rename[col_map[old]] = new
    df = df.rename(columns=rename)
    df = df.drop(columns=[c for c in df.columns if c.lower() == "no"], errors="ignore")
    df["name"] = df["name"].astype(str).str.strip()

    # Dedup
    dup_mask = df.duplicated(subset=["name","dD","dP","dH"], keep="first")
    print(f"Full duplicates removed: {dup_mask.sum()}")
    df = df[~dup_mask].copy()
    print(f"Rows after dedup: {len(df)}")

    # Load v4 CAS cache
    v4_cas = load_v4_cas()
    print(f"Loaded {len(v4_cas)} CAS entries from v4 checkpoint")

    rows_out = []
    pubchem_hits = 0
    cas_found = 0
    out_of_scope_count = 0

    for idx, row in df.iterrows():
        name_input = row["name"]
        name_upper = name_input.upper().strip()
        notes_parts = []

        # Step 0
        pre = pre_classify(name_input)
        notes_parts.append(f"[PRE] route={pre['route']}")

        if pre["route"] == "flag_out_of_scope":
            out_of_scope_count += 1
            notes_parts.append("[PRE] out-of-scope entry")

        # Step 2
        hsp_row = {"dD": row.get("dD"), "dP": row.get("dP"), "dH": row.get("dH"), "radius": row.get("radius")}
        flags = hsp_anomaly_flags(hsp_row)
        notes_parts.extend(flags)

        # Step 3
        resolved = resolve_name(name_input, pre)
        if resolved["source_uncertainty"]:
            notes_parts.append("[NAME] source uncertainty (?)")

        # Step 4: CAS
        cas = None
        pubchem_cid = None

        # Try v4 cache first
        if name_upper in v4_cas:
            cas = v4_cas[name_upper]
            notes_parts.append(f"[CAS] from v4 cache: {cas}")
            cas_found += 1

        # PubChem lookup for abbreviations (small molecules like PMMA have PubChem entries)
        if not cas:
            nc_upper = resolved["name_clean"].upper()
            if nc_upper in ACRONYM_TABLE and ACRONYM_TABLE[nc_upper][2]:
                pubchem_cid = str(ACRONYM_TABLE[nc_upper][2])
                notes_parts.append(f"[CAS] PubChem CID from acronym table: {pubchem_cid}")

        if not cas and not pubchem_cid and pre.get("route") not in ("trade_name", "time_series", "resistance_data", "concentration_series", "flag_out_of_scope"):
            # Try PubChem for standard entries
            cas_try, cid_try = pubchem_cas_lookup(resolved["name_clean"])
            if cas_try:
                cas = cas_try
                pubchem_cid = cid_try
                notes_parts.append(f"[CAS] found via PubChem: {cas}")
                cas_found += 1
                pubchem_hits += 1
            elif cid_try:
                pubchem_cid = cid_try
                notes_parts.append(f"[CAS] CID found: {cid_try}, CAS not in synonyms")
                pubchem_hits += 1
            else:
                notes_parts.append("[CAS] not found")

        if not cas:
            notes_parts.append("[CAS] not found")

        # Step 9: Classification
        cl = classify(name_upper, pre.get("class_predicted"))
        notes_parts.append(f"[CLASS] {cl['notes']}")

        # Subclass refinement from knowledge table
        subclass = cl.get("subclass")
        for key, val in POLYMER_KNOWLEDGE.items():
            if key in name_upper:
                subclass = val[3] or subclass
                break

        # Step 10: Product URL
        prod_url = product_url_for(name_upper, pre.get("route"), cas, pubchem_cid)

        out_row = {
            "name_input":      name_input,
            "name_clean":      resolved["name_clean"],
            "name_iupac":      resolved["name_iupac"],
            "name_common":     resolved["name_common"],
            "name_common_all": resolved["name_common_all"],
            "name_acronyms":   resolved["name_acronyms"],
            "cas":             cas or "",
            "product_url":     prod_url,
            "tds_url":         "",
            "sds_url":         "",
            "dD":              row.get("dD", ""),
            "dP":              row.get("dP", ""),
            "dH":              row.get("dH", ""),
            "radius":          row.get("radius", ""),
            "class":           cl["class"],
            "subclass":        subclass or "",
            "processing_notes": "; ".join(notes_parts),
        }
        rows_out.append(out_row)

    print(f"PubChem hits: {pubchem_hits}, CAS found: {cas_found}")
    print(f"Out-of-scope: {out_of_scope_count}")

    enriched_df = pd.DataFrame(rows_out)

    # Write polymers_enriched.csv (full pipeline output)
    enriched_df.to_csv(ENRICHED, index=False)
    print(f"Wrote enriched: {ENRICHED} ({len(enriched_df)} rows)")

    # Write polymers.csv (database-ready, matching generate_html.py schema)
    # name = name_clean (display name), not name_common
    db_rows = []
    for row in rows_out:
        db_rows.append({
            "name":         row["name_clean"],        # display name in UI
            "name_input":   row["name_input"],         # original for reference
            "cas_number":   row["cas"],
            "delta_d":      row["dD"],
            "delta_p":      row["dP"],
            "delta_h":      row["dH"],
            "radius":       row["radius"],
            "type":         row["class"],
            "confidence":   0.9,
            "source_count": 1,
            "source":       "hsp_polymers_5",
            "source_url":   "https://github.com/jtreeder/Materialism/blob/claude/hansen-solubility-planning-D5iok/data/datasets/hspip_polymers/raw/HSPiP_polymers.csv",
            "name_iupac":   row["name_iupac"],
            "name_common":  row["name_common"],
            "name_common_all": row["name_common_all"],
            "name_acronyms": row["name_acronyms"],
            "subclass":     row["subclass"],
            "product_url":  row["product_url"],
        })
    db_df = pd.DataFrame(db_rows)
    db_df.to_csv(DB_CSV, index=False)
    print(f"Wrote database CSV: {DB_CSV} ({len(db_df)} rows)")

    # Write metadata.json
    meta = {
        "id": "hsp_polymers_5",
        "name": "HSP Polymers 5",
        "source_url": "https://github.com/jtreeder/Materialism/blob/claude/hansen-solubility-planning-D5iok/data/datasets/hspip_polymers/raw/HSPiP_polymers.csv",
        "description": (
            "Re-processed HSPiP polymer database (pipeline v5). "
            "Adds name_clean as explicit output column per pipeline spec. "
            "Comprehensive IUPAC name knowledge table, "
            "13-class polymer classification, CAS lookup via PubChem, "
            "HSP plausibility flags, processing audit trail."
        ),
        "imported_at": "2026-03-08T00:00:00+00:00",
        "chemical_count": 0,
        "polymer_count": len(enriched_df),
        "fields_available": [
            "name_input","name_clean","name_iupac","name_common",
            "name_common_all","name_acronyms","cas","product_url",
            "tds_url","sds_url","dD","dP","dH","radius",
            "class","subclass","processing_notes"
        ],
        "quality_notes": (
            f"Pipeline v5: name_clean added per spec. "
            f"13-class classification (rule-based). "
            f"CAS found: {cas_found}/{len(enriched_df)}. "
            f"PubChem queries: {pubchem_hits}."
        ),
        "active": True,
        "confidence_tier": 0.9,
    }
    with open(OUT_DIR / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Wrote metadata: {OUT_DIR}/metadata.json")

    # Summary stats
    cls_counts = enriched_df["class"].value_counts()
    print("\nClass distribution:")
    for cls, cnt in cls_counts.items():
        print(f"  {cls}: {cnt}")

    return enriched_df


if __name__ == "__main__":
    run()
