"""Chemical and polymer classification by name/SMILES patterns."""


def classify_chemical(name, smiles=None):
    """Simple rule-based classification based on name/SMILES patterns."""
    name_lower = name.lower() if name else ""

    if any(x in name_lower for x in [
        "methanol", "ethanol", "propanol", "butanol", "pentanol", "hexanol",
        "octanol", "heptanol", "nonanol", "decanol", "alcohol", "glycol",
        "glycerol", "phenol", "cresol", "naphthol", "catechol", "resorcinol",
        "hydroquinone", "cyclohexanol", "menthol", "borneol", "fenchol",
        "isoborneol", "terpineol",
    ]):
        return "alcohol"

    if any(x in name_lower for x in [
        "formamide", "acetamide", "pyrrolidone", "pyrrolidinone",
        "nmp", "dmf", "dmac", "caprolactam", "dimethylformamide",
        "dimethylacetamide",
    ]):
        return "amide"

    if any(x in name_lower for x in [
        "methoxyethanol", "ethoxyethanol", "butoxyethanol", "propoxyethanol",
        "glycol ether", "cellosolve", "carbitol", "dowanol",
        "methoxypropanol", "ethoxypropanol",
        "diethylene glycol mono", "propylene glycol mono",
    ]):
        return "glycol ether"

    if any(x in name_lower for x in [
        "acetate", "formate", "propionate", "butyrate", "benzoate",
        "lactone", "butyrolactone", "propiolactone", "valerolactone",
        "carbonate", "acrylate", "methacrylate", "lactate",
        "malonate", "oxalate", "succinate", "phthalate", "maleate",
        "fumarate", "citrate", "tartrate", "sebacate", "adipate",
    ]):
        return "ester"

    if any(x in name_lower for x in [
        "acetone", "ketone", "cyclohexanone", "cyclopentanone",
        "acetophenone", "isophorone", "mesityl oxide", "diacetone",
        "methylethylketone", "methyl ethyl ketone", "mek", "mibk",
        "methyl isobutyl ketone",
    ]):
        return "ketone"

    if any(x in name_lower for x in [
        "ether", "tetrahydrofuran", "thf", "dioxane", "dioxolane",
        "diglyme", "triglyme", "tetraglyme", "glyme", "furan",
        "anisole", "phenetole", "methyltetrahydrofuran",
        "dihydropyran", "tetrahydropyran",
    ]):
        return "ether"

    if any(x in name_lower for x in [
        "nitrile", "cyanide", "acetonitrile", "propionitrile",
        "butyronitrile", "benzonitrile", "acrylonitrile", "succinonitrile",
    ]):
        return "nitrile"

    if any(x in name_lower for x in [
        "amine", "aniline", "pyridine", "morpholine", "triethylamine",
        "ethanolamine", "piperidine", "piperazine", "imidazole",
        "diethylamine", "dimethylamine", "trimethylamine", "butylamine",
        "hexylamine", "diisopropylamine", "dibutylamine",
        "cyclohexylamine", "benzylamine",
    ]):
        return "amine"

    if any(x in name_lower for x in [
        "sulfoxide", "dmso", "sulfolane", "sulfone",
        "dimethyl sulfoxide", "dimethylsulfoxide",
    ]):
        return "sulfoxide"

    if any(x in name_lower for x in [
        "acetic acid", "formic acid", "propionic acid", "butyric acid",
        "valeric acid", "caproic acid", "oleic acid", "stearic acid",
        "benzoic acid", "lactic acid", "citric acid", "oxalic acid",
        "trifluoroacetic", " acid",
    ]):
        return "acid"

    if any(x in name_lower for x in [
        "nitromethane", "nitroethane", "nitropropane", "nitrobenzene",
        "nitrotoluene", "dinitro", "trinitro",
    ]):
        if name_lower.startswith("nitro") or "nitro" in name_lower:
            return "nitro"

    if any(x in name_lower for x in [
        "limonene", "pinene", "cymene", "terpene", "turpentine",
        "myrcene", "camphene", "carvone", "geraniol", "linalool",
        "eucalyptol", "camphor", "thymol", "cineole",
    ]):
        return "terpene"

    if any(x in name_lower for x in ["chlor", "brom", "iodo", "fluoro"]):
        if any(x in name_lower for x in ["perfluoro", "hexafluoro", "trifluoroethanol"]):
            return "fluorinated"
        return "halogenated"

    if any(x in name_lower for x in ["perfluoro", "hexafluoro", "trifluoro", "fluorinated"]):
        return "fluorinated"

    if any(x in name_lower for x in [
        "benzene", "toluene", "xylene", "styrene", "naphthalene",
        "tetralin", "ethylbenzene", "phenyl", "biphenyl", "anthracene",
        "cumene", "mesitylene", "indene", "fluorene", "acenaphthene",
        "azulene", "durene", "hemimellitene",
    ]):
        return "aromatic"

    if any(x in name_lower for x in [
        "hexane", "heptane", "octane", "pentane", "decane", "nonane",
        "undecane", "dodecane", "butane", "propane",
        "cyclohexane", "cyclopentane", "methylcyclohexane",
        "naphtha", "paraffin", "isooctane", "petroleum", "squalane",
    ]):
        return "hydrocarbon"

    if any(x in name_lower for x in [
        "furfural", "furfuryl", "pyrrole", "thiophene", "oxazole",
        "thiazole", "indole", "quinoline", "isoquinoline", "carbazole",
        "acridine",
    ]):
        return "heterocyclic"

    if "glycol" in name_lower and "ether" not in name_lower:
        return "glycol"

    if name_lower in ["water", "carbon disulfide", "carbon disulphide"]:
        return "inorganic"

    if any(x in name_lower for x in [
        "aldehyde", "formaldehyde", "acetaldehyde", "propionaldehyde",
        "butyraldehyde", "benzaldehyde", "furfural",
    ]):
        return "aldehyde"

    if any(x in name_lower for x in [
        "mercaptan", "thiol", "sulfide", "disulfide", "thioacet",
    ]):
        return "sulfur compound"

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
