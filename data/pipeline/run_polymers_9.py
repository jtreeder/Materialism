"""
Materialism HSP Database Pipeline — HSP_polymers_9
Processes: a2only.pdf → HSP_polymers_9 dataset

Uses PyMuPDF (fitz) instead of pdfplumber due to environment constraints.
Output format matches hsp_polymers_8 schema.
"""

import re, os, json
import pandas as pd
import fitz  # pymupdf

PDF_PATH = os.path.join(os.path.dirname(__file__), '..', 'raw', 'a2only.pdf')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'datasets', 'hsp_polymers_9')
MANIFEST_PATH = os.path.join(os.path.dirname(__file__), '..', 'manifest.json')
SOURCE_URL = "https://github.com/jtreeder/Materialism/blob/claude/hansen-solubility-planning-D5iok/data/raw/a2only.pdf"

# ─── FIX GROUP 6 ─────────────────────────────────────────────────────────────

FIX_GROUP_6 = {
    'ARALDITE DY O25':       'ARALDITE DY-025',
    'LUTANAL I60':           'LUTONAL I60',
    'STYRON 44OM-27 MOD PS': 'STYRON 440M-27 MOD PS',
    'LUMFLON LF200':         'LUMIFLON LF-200',
    'LUMFLON LF916':         'LUMIFLON LF-916',
}

# ─── ABBREVIATION SEED TABLE ─────────────────────────────────────────────────

ABBREV_TO_IUPAC = {
    'PTFE':   ('polytetrafluoroethylene', 'poly(1,1,2,2-tetrafluoroethylene)', 'Teflon; PTFE', 'PTFE', '9002-84-0'),
    'PVDF':   ('poly(vinylidene fluoride)', 'poly(1,1-difluoroethylene)', 'PVDF; Kynar', 'PVDF', '24937-79-9'),
    'PFA':    ('perfluoroalkoxy polymer', None, 'PFA', 'PFA', '26655-00-5'),
    'FEP':    ('fluorinated ethylene propylene', 'poly(tetrafluoroethylene-co-hexafluoropropylene)', 'FEP', 'FEP', '25067-11-2'),
    'ETFE':   ('ethylene-tetrafluoroethylene copolymer', None, 'ETFE; Tefzel', 'ETFE', '25038-71-5'),
    'ECTFE':  ('ethylene-chlorotrifluoroethylene copolymer', None, 'ECTFE; Halar', 'ECTFE', '25101-45-5'),
    'PCTFE':  ('polychlorotrifluoroethylene', None, 'PCTFE; Kel-F', 'PCTFE', '9002-83-9'),
    'PE':     ('polyethylene', None, 'PE; polyethylene', 'PE', '9002-88-4'),
    'HDPE':   ('high-density polyethylene', None, 'HDPE; HD-PE', 'HDPE', '9002-88-4'),
    'LDPE':   ('low-density polyethylene', None, 'LDPE; LD-PE', 'LDPE', '9002-88-4'),
    'LLDPE':  ('linear low-density polyethylene', None, 'LLDPE', 'LLDPE', '9002-88-4'),
    'PP':     ('polypropylene', 'poly(propan-1-yl)', 'PP; polypropylene', 'PP', '9003-07-0'),
    'PIB':    ('polyisobutylene', 'poly(2-methylprop-1-ene)', 'PIB; polyisobutylene', 'PIB', '9003-27-4'),
    'PS':     ('polystyrene', 'poly(ethenylbenzene)', 'PS; polystyrene', 'PS', '9003-53-6'),
    'HIPS':   ('high-impact polystyrene', None, 'HIPS; rubber-toughened PS', 'HIPS', '9003-53-6'),
    'ABS':    ('acrylonitrile-butadiene-styrene', None, 'ABS', 'ABS', '9003-56-9'),
    'SAN':    ('styrene-acrylonitrile copolymer', None, 'SAN', 'SAN', '9003-54-7'),
    'ASA':    ('acrylonitrile-styrene-acrylate', None, 'ASA', 'ASA', '26299-14-9'),
    'PMMA':   ('poly(methyl methacrylate)', 'poly(methyl 2-methylprop-2-enoate)', 'PMMA; acrylic glass; Plexiglas; Perspex; Lucite', 'PMMA', '9011-14-7'),
    'PAN':    ('polyacrylonitrile', 'poly(prop-2-enenitrile)', 'PAN; polyacrylonitrile; Orlon', 'PAN', '25014-41-9'),
    'PVC':    ('poly(vinyl chloride)', 'poly(chloroethylene)', 'PVC; vinyl', 'PVC', '9002-86-2'),
    'PVDC':   ('poly(vinylidene chloride)', 'poly(1,1-dichloroethylene)', 'PVDC; Saran', 'PVDC', '9002-85-1'),
    'CPVC':   ('chlorinated poly(vinyl chloride)', None, 'CPVC', 'CPVC', '68648-82-8'),
    'PVCA':   ('poly(vinyl chloride-co-vinyl acetate)', None, 'PVCA; vinyl chloride-vinyl acetate copolymer', 'PVCA', '9003-22-9'),
    'PET':    ('poly(ethylene terephthalate)', 'poly(ethylene benzene-1,4-dicarboxylate)', 'PET; Dacron; Mylar', 'PET', '25038-59-9'),
    'PBT':    ('poly(butylene terephthalate)', 'poly(butane-1,4-diyl benzene-1,4-dicarboxylate)', 'PBT; Valox', 'PBT', '26062-94-2'),
    'PEN':    ('poly(ethylene naphthalate)', None, 'PEN', 'PEN', '25853-85-4'),
    'PCT':    ('poly(cyclohexanedimethylene terephthalate)', None, 'PCT; Thermx', 'PCT', '25037-73-4'),
    'PA6':    ('polyamide 6', 'poly(azepan-2-one)', 'PA6; nylon 6; polycaprolactam', 'PA6', '25038-54-4'),
    'PA66':   ('polyamide 6,6', None, 'PA66; nylon 6,6', 'PA66', '32131-17-2'),
    'PA11':   ('polyamide 11', None, 'PA11; nylon 11; Rilsan', 'PA11', '25035-04-5'),
    'PA12':   ('polyamide 12', None, 'PA12; nylon 12', 'PA12', '24937-16-4'),
    'PC':     ('polycarbonate', 'poly(oxy-1,4-phenyleneisopropylidene-1,4-phenyleneoxycarbonyl)', 'PC; bisphenol A polycarbonate; Lexan; Makrolon', 'PC', '25037-45-0'),
    'POM':    ('polyoxymethylene', 'poly(methylene oxide)', 'POM; acetal; polyacetal; Delrin; Celcon', 'POM; acetal', '9002-81-7'),
    'PU':     ('polyurethane', None, 'PU; PUR; polyurethane', 'PU; PUR', None),
    'PUR':    ('polyurethane', None, 'PU; PUR; polyurethane', 'PU; PUR', None),
    'PSU':    ('polysulfone', None, 'PSU; polysulfone; Udel', 'PSU', '25135-51-7'),
    'PES':    ('poly(ether sulfone)', None, 'PES; polyethersulfone; Victrex PES', 'PES', '25667-42-9'),
    'PEEK':   ('poly(ether ether ketone)', None, 'PEEK; Victrex', 'PEEK', '29658-26-2'),
    'PEI':    ('poly(ether imide)', None, 'PEI; Ultem', 'PEI', '61128-46-9'),
    'PPS':    ('poly(phenylene sulfide)', None, 'PPS; Ryton; Fortron', 'PPS', '26125-40-6'),
    'PPO':    ('poly(phenylene oxide)', 'poly(2,6-dimethyl-1,4-phenylene oxide)', 'PPO; PPE; Noryl (PPO/PS blend)', 'PPO; PPE', '25134-01-4'),
    'PI':     ('polyimide', None, 'PI; polyimide; Kapton', 'PI', None),
    'NC':     ('nitrocellulose', 'cellulose nitrate', 'NC; nitrocellulose; cellulose nitrate; pyroxylin', 'NC', '9004-70-0'),
    'CA':     ('cellulose acetate', None, 'CA; cellulose acetate', 'CA', '9004-35-7'),
    'CAB':    ('cellulose acetate butyrate', None, 'CAB', 'CAB', '9004-36-8'),
    'CAP':    ('cellulose acetate propionate', None, 'CAP', 'CAP', '9004-39-1'),
    'EC':     ('ethyl cellulose', None, 'EC; ethyl cellulose; Ethocel', 'EC', '9004-57-3'),
    'CMC':    ('carboxymethyl cellulose', None, 'CMC; carboxymethylcellulose; cellulose gum', 'CMC', '9000-11-7'),
    'HEC':    ('hydroxyethyl cellulose', None, 'HEC; hydroxyethylcellulose; Natrosol', 'HEC', '9004-62-0'),
    'HPMC':   ('hydroxypropyl methyl cellulose', None, 'HPMC; hypromellose', 'HPMC', '9004-65-3'),
    'PVA':    ('poly(vinyl alcohol)', None, 'PVA; PVOH; Mowiol', 'PVA; PVOH', '9002-89-5'),
    'PVAc':   ('poly(vinyl acetate)', 'poly(ethenyl acetate)', 'PVAc; polyvinyl acetate', 'PVAc', '9003-20-7'),
    'PVB':    ('poly(vinyl butyral)', None, 'PVB; Butvar; Mowital', 'PVB', '63148-65-2'),
    'PVF':    ('poly(vinyl fluoride)', None, 'PVF; Tedlar', 'PVF', '24981-14-4'),
    'PVP':    ('poly(vinylpyrrolidone)', 'poly(1-vinylpyrrolidin-2-one)', 'PVP; polyvidone; povidone; Kollidon; Plasdone', 'PVP', '9003-39-8'),
    'NR':     ('natural rubber', 'cis-1,4-polyisoprene', 'NR; natural rubber; latex', 'NR', '9006-04-6'),
    'IR':     ('synthetic polyisoprene', 'cis-1,4-polyisoprene', 'IR; synthetic polyisoprene; Cariflex IR', 'IR', '9003-31-0'),
    'BR':     ('polybutadiene', 'poly(buta-1,3-diene)', 'BR; polybutadiene rubber', 'BR', '9003-17-2'),
    'SBR':    ('styrene-butadiene rubber', None, 'SBR; styrene-butadiene rubber; Buna S', 'SBR', '9003-55-8'),
    'NBR':    ('nitrile butadiene rubber', 'poly(acrylonitrile-co-butadiene)', 'NBR; nitrile rubber; Buna N; acrylonitrile-butadiene rubber', 'NBR', '9003-18-3'),
    'EPDM':   ('ethylene propylene diene rubber', None, 'EPDM; ethylene propylene diene monomer rubber', 'EPDM', '25038-36-2'),
    'CR':     ('polychloroprene', 'poly(2-chlorobuta-1,3-diene)', 'CR; neoprene; polychloroprene; chloroprene rubber', 'CR', '9010-98-4'),
    'IIR':    ('isobutylene-isoprene rubber', None, 'IIR; butyl rubber; Butil', 'IIR', '9010-85-9'),
    'CSM':    ('chlorosulfonated polyethylene', None, 'CSM; Hypalon; chlorosulfonated PE', 'CSM', '68037-39-8'),
    'ECO':    ('epichlorohydrin rubber', None, 'ECO; epichlorohydrin rubber', 'ECO', '24969-06-0'),
    'ACM':    ('polyacrylate rubber', None, 'ACM; polyacrylate rubber', 'ACM', '25212-88-8'),
    'FKM':    ('fluoroelastomer', None, 'FKM; Viton; fluoroelastomer; fluorocarbon rubber', 'FKM', '9011-17-0'),
    'EVA':    ('ethylene-vinyl acetate copolymer', None, 'EVA; Elvax; ethylene-vinyl acetate', 'EVA', '24937-78-8'),
    'EBA':    ('ethylene-butyl acrylate copolymer', None, 'EBA; ethylene-butyl acrylate', 'EBA', None),
    'EEA':    ('ethylene-ethyl acrylate copolymer', None, 'EEA; ethylene-ethyl acrylate', 'EEA', '9010-86-0'),
    'EMA':    ('ethylene-methyl acrylate copolymer', None, 'EMA; ethylene-methyl acrylate', 'EMA', '25053-53-6'),
    'EMAA':   ('ethylene-methacrylic acid copolymer', None, 'EMAA; ethylene-methacrylic acid; Nucrel', 'EMAA', '25053-53-6'),
    'PDMS':   ('polydimethylsiloxane', 'poly(dimethylsiloxane)', 'PDMS; silicone rubber; PDMS; dimethyl silicone', 'PDMS; silicone', '9016-00-6'),
    'PVMS':   ('poly(vinylmethylsiloxane)', None, 'PVMS', 'PVMS', None),
}

BRAND_CLASS = {
    'DESMOPHEN':     ('polyurethane precursor', 'polyester/polyether polyol', 'Covestro polyol for polyurethane synthesis'),
    'DESMODUR':      ('polyurethane precursor', 'polyisocyanate', 'Covestro polyisocyanate crosslinker'),
    'BAYHYDROL':     ('polyurethane', 'waterborne polyurethane dispersion', 'Covestro waterborne PU dispersion'),
    'BAYDERM':       ('polyurethane', 'polyurethane leather coating', 'Covestro PU leather coating system'),
    'EPIKOTE':       ('epoxy resin', 'bisphenol A diglycidyl ether epoxy', 'Hexion/Momentive bisphenol A epoxy resin'),
    'EPON':          ('epoxy resin', 'bisphenol A diglycidyl ether epoxy', 'Hexion/Shell bisphenol A epoxy resin'),
    'ARALDITE':      ('epoxy resin', 'bisphenol A or cycloaliphatic epoxy', 'Huntsman Araldite epoxy resin or hardener'),
    'EPICLON':       ('epoxy resin', 'bisphenol A epoxy resin', 'DIC Corporation epoxy resin'),
    'ELVAX':         ('copolymer', 'ethylene-vinyl acetate (EVA)', 'DuPont EVA copolymer; VA content varies by grade'),
    'ELVALOY':       ('copolymer', 'ethylene copolymer with acrylate', 'DuPont ethylene acrylate copolymer'),
    'SURLYN':        ('ionomer', 'ethylene-methacrylic acid ionomer', 'DuPont ionomer; metal-neutralized EMAA'),
    'NUCREL':        ('copolymer', 'ethylene-methacrylic acid copolymer', 'DuPont EMAA copolymer'),
    'DARAN':         ('chlorinated polymer', 'poly(vinylidene chloride)', 'W.R. Grace PVDC copolymer'),
    'SARAN':         ('chlorinated polymer', 'poly(vinylidene chloride)', 'Dow PVDC copolymer film resin'),
    'TEFLON':        ('fluoropolymer', 'PTFE or fluoropolymer blend', 'DuPont PTFE or fluoropolymer'),
    'VITON':         ('fluoroelastomer', 'vinylidene fluoride copolymer (FKM)', 'DuPont fluoroelastomer; VF2 copolymer'),
    'HYPALON':       ('chlorinated rubber', 'chlorosulfonated polyethylene (CSM)', 'DuPont chlorosulfonated PE rubber'),
    'NEOPRENE':      ('rubber', 'polychloroprene (CR)', 'DuPont polychloroprene rubber'),
    'KRATON':        ('thermoplastic elastomer', 'styrenic block copolymer (SBS/SEBS)', 'Kraton SBS or SEBS block copolymer'),
    'CARIFLEX':      ('rubber', 'synthetic polyisoprene (IR)', 'Shell/Kraton synthetic polyisoprene; cis-1,4-PI'),
    'VERSAMID':      ('polyamide resin', 'dimer acid-based polyamide', 'Cognis/BASF dimer acid polyamide; used as epoxy hardener'),
    'EUREDUR':       ('epoxy hardener', 'amine or amide epoxy curing agent', 'Schering epoxy hardener; amine or polyamide type'),
    'BEETLE':        ('amino resin', 'urea-formaldehyde or melamine-formaldehyde resin', 'Cytec/BIP amino resin'),
    'PLEXIGLAS':     ('acrylic', 'poly(methyl methacrylate) (PMMA)', 'Evonik/Röhm PMMA; acrylic sheet/pellet'),
    'PERSPEX':       ('acrylic', 'poly(methyl methacrylate) (PMMA)', 'Lucite International PMMA'),
    'LUCITE':        ('acrylic', 'poly(methyl methacrylate) (PMMA)', 'Lucite International PMMA'),
    'STYRON':        ('styrenic', 'polystyrene or HIPS', 'Dow/Trinseo general-purpose or high-impact PS'),
    'NORYL':         ('engineering plastic', 'PPO/PS blend', 'GE/SABIC modified polyphenylene oxide; PPO + PS blend'),
    'LEXAN':         ('engineering plastic', 'polycarbonate (PC)', 'GE/SABIC bisphenol A polycarbonate'),
    'MAKROLON':      ('engineering plastic', 'polycarbonate (PC)', 'Covestro bisphenol A polycarbonate'),
    'DELRIN':        ('engineering plastic', 'polyoxymethylene (POM) homopolymer', 'DuPont acetal homopolymer; POM-H'),
    'CELCON':        ('engineering plastic', 'polyoxymethylene (POM) copolymer', 'Celanese acetal copolymer; POM-C'),
    'ZYTEL':         ('engineering plastic', 'polyamide (PA66 or PA6)', 'DuPont nylon resin; typically PA66'),
    'NYLON':         ('polyamide', 'polyamide (generic)', 'generic polyamide; specific type by grade number'),
    'KAPTON':        ('polyimide', 'aromatic polyimide film', 'DuPont aromatic polyimide; PMDA-ODA type'),
    'ULTEM':         ('engineering plastic', 'poly(ether imide) (PEI)', 'GE/SABIC Ultem PEI'),
    'RYTON':         ('engineering plastic', 'poly(phenylene sulfide) (PPS)', 'Solvay Ryton PPS'),
    'LUMIFLON':      ('fluoropolymer coating resin', 'fluoroethylene-vinyl ether copolymer (FEVE)', 'AGC Chemicals FEVE fluoropolymer coating resin'),
    'LUMFLON':       ('fluoropolymer coating resin', 'fluoroethylene-vinyl ether copolymer (FEVE)', 'AGC Chemicals FEVE fluoropolymer coating resin (alt. spelling)'),
    'KYNAR':         ('fluoropolymer', 'poly(vinylidene fluoride) (PVDF)', 'Arkema PVDF; coating/engineering grade'),
    'TEDLAR':        ('fluoropolymer', 'poly(vinyl fluoride) (PVF) film', 'DuPont PVF film'),
    'HALAR':         ('fluoropolymer', 'ethylene-chlorotrifluoroethylene (ECTFE)', 'Solvay Halar ECTFE'),
    'NITROCELLULOSE': ('cellulosic', 'nitrocellulose (cellulose nitrate)', 'nitrocellulose; DS and MW dependent on grade'),
    'ETHOCEL':       ('cellulosic', 'ethyl cellulose', 'Dow ethyl cellulose; DS ~2.2–2.6'),
    'CELLIDORA':     ('cellulosic', 'cellulose acetate butyrate (CAB)', 'Bayer CAB; butyrate/acetate ratio varies by grade'),
    'CELLIT':        ('cellulosic', 'cellulose acetate butyrate or propionate', 'Bayer CAB or CAP cellulosic plastics'),
    'BUTVAR':        ('polyvinyl acetal', 'poly(vinyl butyral) (PVB)', 'Solutia/Eastman PVB resin'),
    'MOWITAL':       ('polyvinyl acetal', 'poly(vinyl butyral) (PVB)', 'Kuraray PVB resin; coating/film grade'),
    'MOWIOL':        ('polyvinyl alcohol', 'poly(vinyl alcohol) (PVA)', 'Kuraray/Hoechst PVA; hydrolysis degree varies'),
    'LAROPAL':       ('ketone resin', 'cyclohexanone condensation resin', 'BASF ketone resin; cyclohexanone-formaldehyde condensate'),
    'DURITE':        ('phenolic resin', 'phenol-formaldehyde resin (novolak or resole)', 'Borden/Momentive phenolic resin'),
    'BAKELITE':      ('phenolic resin', 'phenol-formaldehyde resin', 'Hexion/historical phenol-formaldehyde thermoset'),
    'SOAMIN':        ('polyamide resin', 'dimer acid polyamide (deprecated brand)', 'Schering/deprecated dimer acid polyamide'),
    'PLEXAL':        ('polyester resin', 'unsaturated or alkyd polyester (deprecated brand)', 'Röhm/deprecated polyester or alkyd resin'),
    'SOALKYD':       ('alkyd resin', 'oil-modified alkyd resin (deprecated brand)', 'Schering/deprecated alkyd resin'),
    'VILIT':         ('acrylic copolymer', 'acrylate copolymer dispersion (deprecated brand)', 'Hoechst/deprecated acrylic latex'),
    'PIOLOFORM':     ('polyvinyl acetal', 'poly(vinyl formal) or PVB', 'Wacker polyvinyl acetal resin'),
    'PIOFORM':       ('polyvinyl acetal', 'poly(vinyl formal)', 'Wacker poly(vinyl formal)'),
    'ISOFLEX':       ('rubber', 'synthetic rubber compound', 'synthetic rubber compound — grade dependent'),
    'KLUCEL':        ('cellulosic', 'hydroxypropyl cellulose (HPC)', 'Ashland HPC; water-soluble cellulosic'),
    'NATROSOL':      ('cellulosic', 'hydroxyethyl cellulose (HEC)', 'Aqualon/Ashland HEC'),
    'GANTREZ':       ('copolymer', 'methyl vinyl ether-maleic anhydride copolymer', 'ISP/Ashland MVE/MA copolymer; Gantrez AN/ES series'),
}

GENERIC_POLYMER_CAS = {
    'POLYETHYLENE': ('polyethylene', 'polyolefin', '9002-88-4', '[CAS] MW-range CAS — not grade specific'),
    'POLYPROPYLENE': ('polypropylene', 'polyolefin', '9003-07-0', '[CAS] MW-range CAS — not grade specific'),
    'POLYSTYRENE': ('polystyrene', 'styrenic', '9003-53-6', '[CAS] MW-range CAS — not grade specific'),
    'POLYISOPRENE': ('polyisoprene', 'rubber', '9003-31-0', '[CAS] MW-range CAS — not grade specific'),
    'POLYBUTADIENE': ('polybutadiene', 'rubber', '9003-17-2', '[CAS] MW-range CAS — not grade specific'),
    'POLYURETHANE': ('polyurethane', 'polyurethane', None, '[CAS] composition-dependent — no single CAS'),
    'POLYCARBONATE': ('polycarbonate', 'engineering plastic', '25037-45-0', '[CAS] MW-range CAS — not grade specific'),
    'POLYACETAL': ('polyoxymethylene', 'engineering plastic', '9002-81-7', '[CAS] MW-range CAS — not grade specific'),
    'POLYSILOXANE': ('polysiloxane', 'silicone', '9016-00-6', '[CAS] PDMS representative CAS'),
    'SILICONE': ('polysiloxane/silicone rubber', 'silicone', '9016-00-6', '[CAS] PDMS representative CAS'),
    'POLYIMIDE': ('polyimide', 'engineering plastic', None, '[CAS] structure-dependent — no single CAS'),
    'POLYAMIDE': ('polyamide', 'engineering plastic', None, '[CAS] type-dependent — no single CAS'),
    'POLYESTER': ('polyester', 'polyester', None, '[CAS] type-dependent — no single CAS'),
    'POLYSULFONE': ('polysulfone', 'engineering plastic', '25135-51-7', '[CAS] MW-range CAS — not grade specific'),
    'PHENOLIC': ('phenol-formaldehyde resin', 'thermoset', '9003-35-4', '[CAS] broad phenolic resin CAS'),
    'EPOXY': ('epoxy resin', 'thermoset', None, '[CAS] grade-dependent — no single CAS'),
    'ALKYD': ('alkyd resin', 'thermoset', None, '[CAS] composition-dependent — no single CAS'),
    'NITROCELLULOSE': ('nitrocellulose', 'cellulosic', '9004-70-0', '[CAS] DS-dependent, MW-range CAS'),
    'CELLULOSE': ('cellulose', 'cellulosic', '9004-34-6', '[CAS] native cellulose CAS'),
    'STARCH': ('starch', 'polysaccharide', '9005-25-8', '[CAS] starch CAS'),
    'GELATIN': ('gelatin', 'protein', '9000-70-8', '[CAS] gelatin CAS'),
    'COLLAGEN': ('collagen', 'protein', '9007-34-5', '[CAS] collagen CAS'),
    'CHITIN': ('chitin', 'polysaccharide', '1398-61-4', '[CAS] chitin CAS'),
    'SHELLAC': ('shellac', 'natural resin', '9000-59-3', '[CAS] shellac CAS'),
    'ROSIN': ('rosin', 'natural resin', '8050-09-7', '[CAS] rosin CAS'),
    'CASTOR OIL': ('castor oil', 'natural oil', '8001-79-4', '[CAS] castor oil CAS'),
    'LINSEED OIL': ('linseed oil', 'natural oil', '8001-26-1', '[CAS] linseed oil CAS'),
    'PALM OIL': ('palm oil', 'natural oil', '8002-75-3', '[CAS] palm oil CAS'),
    'LARD': ('lard', 'animal fat', '61789-10-4', '[CAS] lard (pork fat) CAS'),
}


# ─── POLYMER ROW CLASSIFICATION ──────────────────────────────────────────────

def classify_polymer(name_input):
    name_clean = FIX_GROUP_6.get(name_input, name_input)
    n = name_clean.upper().strip()

    if re.match(r'^R\s+[A-Z]', n):
        return name_clean, 'resistance_data', 'resistance_data', 'experimental_condition'
    if re.search(r'\b(\d+\s*H\s*R|HRS?|H\s*\d+|\d+H\b|HR\b|HOUR|MIN\b)\b', n):
        return name_clean, 'time_series', 'time_series', 'experimental_condition'
    if re.search(r'(%|PPM|IN WATER)', n):
        return name_clean, 'concentration_series', 'concentration_series', 'experimental_condition'
    if re.search(r'\b\d+\s*°?\s*C\b', name_clean):
        return name_clean, 'temperature_series', 'temperature_series', 'experimental_condition'

    clean_key = re.sub(r'[-/\d\s]', '', n)
    if clean_key in ABBREV_TO_IUPAC:
        return name_clean, 'abbreviation', 'material', 'literature'

    for brand in BRAND_CLASS:
        if n.startswith(brand.upper()):
            return name_clean, 'trade_name', 'material', 'literature'

    for generic in GENERIC_POLYMER_CAS:
        if generic in n:
            return name_clean, 'systematic_chemical', 'material', 'literature'

    bio = ['LARD', 'PALM OIL', 'KAURI GUM', 'SHELLAC', 'ROSIN', 'COLOPHONY',
           'CASTOR', 'LINSEED', 'ALKYD', 'LATEX', 'CARBON-60', 'C60', 'BETHOXAZIN']
    for b in bio:
        if b in n:
            return name_clean, 'flag_out_of_scope', 'biological_reference', 'literature'

    if re.search(r'[A-Z]{2,}/[A-Z]{2,}', n) or re.search(r'\d+/\d+', n):
        return name_clean, 'copolymer', 'material', 'literature'

    if 'NITRO CELLULOSE' in n or 'NITRO-CELLULOSE' in n or n.startswith('NC ') or n.endswith(' NC'):
        return name_clean, 'systematic_chemical', 'material', 'literature'

    return name_clean, 'trade_name', 'material', 'literature'


def get_polymer_common_name(name_input, name_clean, processing_route):
    n = name_clean.upper()
    clean_key = re.sub(r'[-/\d\s]', '', n)
    if clean_key in ABBREV_TO_IUPAC:
        return ABBREV_TO_IUPAC[clean_key][2]

    for brand, (cls, subcls, note) in BRAND_CLASS.items():
        if n.startswith(brand.upper()):
            return note

    for generic, (common, cls, cas, cas_note) in GENERIC_POLYMER_CAS.items():
        if generic in n:
            return common

    if processing_route == 'resistance_data':
        base = re.sub(r'^R\s+', '', name_clean, flags=re.IGNORECASE).strip()
        base_common = get_polymer_common_name(base, base, 'material')
        return f"{base_common} (RAPRA chemical resistance data)"

    if processing_route == 'time_series':
        base = re.sub(r'\s+\d+\s*H\s*R?\s*$', '', name_clean, flags=re.IGNORECASE).strip()
        base = re.sub(r'\s+\d+HR\s*$', '', base, flags=re.IGNORECASE).strip()
        if base != name_clean:
            base_common = get_polymer_common_name(base, base, 'material')
            time_part = name_clean[len(base):].strip()
            return f"{base_common}; condition: {time_part}"
        return f"{name_clean} (time-series condition entry)"

    if processing_route == 'concentration_series':
        return f"{name_clean} (concentration-series condition entry)"

    if processing_route == 'copolymer':
        parts = re.split(r'[/\-]', n)
        expanded = []
        for p in parts:
            p_clean = re.sub(r'[\d\s]', '', p)
            if p_clean in ABBREV_TO_IUPAC:
                expanded.append(ABBREV_TO_IUPAC[p_clean][0])
            else:
                expanded.append(p.strip())
        if expanded:
            return ' / '.join(expanded) + ' copolymer'
        return f"{name_clean} copolymer"

    if 'NITRO' in n and 'CELLUL' in n:
        return "nitrocellulose (cellulose nitrate); grade depends on DS and MW"

    if processing_route == 'flag_out_of_scope':
        for generic, (common, cls, cas, note) in GENERIC_POLYMER_CAS.items():
            if generic in n:
                return f"{common} (non-polymer reference material)"
        return f"{name_clean} (non-polymer / biological reference material)"

    return f"PENDING|haiku: composition of {name_clean}"


def get_polymer_iupac(name_clean, processing_route):
    n = name_clean.upper()
    clean_key = re.sub(r'[-/\d\s]', '', n)
    if clean_key in ABBREV_TO_IUPAC:
        entry = ABBREV_TO_IUPAC[clean_key]
        return entry[1] if entry[1] else f"PENDING|pubchem:name/{name_clean}/property/IUPACName/JSON"
    return f"PENDING|pubchem:name/{name_clean}/property/IUPACName/JSON"


def get_polymer_common_all(name_clean, name_common):
    """Return extended synonyms string (same as name_common for seed hits; else just name_common)."""
    n = name_clean.upper()
    clean_key = re.sub(r'[-/\d\s]', '', n)
    if clean_key in ABBREV_TO_IUPAC:
        return ABBREV_TO_IUPAC[clean_key][2]
    return name_common


def get_polymer_acronyms(name_clean):
    n = name_clean.upper()
    clean_key = re.sub(r'[-/\d\s]', '', n)
    if clean_key in ABBREV_TO_IUPAC:
        return ABBREV_TO_IUPAC[clean_key][3]
    tokens = re.findall(r'\b[A-Z]{2,6}\b', name_clean)
    if tokens:
        return '; '.join(dict.fromkeys(tokens))
    return ''


def get_polymer_cas(name_clean, processing_route):
    n = name_clean.upper()
    if processing_route in ('time_series', 'concentration_series', 'temperature_series',
                             'resistance_data', 'flag_out_of_scope'):
        return '', f'[CAS] {processing_route} entry — CAS not assigned'

    clean_key = re.sub(r'[-/\d\s]', '', n)
    if clean_key in ABBREV_TO_IUPAC:
        cas = ABBREV_TO_IUPAC[clean_key][4]
        if cas:
            return cas, '[CAS] MW-range CAS — not grade specific'
        return '', '[CAS] structure-dependent — no single CAS'

    for generic, (common, cls, cas, note) in GENERIC_POLYMER_CAS.items():
        if generic in n:
            if cas:
                return cas, note
            return '', note

    if processing_route == 'trade_name':
        return '', '[CAS] PENDING|pubchem/cascc: trade name CAS lookup required'

    if processing_route == 'copolymer':
        return '', '[CAS] PENDING|copolymer: no universal CAS'

    if 'NITRO' in n and 'CELLUL' in n:
        return '9004-70-0', '[CAS] nitrocellulose broad CAS — DS and MW-range dependent'

    return '', '[CAS] PENDING|pubchem/cascc lookup required'


def get_polymer_class(name_clean, processing_route, name_common):
    n = name_clean.upper()
    clean_key = re.sub(r'[-/\d\s]', '', n)
    if clean_key in ABBREV_TO_IUPAC:
        common = ABBREV_TO_IUPAC[clean_key][2].lower()
        for kw, cls, sub in [
            ('fluoropolymer', 'fluoropolymer', 'homopolymer fluoropolymer'),
            ('fluoroelastomer', 'fluoroelastomer', 'fluoroelastomer'),
            ('polyolefin', 'polyolefin', 'polyolefin'),
            ('polypropylene', 'polyolefin', 'polypropylene'),
            ('polyethylene', 'polyolefin', 'polyethylene'),
            ('polystyrene', 'styrenic', 'polystyrene'),
            ('styrene', 'styrenic', 'styrenic copolymer'),
            ('acrylic', 'acrylic', 'acrylate polymer'),
            ('pmma', 'acrylic', 'poly(methyl methacrylate)'),
            ('chlorinated', 'chlorinated polymer', 'chlorinated polymer'),
            ('polyester', 'polyester', 'polyester'),
            ('polyamide', 'polyamide', 'polyamide'),
            ('nylon', 'polyamide', 'polyamide'),
            ('polycarbonate', 'polycarbonate', 'bisphenol A polycarbonate'),
            ('polyacetal', 'polyacetal', 'polyoxymethylene'),
            ('polyurethane', 'polyurethane', 'polyurethane'),
            ('epoxy', 'epoxy resin', 'epoxy resin'),
            ('phenolic', 'thermoset', 'phenolic resin'),
            ('rubber', 'rubber', 'synthetic rubber'),
            ('elastomer', 'rubber', 'thermoplastic elastomer'),
            ('cellulosic', 'cellulosic', 'cellulose derivative'),
            ('silicone', 'silicone', 'polysiloxane'),
            ('polyimide', 'engineering plastic', 'polyimide'),
            ('engineering plastic', 'engineering plastic', 'engineering thermoplastic'),
            ('ionomer', 'ionomer', 'ionomer'),
            ('copolymer', 'copolymer', 'copolymer'),
        ]:
            if kw in common:
                return cls, sub

    for brand, (cls, sub, note) in BRAND_CLASS.items():
        if n.startswith(brand.upper()):
            return cls, sub

    for generic, (common_g, cls, cas, note) in GENERIC_POLYMER_CAS.items():
        if generic in n:
            return cls, f'{common_g}'

    if processing_route == 'resistance_data':
        return 'resistance data', 'resistance data entry'
    if processing_route in ('time_series', 'concentration_series', 'temperature_series'):
        return 'condition entry', f'{processing_route}'
    if processing_route == 'flag_out_of_scope':
        return 'non-polymer', 'biological/natural reference'

    return 'PENDING|haiku:classify', 'PENDING|haiku:subclassify'


def get_polymer_urls(name_clean, processing_route):
    if processing_route in ('time_series', 'concentration_series', 'temperature_series',
                             'resistance_data', 'flag_out_of_scope'):
        return '', '', ''

    if processing_route == 'trade_name':
        return (
            f'PENDING|brave:"{name_clean}" manufacturer product page',
            f'PENDING|brave:"{name_clean}" technical data sheet filetype:pdf',
            f'PENDING|brave:"{name_clean}" SDS filetype:pdf',
        )

    slug = name_clean.replace(' ', '_')
    return (
        f'PENDING|wikipedia:https://en.wikipedia.org/wiki/{slug}',
        '',
        f'PENDING|brave:"{name_clean} polymer" SDS site:sigmaaldrich.com',
    )


def is_out_of_scope(processing_route, data_type):
    return processing_route in ('resistance_data', 'time_series', 'concentration_series',
                                 'temperature_series', 'flag_out_of_scope')


# ─── MAIN ────────────────────────────────────────────────────────────────────

def run():
    print("=" * 60)
    print("HSP_polymers_9 PIPELINE")
    print("=" * 60)

    ROW_RE = re.compile(
        r'^(\d{1,3})\s+(.+?)\s+([-]?\d{1,2}\.\d{1,2})\s+([-]?\d{1,2}\.\d{1,2})\s+([-]?\d{1,2}\.\d{1,2})\s+([-]?\d{1,2}\.\d{1,2})\s*$',
        re.MULTILINE
    )

    raw_rows = []
    doc = fitz.open(PDF_PATH)
    print(f"PDF pages: {len(doc)}")
    for page in doc:
        text = page.get_text()
        text = text.replace('\u2013', '-').replace('\u2212', '-')
        for m in ROW_RE.finditer(text):
            raw_rows.append({
                'row_num': int(m.group(1)),
                'name_input': m.group(2).strip(),
                'dD': float(m.group(3)),
                'dP': float(m.group(4)),
                'dH': float(m.group(5)),
                'radius': float(m.group(6)),
            })
    doc.close()
    raw_rows.sort(key=lambda x: x['row_num'])
    print(f"Extracted {len(raw_rows)} rows from PDF")

    output_rows = []
    for i, r in enumerate(raw_rows):
        if (i + 1) % 100 == 0:
            print(f"  Enriching row {i+1}/{len(raw_rows)}...")

        name_input = r['name_input']
        notes = ['hsp_polymers_9', 'source=a2only.pdf', 'pipeline_v9_fitz']

        name_clean, proc_route, data_type, data_rel = classify_polymer(name_input)
        if name_clean != name_input:
            notes.append(f'FIX6: {name_input} → {name_clean}')

        name_common = get_polymer_common_name(name_input, name_clean, proc_route)
        name_iupac = get_polymer_iupac(name_clean, proc_route)
        name_common_all = get_polymer_common_all(name_clean, name_common)
        acronyms = get_polymer_acronyms(name_clean)
        cas, cas_note = get_polymer_cas(name_clean, proc_route)
        notes.append(cas_note)
        poly_class, poly_subclass = get_polymer_class(name_clean, proc_route, name_common)
        product_url, tds_url, sds_url = get_polymer_urls(name_clean, proc_route)

        hidden = is_out_of_scope(proc_route, data_type)

        # Map to database schema (matches hsp_polymers_8 columns)
        output_rows.append({
            'name':           name_clean,
            'name_input':     name_input,
            'cas_number':     cas,
            'delta_d':        r['dD'],
            'delta_p':        r['dP'],
            'delta_h':        r['dH'],
            'radius':         r['radius'],
            'type':           poly_class,
            'subclass':       poly_subclass,
            'data_type':      data_type,
            'data_reliability': data_rel,
            'confidence':     0.9,
            'source_count':   1,
            'source':         'hsp_polymers_9',
            'source_url':     SOURCE_URL,
            'name_iupac':     name_iupac,
            'name_common':    name_common,
            'name_common_all': name_common_all,
            'name_acronyms':  acronyms,
            'product_url':    product_url,
            'tds_url':        tds_url,
            'sds_url':        sds_url,
            'processing_notes': '; '.join(notes),
            'hidden':         str(hidden).lower(),
        })

    df = pd.DataFrame(output_rows)

    # Stats
    cas_filled = (df['cas_number'] != '').sum()
    iupac_filled = (~df['name_iupac'].str.startswith('PENDING')).sum()
    hidden_count = (df['hidden'] == 'true').sum()
    trade_names = (df['processing_notes'].str.contains('trade_name', na=False)).sum()
    print(f"\nPolymer pipeline complete: {len(df)} rows")
    print(f"  CAS assigned:     {cas_filled}/{len(df)}")
    print(f"  IUPAC resolved:   {iupac_filled}/{len(df)}")
    print(f"  Hidden (OOS):     {hidden_count}")

    # Write dataset
    os.makedirs(OUT_DIR, exist_ok=True)
    out_csv = os.path.join(OUT_DIR, 'polymers.csv')
    df.to_csv(out_csv, index=False)
    print(f"\nSaved: {out_csv}")

    # Update manifest
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)

    manifest['datasets']['hsp_polymers_9'] = {
        "id": "hsp_polymers_9",
        "name": "HSP Polymers 9",
        "source_url": SOURCE_URL,
        "description": (
            "Hansen Solubility Parameters Table A.2 extracted from the original Hansen (2007) PDF "
            "(a2only.pdf). Pipeline v9: PDF extraction with PyMuPDF/fitz, abbreviation seed table "
            "enrichment, brand/trade name classification, CAS from seed tables, IUPAC/common/acronym "
            "fields resolved from seed data, out-of-scope entries flagged hidden=true."
        ),
        "imported_at": "2026-03-11T00:00:00+00:00",
        "chemical_count": 0,
        "polymer_count": len(df),
        "active": True,
        "confidence_tier": 0.95,
        "fields_available": list(df.columns),
        "quality_notes": (
            f"Pipeline v9: fitz PDF extraction ({len(df)} rows). "
            f"CAS from seed: {cas_filled}/{len(df)}. "
            f"IUPAC from seed: {iupac_filled}/{len(df)}. "
            f"Hidden (out-of-scope): {hidden_count}."
        )
    }

    with open(MANIFEST_PATH, 'w') as f:
        json.dump(manifest, f, indent=4)
    print(f"Updated manifest: hsp_polymers_9 added")

    return df


if __name__ == '__main__':
    df = run()
    print(f"\nFirst 3 rows:")
    print(df[['name', 'delta_d', 'delta_p', 'delta_h', 'type', 'hidden']].head(3))
