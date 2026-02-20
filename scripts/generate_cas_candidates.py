"""Generate candidate corrections for chemicals missing CAS numbers.

For each chemical without a CAS, this script:
1. Generates name-repair guesses (fix truncation, missing hyphens, OCR artifacts)
2. Queries PubChem to validate each guess and retrieve CAS + canonical name
3. Computes a confidence score for each candidate
4. Outputs a JSON file consumed by the static review page

Usage: python scripts/generate_cas_candidates.py
"""

import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CHEM_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "hsp_chemicals.csv")
OUT_JSON = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "cas_candidates.json")
BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")


# ---- PubChem helpers ----

def pubchem_get(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 503):
                time.sleep(2 ** (attempt + 1))
                continue
            return None
        except Exception:
            time.sleep(1)
            continue
    return None


def _get_synonyms_and_cas(cid):
    """Given a CID, return (cas, synonyms) from PubChem."""
    surl = f"{BASE}/compound/cid/{cid}/synonyms/JSON"
    sdata = pubchem_get(surl)
    cas = ""
    synonyms = []
    if sdata:
        try:
            syns = sdata["InformationList"]["Information"][0]["Synonym"]
            synonyms = syns[:8]
            for s in syns:
                if CAS_RE.match(s):
                    cas = s
                    break
        except (KeyError, IndexError):
            pass
    return cas, synonyms


def _get_density(cid):
    """Fetch experimental density (g/mL) for a CID from PubChem pug_view.
    Returns float or None."""
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON?heading=Density"
    data = pubchem_get(url)
    if not data:
        return None
    # Walk nested JSON to find the first numeric density value
    density_re = re.compile(r"(\d+\.?\d*)\s*(?:g/(?:cu\s*cm|mL|ml)|at\s+\d)")
    def _walk(obj):
        if isinstance(obj, dict):
            if "StringWithMarkup" in obj:
                for s in obj["StringWithMarkup"]:
                    text = s.get("String", "")
                    m = density_re.search(text)
                    if m:
                        val = float(m.group(1))
                        if 0.3 <= val <= 3.0:
                            return val
            for v in obj.values():
                r = _walk(v)
                if r is not None:
                    return r
        elif isinstance(obj, list):
            for item in obj:
                r = _walk(item)
                if r is not None:
                    return r
        return None
    return _walk(data)


def _enrich_with_density(result):
    """Add computed reference molar volume to a lookup result dict."""
    cid = result.get("cid")
    mw = result.get("mw")
    if not cid or not mw:
        return
    density = _get_density(cid)
    if density:
        result["density"] = round(density, 4)
        result["ref_mv"] = round(mw / density, 1)
    time.sleep(0.15)


def lookup_name(name):
    """Query PubChem by name, return dict with cid, cas, iupac, mw, density, ref_mv, synonyms or None."""
    encoded = urllib.parse.quote(name, safe="")
    url = f"{BASE}/compound/name/{encoded}/property/IUPACName,MolecularFormula,MolecularWeight/JSON"
    data = pubchem_get(url)
    if not data:
        return None
    try:
        props = data["PropertyTable"]["Properties"][0]
        cid = props["CID"]
        iupac = props.get("IUPACName", "")
        mw = props.get("MolecularWeight")
        if mw is not None:
            mw = float(mw)
    except (KeyError, IndexError, ValueError):
        return None
    cas, synonyms = _get_synonyms_and_cas(cid)
    result = {"cid": cid, "cas": cas, "iupac": iupac, "mw": mw, "synonyms": synonyms}
    _enrich_with_density(result)
    return result


def lookup_smiles(smiles):
    """Query PubChem by SMILES, return same dict as lookup_name."""
    encoded = urllib.parse.quote(smiles, safe="")
    url = f"{BASE}/compound/smiles/{encoded}/property/IUPACName,MolecularFormula,MolecularWeight/JSON"
    data = pubchem_get(url)
    if not data:
        return None
    try:
        props = data["PropertyTable"]["Properties"][0]
        cid = props["CID"]
        iupac = props.get("IUPACName", "")
        mw = props.get("MolecularWeight")
        if mw is not None:
            mw = float(mw)
    except (KeyError, IndexError, ValueError):
        return None
    cas, synonyms = _get_synonyms_and_cas(cid)
    result = {"cid": cid, "cas": cas, "iupac": iupac, "mw": mw, "synonyms": synonyms}
    _enrich_with_density(result)
    return result


# ---- Name repair heuristics ----

# Truncated endings from OCR (last 1-3 chars cut off)
_TRUNCATION_FIXES = {
    "ethan": "ethane", "methan": "methane", "propan": "propane",
    "butan": "butane", "pentan": "pentane", "hexan": "hexane",
    "ylen": "ylene", "elen": "elene", "ilen": "ilene",
    "onitril": "onitrile", "nitril": "nitrile",
    "benzen": "benzene", "toluen": "toluene",
    "fluorid": "fluoride", "sulfid": "sulfide",
    "chlorid": "chloride", "bromid": "bromide",
    "sulfit": "sulfite", "sulfonat": "sulfonate",
    "phosphonat": "phosphonate", "fluoridat": "fluoridate",
    "fulvalen": "fulvalene", "dien": "diene",
    "phenon": "phenone", "oxim": "oxime",
    "Ethano": "Ethanol", " Aci": " Acid",
    "amin": "amine", "anhydrid": "anhydride",
    "carboxylat": "carboxylate", "acetat": "acetate",
    "propionat": "propionate", "butanoat": "butanoate",
    "acrylat": "acrylate", "methacrylat": "methacrylate",
    "carbonat": "carbonate",
    "o Isopropanol": "o-Isopropanol",
    "oluene": "otoluene",
}


def _add(guesses, text, reason, conf):
    """Helper to append a guess."""
    text = text.strip()
    if text:
        guesses.append((text, reason, conf))


def generate_name_guesses(name):
    """Generate plausible corrections for a chemical name.
    Returns list of (guess, reason, confidence).
    """
    guesses = []
    o = name.strip()

    # ── Wolfram concatenated names ───────────────────────────────────────
    # "2Butanone" → "2-Butanone"
    # "1Methoxy2Propanol" → "1-Methoxy-2-Propanol"
    # "4Hydroxy4Methyl2Pentanone" → "4-Hydroxy-4-Methyl-2-Pentanone"
    if re.search(r"\d[A-Z]", o) and not re.search(r"\s", o):
        fixed = re.sub(r"(\d)([A-Z])", r"\1-\2", o)
        if fixed != o:
            _add(guesses, fixed, "Insert hyphens: digit→letter", 0.88)
            # Also try with spaces instead of hyphens for multi-word
            if fixed.count("-") > 2:
                spaced = re.sub(r"(?<=\d)-(?=[A-Z])", "-", fixed)
                _add(guesses, spaced, "Insert hyphens at digit boundaries", 0.85)

    # CamelCase → spaces: "DiethyleneGlycolButylEther" → "Diethylene Glycol Butyl Ether"
    if re.search(r"[a-z][A-Z]", o) and not re.search(r"\s", o):
        spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", o)
        if spaced != o:
            _add(guesses, spaced, "Split CamelCase words", 0.82)
            # Combined: digit-hyphens + CamelCase spaces
            combined = re.sub(r"([a-z])([A-Z])", r"\1 \2",
                              re.sub(r"(\d)([A-Z])", r"\1-\2", o))
            if combined != spaced and combined != o:
                _add(guesses, combined, "Split CamelCase + digit hyphens", 0.85)

    # ── Truncated endings ────────────────────────────────────────────────
    for suffix, full in _TRUNCATION_FIXES.items():
        if o.endswith(suffix) and not o.endswith(full):
            fixed = o[:-len(suffix)] + full
            _add(guesses, fixed, f"Fix truncation: …{suffix} → …{full}", 0.90)

    # Generic: ends in consonant cluster that's likely truncated (try +e)
    if re.search(r"[bcdfghjklmnpqrstvwxz]{2}$", o.lower()) and not any(
            o.endswith(s) for s in ("ss", "ll", "ff", "tt", "nn")):
        _add(guesses, o + "e", "Append missing final 'e'", 0.65)

    # ── Spurious spaces from OCR ─────────────────────────────────────────
    # "1,1-Difluoroet ylene" → "1,1-Difluoroethylene"
    # "Perfluoromet ylcyclohexane" → "Perfluoromethylcyclohexane"
    # "4-(Trifluoromet yl)" → "4-(Trifluoromethyl)"
    parts = o.split()
    if len(parts) >= 2:
        for i in range(len(parts) - 1):
            a, b = parts[i], parts[i + 1]
            if a[-1:].isalpha() and b[0:1].islower() and len(b) >= 2:
                joined = list(parts)
                joined[i] = a + b
                del joined[i + 1]
                result = " ".join(joined)
                if result != o:
                    _add(guesses, result, f"Remove OCR space: '{a} {b}'→'{a}{b}'", 0.85)

    # ── Trailing junk ────────────────────────────────────────────────────
    # Incomplete parenthetical: "Anisaldehyde (2-Methoxy" → "Anisaldehyde"
    if " (" in o and not o.endswith(")"):
        trimmed = o[:o.index(" (")].strip()
        if len(trimmed) > 3:
            _add(guesses, trimmed, "Remove incomplete parenthetical", 0.72)
            # Also try extracting what's inside: "Cineol (Eucalyptol)"
            inner = o[o.index("(") + 1:].rstrip(")")
            if len(inner) > 3:
                _add(guesses, inner, "Use parenthetical as name", 0.60)

    # Complete parenthetical after name: "Tetramethylene Sulfone (Sulfolane)" → both
    m = re.match(r"^(.+?)\s*\(([^)]+)\)\s*$", o)
    if m and len(m.group(1)) > 3 and len(m.group(2)) > 3:
        _add(guesses, m.group(1).strip(), "Use name before parentheses", 0.75)
        _add(guesses, m.group(2).strip(), "Use parenthetical name", 0.78)

    # Hansen computation notes: "Diphenyl Acetylene P from 0 Dipole" → "Diphenyl Acetylene"
    m = re.match(r"^(.+?)\s+P\s+(?:from|by)\s+", o)
    if m:
        _add(guesses, m.group(1), "Remove 'P from/by…' note", 0.78)

    # Trailing partial repeat: "1,2,4,5-Tetrachlorobenzene 1,2,4,5-T" → first word group
    m = re.match(r"^(.{8,}?)\s+\d[\d,]*-[A-Z]$", o)
    if m:
        _add(guesses, m.group(1), "Remove trailing fragment", 0.72)

    # "Commercial" suffix
    if o.endswith(" Commercial"):
        _add(guesses, o[:-len(" Commercial")].strip(), "Remove 'Commercial'", 0.72)

    # ── Common OCR / encoding errors ─────────────────────────────────────
    if "alfa" in o.lower():
        _add(guesses, re.sub(r"(?i)\balfa\b", "alpha", o), "'alfa' → 'alpha'", 0.90)

    if "alpha,alpha,alpha" in o.lower():
        _add(guesses, re.sub(r"(?i)alpha,alpha,alpha", "alpha,alpha,alpha-", o),
             "Fix alpha prefix", 0.70)

    # "α,α,α" or "α" → "alpha"
    if "α" in o:
        _add(guesses, o.replace("α", "alpha"), "Replace α with alpha", 0.85)

    # "Chlorprene" → "Chloroprene"
    for bad, good in [("Chlorprene", "Chloroprene"), ("Bromoprene", "2-Bromobutadiene"),
                       ("Iodoprene", "2-Iodo-1,3-butadiene"),
                       ("Trinitomethane", "Trinitromethane"),
                       ("Norephedrin", "Norephedrine"),
                       ("Tigaldehyde", "Tiglic aldehyde"),
                       ("Vinylenecarbonate", "Vinylene carbonate")]:
        if bad in o:
            _add(guesses, o.replace(bad, good), f"Fix '{bad}' → '{good}'", 0.88)

    # ── Inverted names ───────────────────────────────────────────────────
    # "Butadiene-1-Chloro" → "1-Chlorobutadiene"
    # "Butadiene-1,2-Di-Chloro" → "1,2-Dichlorobutadiene"
    m = re.match(r"^(\w+)-(\d[\d,]*)-(?:Di-|Tri-|)?(\w+)$", o)
    if m:
        base, pos, subst = m.group(1), m.group(2), m.group(3)
        # Check for Di-/Tri- prefix
        prefix_m = re.match(r"^(\w+)-(\d[\d,]*)-(Di|Tri)-(\w+)$", o)
        if prefix_m:
            base, pos, mult, subst = prefix_m.groups()
            inverted = f"{pos}-{mult}{subst.lower()}{base.lower()}"
        else:
            inverted = f"{pos}-{subst}{base.lower()}"
        _add(guesses, inverted, "Invert name order", 0.75)

    # ── Amine/acid salt names ────────────────────────────────────────────
    # "Diethyl Amine/Acetic Acid" → "Diethylamine acetate"
    m = re.match(r"^(.+?)/(Acetic Acid|Formic Acid|Acetic|Methacrylic|.+Acid)$", o)
    if m:
        base = m.group(1).strip()
        # Try just the base amine
        _add(guesses, base, "Use base compound (salt)", 0.65)
        # Try without spaces
        base_joined = base.replace(" ", "")
        if base_joined != base:
            _add(guesses, base_joined, "Join base compound words", 0.60)

    # ── Remove excessive spaces ──────────────────────────────────────────
    # "2-Ethyl Hexyl Acrylate" → "2-Ethylhexyl Acrylate"
    # Try joining pairs that form common chemical words
    chem_parts = ["methyl", "ethyl", "propyl", "butyl", "hexyl", "octyl",
                  "chloro", "bromo", "fluoro", "nitro", "amino", "hydroxy",
                  "methoxy", "ethoxy", "butoxy", "propoxy", "phenyl", "vinyl",
                  "benzyl", "cyclohexyl", "isopropyl", "isobutyl"]
    lower = o.lower()
    for part in chem_parts:
        # Look for "Xxx Part" where joining gives "XxxPart"
        pattern = re.compile(r"(\w+)\s+" + re.escape(part), re.IGNORECASE)
        m2 = pattern.search(o)
        if m2:
            prefix = m2.group(1)
            if prefix[-1:].isalpha() and not prefix.lower().endswith(("di", "tri", "mono", "bis")):
                fixed = o[:m2.start()] + prefix + part + o[m2.end():]
                if fixed.lower() != o.lower():
                    _add(guesses, fixed, f"Join '{prefix} {part}' → '{prefix}{part}'", 0.72)

    # ── "Ro = XX" or "Water - ..." special cases → skip material ────────
    if re.search(r"Ro?\s*=\s*\d", o) or o.startswith("Water -"):
        _add(guesses, o, "Special entry (may not be a standard chemical)", 0.10)

    # ── Mixtures / long descriptions → extract first word ────────────────
    if "Mix of" in o or "Mixture" in o:
        _add(guesses, o, "Mixture — may not have a single CAS", 0.10)

    # ── Last resort: try the original ────────────────────────────────────
    if not guesses:
        _add(guesses, o, "Original name (retry)", 0.30)

    # ── Also generate combined fixes ─────────────────────────────────────
    # Apply truncation fixes to guesses that were already space-fixed
    extra = []
    for g, reason, conf in guesses:
        for suffix, full in _TRUNCATION_FIXES.items():
            if g.endswith(suffix) and not g.endswith(full):
                fixed = g[:-len(suffix)] + full
                extra.append((fixed, reason + f" + fix …{suffix}", min(conf + 0.03, 0.95)))
    guesses.extend(extra)

    # ── Deduplicate ──────────────────────────────────────────────────────
    seen = set()
    unique = []
    for g, reason, conf in guesses:
        g = g.strip()
        key = g.lower()
        if key not in seen and key != o.lower():
            seen.add(key)
            unique.append((g, reason, conf))

    # Always try original as lowest-priority fallback
    if o.lower() not in seen:
        unique.append((o, "Original name", 0.30))

    return unique


def main():
    with open(CHEM_CSV) as f:
        rows = list(csv.DictReader(f))

    missing = [(i, r) for i, r in enumerate(rows) if not r.get("cas_number", "").strip()]
    print(f"Total chemicals: {len(rows)}")
    print(f"Missing CAS: {len(missing)}")

    candidates = []

    for idx, (row_idx, row) in enumerate(missing):
        name = row["name"]
        smiles = row.get("smiles", "").strip()
        source = row.get("source", "")
        dd = row.get("delta_d", "")
        dp = row.get("delta_p", "")
        dh = row.get("delta_h", "")
        known_mv_str = row.get("molar_volume", "").strip()
        known_mv = float(known_mv_str) if known_mv_str else None

        entry = {
            "row_index": row_idx,
            "original_name": name,
            "source": source,
            "smiles": smiles,
            "delta_d": dd, "delta_p": dp, "delta_h": dh,
            "molar_volume": known_mv,
            "options": []
        }

        # Generate name guesses
        guesses = generate_name_guesses(name)

        def _make_option(result, reason, base_conf, via_smiles=False):
            """Build an option dict with molar volume validation."""
            conf = base_conf
            if result["cas"]:
                conf = min(conf + 0.05, 0.99)
            elif not via_smiles:
                conf = max(conf - 0.15, 0.20)

            pubchem_mw = result.get("mw")
            ref_mv = result.get("ref_mv")       # MW / density from PubChem
            ref_density = result.get("density")  # g/mL from PubChem
            mv_match = None   # None = can't compare, True = close, False = mismatch
            mv_pct_diff = None  # percentage difference between known MV and ref MV

            if known_mv and ref_mv:
                # Direct comparison: our MV vs PubChem's MW/density
                mv_pct_diff = round(abs(known_mv - ref_mv) / known_mv * 100, 1)
                if mv_pct_diff <= 15:
                    mv_match = True
                    # Scale bonus: <5% → +0.12, 5-10% → +0.08, 10-15% → +0.04
                    if mv_pct_diff <= 5:
                        conf = min(conf + 0.12, 0.99)
                    elif mv_pct_diff <= 10:
                        conf = min(conf + 0.08, 0.99)
                    else:
                        conf = min(conf + 0.04, 0.99)
                else:
                    mv_match = False
                    # Penalty scales with how far off: >30% → −0.30, 15-30% → −0.15
                    if mv_pct_diff > 30:
                        conf = max(conf - 0.30, 0.05)
                    else:
                        conf = max(conf - 0.15, 0.10)
            elif known_mv and pubchem_mw:
                # Fallback: no density from PubChem, use implied density check
                implied_density = pubchem_mw / known_mv
                if not (0.5 <= implied_density <= 2.5):
                    mv_match = False
                    conf = max(conf - 0.30, 0.05)

            opt = {
                "corrected_name": result["synonyms"][0] if result["synonyms"] else (result.get("guess_text") or name),
                "cas": result["cas"],
                "iupac": result["iupac"],
                "confidence": round(conf, 2),
                "reason": reason,
                "cid": result["cid"],
                "synonyms": result["synonyms"],
                "pubchem_mw": pubchem_mw,
                "ref_mv": ref_mv,
                "ref_density": ref_density,
                "mv_match": mv_match,
                "mv_pct_diff": mv_pct_diff,
            }
            if not via_smiles and result.get("guess_text"):
                opt["guess_text"] = result["guess_text"]
            return opt

        # Look up SMILES first (most reliable if available)
        smiles_result = None
        if smiles:
            smiles_result = lookup_smiles(smiles)
            time.sleep(0.2)
            if smiles_result and smiles_result["cas"]:
                entry["options"].append(
                    _make_option(smiles_result, "Matched via SMILES", 0.95, via_smiles=True)
                )

        # Try each name guess
        seen_cids = set()
        if smiles_result:
            seen_cids.add(smiles_result["cid"])

        for guess, reason, base_conf in guesses:
            result = lookup_name(guess)
            time.sleep(0.2)

            if result and result["cid"] not in seen_cids:
                seen_cids.add(result["cid"])

                if smiles_result and result["cid"] == smiles_result["cid"]:
                    continue  # already covered

                result["guess_text"] = guess
                entry["options"].append(_make_option(result, reason, base_conf))

            elif result and result["cid"] in seen_cids:
                for opt in entry["options"]:
                    if opt.get("cid") == result["cid"]:
                        opt["confidence"] = min(round(opt["confidence"] + 0.05, 2), 0.99)
                        break

        # If no options at all, add a "skip/manual" placeholder
        if not entry["options"]:
            entry["options"].append({
                "corrected_name": name,
                "cas": "",
                "iupac": "",
                "confidence": 0.0,
                "reason": "No match found — needs manual review",
                "cid": None,
                "synonyms": [],
                "pubchem_mw": None,
                "ref_mv": None,
                "ref_density": None,
                "mv_match": None,
                "mv_pct_diff": None,
            })

        # Sort options by confidence descending
        entry["options"].sort(key=lambda x: -x["confidence"])

        candidates.append(entry)

        if (idx + 1) % 10 == 0 or idx == len(missing) - 1:
            resolved = sum(1 for c in candidates if any(o["cas"] for o in c["options"]))
            print(f"  [{idx+1}/{len(missing)}] resolved={resolved}")
            # Save incrementally
            with open(OUT_JSON, "w") as f:
                json.dump(candidates, f, indent=1)

    # Final save
    with open(OUT_JSON, "w") as f:
        json.dump(candidates, f, indent=1)

    resolved = sum(1 for c in candidates if any(o["cas"] for o in c["options"]))
    print(f"\nDone! {resolved}/{len(candidates)} have at least one CAS candidate.")


if __name__ == "__main__":
    main()
