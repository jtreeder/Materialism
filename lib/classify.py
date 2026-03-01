"""Chemical and polymer classification by name/SMILES patterns."""


def classify_chemical(name, smiles=None):
    """Rule-based classification based on name/SMILES patterns."""
    name_lower = name.lower() if name else ""

    # Alcohol — check first (broad match for -ol, glycol, phenol, polyols, etc.)
    if any(x in name_lower for x in [
        "methanol", "ethanol", "propanol", "butanol", "pentanol", "hexanol",
        "octanol", "heptanol", "nonanol", "decanol", "alcohol", "glycerol",
        "phenol", "cresol", "naphthol", "catechol", "resorcinol",
        "hydroquinone", "cyclohexanol", "menthol", "borneol", "fenchol",
        "isoborneol", "terpineol", "carbinol", "diol",
        "itol",     # sugar alcohols: sorbitol, mannitol, xylitol, adonitol
        "eugenol",  # phenol derivative
    ]):
        return "alcohol"

    # Phosphates / phosphonates → inorganic (before amide to catch phosphoramide)
    if any(x in name_lower for x in [
        "phosphate", "phosphonate", "phosphonite", "phosphite", "phosphoric",
        "phosphoramide", "phosphofluoridate", "phosphomethyl", "phosphonic",
        "tri-n-butyl phosph", "trimethylphosph", "triethylphosph",
        "tricresyl phosph", "trioctyl phosph",
    ]):
        return "inorganic"

    # Boron compounds → inorganic
    if any(x in name_lower for x in ["borate", "boronate", "borane", "boronic"]):
        return "inorganic"

    # Sulfate / sulfonate esters → sulfur compound
    if any(x in name_lower for x in ["sulfate", "sulfonate", "sulphate", "sulphonate"]):
        return "sulfur compound"

    # Amide — expanded (urea, isocyanate, carbamate are amide-like)
    if any(x in name_lower for x in [
        "formamide", "acetamide", "pyrrolidone", "pyrrolidinone",
        "nmp", "dmf", "dmac", "caprolactam", "dimethylformamide",
        "dimethylacetamide", "acrylamide", "methacrylamide",
        "benzamide", "butyramide", "propionamide",
        "urea", "thiourea", "biuret", "tetramethylurea",
        "isocyanate", "urethane", "carbamate",
        "dimethylbutyramide", "n,n-dimethyl",
        "anilide", "amide",  # general amide keyword (after phosphate check)
        "n-formyl", "acetamid", "paracetamol",
    ]):
        return "amide"

    # Glycol ether (before ether to prioritize this sub-category)
    if any(x in name_lower for x in [
        "methoxyethanol", "ethoxyethanol", "butoxyethanol", "propoxyethanol",
        "glycol ether", "cellosolve", "carbitol", "dowanol",
        "methoxypropanol", "ethoxypropanol",
        "diethylene glycol mono", "propylene glycol mono",
    ]):
        return "glycol ether"

    # Anhydride → ester (anhydrides are condensed esters)
    if "anhydride" in name_lower:
        return "ester"

    # Ester — expanded with fatty esters, salicylates, glutarates, etc.
    if any(x in name_lower for x in [
        "acetate", "formate", "propionate", "butyrate", "benzoate",
        "lactone", "butyrolactone", "propiolactone", "valerolactone",
        "carbonate", "acrylate", "methacrylate", "lactate",
        "malonate", "oxalate", "succinate", "phthalate", "maleate",
        "fumarate", "citrate", "tartrate", "sebacate", "adipate",
        # Fatty acid esters
        "oleate", "stearate", "linoleate", "palmitate", "myristate",
        "laurate", "caproate", "caprylate", "caprate", "linolenate",
        "ricinoleate",
        # Other esters
        "cinnamate", "crotonate", "sorbate", "azelate", "salicylate",
        "furoate", "trimellitate", "trimellilate", "capronate",
        "glutarate", "propanoate", "hexanoate", "heptanoate", "octanoate",
        "decanoate", "toluate",
        # Broad terms
        " ester", "dibasic ester",
    ]):
        return "ester"

    # Ketone — expanded with cyclic ketones, quinones, phenones, diketones
    if any(x in name_lower for x in [
        "acetone", "ketone", "cyclohexanone", "cyclopentanone",
        "acetophenone", "isophorone", "mesityl oxide", "diacetone",
        "methylethylketone", "methyl ethyl ketone", "mek", "mibk",
        "methyl isobutyl ketone",
        "cyclobutanone", "cycloheptanone", "cyclodecanone", "cyclooctanone",
        "diketone", "butanedione", "diacetyl", "ketene", "diketene",
        "butadione", "glyoxal", "methyl glyoxal",
        "quinone", "phenone", "hexanone", "pentanone", "heptanone",
        "octanone", "nonanone", "decanone",
        "benzoin",  # α-hydroxy ketone
    ]):
        return "ketone"

    # Ether — expanded with epoxides (cyclic ethers) and acetals
    if any(x in name_lower for x in [
        "ether", "tetrahydrofuran", "thf", "dioxane", "dioxolane",
        "diglyme", "triglyme", "tetraglyme", "glyme", "furan",
        "anisole", "phenetole", "methyltetrahydrofuran",
        "dihydropyran", "tetrahydropyran",
        # Epoxides (cyclic ethers)
        "oxirane", "oxetane", "ethylene oxide", "propylene oxide",
        "butylene oxide", "isobutylene oxide", "butyleneoxide",
        "isobutyleneoxide", "glycidol", "epichlorohydrin",
        # Acetals and orthoesters
        "dimethoxymethane", "diethoxymethane", "methylal",
        "dimethyl isosorbide", "isosorbide",
        # Cyclic oxygen heterocycles
        "trioxane", "tetrahydrothiapyran",
        # Acetal patterns by name fragment
        "oxyethane", "allyloxyethane",
    ]):
        return "ether"

    # Acetal pattern — dimethoxy/diethoxy/trimethoxy not part of aromatic system
    if any(x in name_lower for x in ["dimethoxy", "diethoxy", "trimethoxy", "triethoxy"]):
        if not any(x in name_lower for x in ["benzene", "anisol", "phenol"]):
            return "ether"

    # Nitrile
    if any(x in name_lower for x in [
        "nitrile", "cyanide", "acetonitrile", "propionitrile",
        "butyronitrile", "benzonitrile", "acrylonitrile", "succinonitrile",
        "cyanogen", "cyanohydrin",
    ]):
        return "nitrile"

    # Amine — expanded with hydrazines, pyrrolidine, aziridine, imines
    if any(x in name_lower for x in [
        "amine", "aniline", "pyridine", "morpholine", "triethylamine",
        "ethanolamine", "piperidine", "piperazine", "imidazole",
        "diethylamine", "dimethylamine", "trimethylamine", "butylamine",
        "hexylamine", "diisopropylamine", "dibutylamine",
        "cyclohexylamine", "benzylamine",
        # New patterns
        "hydrazine", "hydrazide", "pyrrolidine", "aziridine",
        "guanidine", "toluidine", "imidazolidine", "methylhydrazine",
        "ethyleneimine", "imine", "oxime",
    ]):
        return "amine"

    # Sulfoxide
    if any(x in name_lower for x in [
        "sulfoxide", "dmso", "sulfolane", "sulfone",
        "dimethyl sulfoxide", "dimethylsulfoxide",
    ]):
        return "sulfoxide"

    # Acid
    if any(x in name_lower for x in [
        "acetic acid", "formic acid", "propionic acid", "butyric acid",
        "valeric acid", "caproic acid", "oleic acid", "stearic acid",
        "benzoic acid", "lactic acid", "citric acid", "oxalic acid",
        "trifluoroacetic", " acid",
    ]):
        return "acid"

    # Nitro compounds — also catches nitrates (like nitroglycerin)
    if any(x in name_lower for x in [
        "nitromethane", "nitroethane", "nitropropane", "nitrobenzene",
        "nitrotoluene", "dinitro", "trinitro", "nitro",
        "nitroglycerin", "nitrate", "nitrite",
    ]):
        if name_lower.startswith("nitro") or "nitro" in name_lower or "nitrate" in name_lower:
            return "nitro"

    # Terpene — expanded
    if any(x in name_lower for x in [
        "limonene", "pinene", "cymene", "terpene", "turpentine",
        "myrcene", "camphene", "carvone", "geraniol", "linalool",
        "eucalyptol", "camphor", "thymol", "cineole",
        "fenchene", "tricyclene", "pulegone", "fenchone",
        "menthone", "pine oil", "pine tar",
    ]):
        return "terpene"

    # HFC / HCFC / HFE refrigerants → fluorinated (before halogenated check)
    if any(name_lower.startswith(x) for x in ["hfc", "hcfc", "hfe"]):
        if any(c.isdigit() for c in name_lower):
            return "fluorinated"

    # Halogenated / fluorinated — use "fluor" (not "fluoro") to catch fluoride too
    if any(x in name_lower for x in ["chlor", "brom", "iodide", "iodo", "fluor",
                                      "ddt", "triclosan"]):
        if any(x in name_lower for x in [
            "perfluor", "hexafluor", "trifluoroethanol", "fluorinated",
            "hfc", "hcfc", "hfe",
        ]):
            return "fluorinated"
        return "halogenated"

    if any(x in name_lower for x in ["perfluoro", "hexafluoro", "trifluoro", "fluorinated"]):
        return "fluorinated"

    # Aromatic hydrocarbons
    if any(x in name_lower for x in [
        "benzene", "toluene", "xylene", "styrene", "naphthalene",
        "tetralin", "ethylbenzene", "phenyl", "biphenyl", "anthracene",
        "cumene", "mesitylene", "indene", "fluorene", "acenaphthene",
        "azulene", "durene", "hemimellitene",
        "anethole",  # methoxypropylbenzene — aromatic ether
    ]):
        return "aromatic"

    # Hydrocarbon — expanded with long-chain alkanes and alkenes/dienes
    if any(x in name_lower for x in [
        "hexane", "heptane", "octane", "pentane", "decane", "nonane",
        "undecane", "dodecane", "butane", "propane",
        "cyclohexane", "cyclopentane", "methylcyclohexane",
        "naphtha", "paraffin", "isooctane", "petroleum", "squalane",
        "eicosane", "tetradecane", "pentadecane", "hexadecane",
        "heptadecane", "octadecane", "nonadecane", "tricosane",
        # Alkenes and dienes
        "1-butene", "1-pentene", "1-hexene", "1-heptene", "1-octene",
        "1-nonene", "1-decene", "1-tetradecene", "1-hexadecene",
        "2-butene", "2-pentene", "isobutylene",
        "1,3-butadiene", "1,2-butadiene", "1,3-pentadiene",
        "isoprene", "butadiene",
        "cyclopentadiene", "cyclohexene", "cyclopentene", "cyclopropene",
        "propadiene", "allene",
        # Alkynes
        "acetylene", "ethyne", "propyne", "butyne",
        "methyl acetylene", "ethyl acetylene", "dimethyl acetylene",
        "vinyl acetylene",
        # Bicyclic hydrocarbons
        "bicyclohexyl",
    ]):
        return "hydrocarbon"

    # Catch simple gaseous/liquid hydrocarbons by exact name
    if name_lower.rstrip() in [
        "ethylene", "propylene", "isoprene",
        "ethane", "methane", "propane",
        "ethane (liq. b.p.)", "methane (liquid b.p.)",
    ]:
        return "hydrocarbon"

    # Castor oil — triglyceride ester
    if "castor oil" in name_lower:
        return "ester"

    # Alcohol by "-ol" name ending (propargyl alcohol, adonitol, eugenol, etc.)
    if (name_lower.endswith("-ol") or name_lower.endswith(" ol") or
            name_lower.rstrip("()").endswith("-ol")):
        return "alcohol"
    # Also catch names ending in plain "ol" preceded by digit or dash
    if len(name_lower) > 4 and name_lower[-2:] == "ol" and name_lower[-3] in "0123456789-":
        return "alcohol"

    # Catch alkenes by name pattern — ends in "-ene" and is not aromatic
    if (name_lower.endswith("ene") or name_lower.endswith("ylene") or
            name_lower.endswith("adiene") or name_lower.endswith("triene")):
        _aromatic_terms = [
            "benzene", "toluene", "naphthalene", "phenylene",
            "cumene", "mesitylene", "styrene", "durene", "fluorene",
            "polyethylene", "polypropylene",
        ]
        if not any(x in name_lower for x in _aromatic_terms):
            return "hydrocarbon"

    # Silicones and siloxanes → inorganic
    if any(x in name_lower for x in [
        "siloxane", "silazane", "tetraethylorthosilicate",
        "hexamethyldisiloxane", "octamethyldisiloxane",
    ]):
        return "inorganic"
    if "silane" in name_lower and any(x in name_lower for x in [
        "methyl", "vinyl", "ethyl", "propyl", "trimethyl", "dimethyl",
    ]):
        return "inorganic"

    # Heterocyclic — expanded with N-heterocycles
    if any(x in name_lower for x in [
        "furfural", "furfuryl", "pyrrole", "thiophene", "oxazole",
        "thiazole", "indole", "quinoline", "isoquinoline", "carbazole",
        "acridine",
        # N-heterocycles
        "triazole", "pyrazole", "pyrimidine", "pyridazine", "purine",
        "pyrazine", "benzotriazole", "imidazoline",
        "oxazoline", "thymine", "adenine", "coumarin", "skatole",
        "caffeine", "nicotine", "quinine",
    ]):
        return "heterocyclic"

    # Glycol (diols without ether linkage)
    if "glycol" in name_lower and "ether" not in name_lower:
        return "glycol"

    # Inorganic — expanded
    if name_lower.rstrip() in [
        "water", "carbon disulfide", "carbon disulphide",
        "ammonia", "sulfur dioxide", "hydrogen peroxide",
        "ozone", "phosgene", "carbon dioxide (fit = 1.0)",
        "water 1% soluble in - ro=18.1", "water complete misc. (r=13.0)",
    ]:
        return "inorganic"
    if any(x in name_lower for x in [
        "ammonia", "sulfur dioxide", "hydrogen peroxide", "borine carbonyl",
    ]):
        return "inorganic"

    # Aldehyde — expanded with acrolein, enal compounds, pentenal, etc.
    if any(x in name_lower for x in [
        "aldehyde", "formaldehyde", "acetaldehyde", "propionaldehyde",
        "butyraldehyde", "benzaldehyde", "furfural",
        "hexanal", "pentanal", "heptanal", "octanal", "nonanal", "decanal",
        "acrolein", "crotonaldehyde", "malonaldehyde",
        "vanillin", "cinnamaldehyde", "pentenal",
    ]):
        return "aldehyde"
    # Catch "-al" ending aldehydes (but not "methanol", "ethanol", etc.)
    if name_lower.rstrip().endswith("nal") and not name_lower.endswith("anol"):
        return "aldehyde"

    # Sulfur compounds — expanded with isothiocyanates
    if any(x in name_lower for x in [
        "mercaptan", "thiol", "sulfide", "disulfide", "thioacet",
        "isothiocyanate", "thiocyanate", "thioxane",
    ]):
        return "sulfur compound"

    # SMILES-based fallback classification
    if smiles:
        s = smiles
        has_ring = "c" in s or "C1" in s
        has_O = "O" in s
        has_N = "N" in s
        has_halogen = any(x in s for x in ["Cl", "Br", "I", "F"])

        if has_halogen and not has_O:
            return "halogenated"
        if has_ring and not has_O and not has_N and not has_halogen:
            return "aromatic"
        if not has_O and not has_N and not has_halogen and not has_ring:
            return "hydrocarbon"

    return "other"


def classify_polymer(name):
    """Classify polymer type based on name."""
    nl = name.lower()

    if any(x in nl for x in ["epoxy", "epoxies", "epon", "epikote"]):
        return "Epoxy"
    if any(x in nl for x in ["polyurethane", "polyurethanes"]):
        return "Polyurethane"
    if any(x in nl for x in ["polyimide", "polyamideimide"]):
        return "Polyimide"
    if any(x in nl for x in ["nylon", "polyamide", "pa6", "pa11", "pa12"]):
        return "Polyamide"
    if any(x in nl for x in ["polycarbonate"]):
        return "Polycarbonate"
    if any(x in nl for x in ["polysulfone", "polysulphone"]):
        return "Polysulfone PSU"
    if any(x in nl for x in ["polystyrene", "abs"]):
        return "Polystyrene"
    if any(x in nl for x in ["polyvinyl chloride", "pvc"]):
        return "Polyvinylchloride"
    if any(x in nl for x in ["polyvinyl acetate", "pvac"]):
        return "Polyvinylacetate"
    if any(x in nl for x in ["polyvinyl alcohol", "pva)", "pvoh"]):
        return "Polyvinyl Alcohol"
    if any(x in nl for x in ["polyvinyl butyral", "pvb"]):
        return "Polyvinylbutyral"
    if any(x in nl for x in ["polyvinylidene", "pvdc", "saran"]):
        return "Polyvinylidene Chloride"
    if any(x in nl for x in ["polyvinylpyrrolidone", "pvp"]):
        return "Polyvinylpyrrolidone"
    if any(x in nl for x in ["pmma", "pema", "pibma", "pbma", "methacrylate",
                               "acrylate", "acrylic", "plexiglas"]):
        return "Polyacrylate"
    if any(x in nl for x in ["polyacrylonitrile", "pan)"]):
        return "Polyacrylonitrile"
    if any(x in nl for x in ["polyethylene terephthalate", "pet)", "pla)",
                               "polylactic"]):
        return "Polyester"
    if any(x in nl for x in ["polyethylene", "hdpe", "ldpe", "pe)"]):
        return "Polyethylene"
    if any(x in nl for x in ["polypropylene", "pp)"]):
        return "Polypropylene"
    if any(x in nl for x in ["polyisoprene", "pip)"]):
        return "Polyisoprene"
    if any(x in nl for x in ["polybutadiene"]):
        return "Polybutadiene"
    if any(x in nl for x in ["polyphenylene oxide", "ppo"]):
        return "Polyphenylene Oxide"
    if any(x in nl for x in ["polyphenylene sulfide", "pps"]):
        return "Polyphenylene Sulfide"
    if any(x in nl for x in ["polyetherimide", "pei)"]):
        return "Polyetherimide"
    if any(x in nl for x in ["polyethersulfone", "pes)"]):
        return "Polyethersulfone"
    if any(x in nl for x in ["polychlorotrifluoroethylene", "pctfe",
                               "ptfe", "pvdf", "fluoropolymer", "teflon",
                               "fep", "fluorinated ethylene", "pfa"]):
        return "Fluoropolymer"
    if any(x in nl for x in ["phenolic"]):
        return "Phenolic Resins"
    if any(x in nl for x in ["alkyd"]):
        return "Alkyd"
    if any(x in nl for x in ["rubber", "elastomer", "neoprene", "epdm"]):
        return "Elastomer"
    if any(x in nl for x in ["silicone", "pdms"]):
        return "Silicone Resins"
    if any(x in nl for x in ["cellulose", "cellophane"]):
        return "Cellulose"
    if any(x in nl for x in ["starch", "lignin", "shellac", "rosin",
                               "bitumen", "natural", "chitosan", "chitin",
                               "zein", "collagen"]):
        return "Natural"
    if any(x in nl for x in ["nitrocellulose"]):
        return "Nitrocellulose"
    return ""
