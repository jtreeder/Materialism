"""Name normalization, CAS validation, and float parsing utilities."""

import re


def normalize_name(name):
    """Normalize chemical name for dedup comparison."""
    if not name:
        return ""
    n = name.strip().lower()
    n = re.sub(r"\s+", " ", n)
    # Remove trailing parenthetical descriptions
    n = re.sub(r"\s*\([^)]*\)\s*$", "", n)
    # Strip punctuation and whitespace for comparison
    n = n.replace("-", "").replace(",", "").replace(" ", "").replace(".", "")
    return n


def normalize_cas(cas):
    """Clean up CAS number. Returns empty string for invalid."""
    if not cas:
        return ""
    cas = str(cas).strip()
    if re.match(r"^\d{2,7}-\d{2}-\d$", cas):
        return cas
    return ""


def parse_float(val):
    """Parse a float value, returning None for missing/invalid data."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        if val != val:  # NaN check
            return None
        return float(val)
    val = str(val).strip()
    if not val or val == "-" or val.lower() in ("nan", "none", ""):
        return None
    try:
        return float(val.replace(",", ""))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Hansen A1 Name Splitting (IUPAC helpers)
# ---------------------------------------------------------------------------

# IUPAC carbon-chain stems
_IUPAC_STEMS = re.compile(
    r"(meth|eth(?!yl)|prop|but(?!yl)|pent|hex|hept|oct|non(?!yl)|dec|"
    r"undec|dodec|benz[eo]|naphthal|oxir|thiir|azirid|furan|pyrrol|"
    r"pyrid|thiophen|imidazol|morpholin|quinol|chromen|oxepan|thiet)",
    re.I,
)

# Systematic suffixes (without preceding hyphen)
_IUPAC_SUFFIX = re.compile(
    r"(ane|ene|yne|ol|al|one|amine|amide|nitrile|thiol|diol|dione|"
    r"triol|anone|enol|anide|oate|oic|ide|ate|ole)$",
    re.I,
)


def _looks_like_iupac_word(word):
    """Check if a word is a systematic IUPAC-style name (with hyphens/digits)."""
    if re.search(r"-\d", word):
        return True
    if re.match(r"^[A-Z][a-z]+-[a-z]", word):
        return True
    if "-" in word and re.match(r"^(Di|Tri|Tetra|Penta|Hexa|Bis|Tris)", word):
        return True
    if re.match(r"^N[,N]*-[A-Z]", word) and "-" in word[3:]:
        return True
    if "[" in word:
        return True
    if re.match(r"^[a-z]-[A-Z]", word):
        return True
    return False


def _looks_like_iupac_name(word):
    """Check if a single unhyphenated word is likely a systematic IUPAC name."""
    has_stem = bool(_IUPAC_STEMS.search(word))
    has_suffix = bool(_IUPAC_SUFFIX.search(word))
    if has_stem and has_suffix:
        return True
    known = {
        "aziridine", "thiirane", "oxirane", "thietane", "oxetane",
        "anthraquinone", "benzoquinone", "quinone",
    }
    if word.lower() in known:
        return True
    return False


def _has_iupac_suffix(word):
    """Check if a word ends with a recognized chemical suffix."""
    return bool(_IUPAC_SUFFIX.search(word))


def extract_common_name(raw_name):
    """Extract the common (trivial) name from 'CommonName IUPACName' format."""
    name = raw_name.strip()
    if not name:
        return name

    # 1. Handle asterisk delimiter
    if "*" in name:
        return name.split("*")[0].strip()

    # 2. Strip parenthetical aliases
    paren_match = re.match(r"^(.+?)\s*\([^)]*\)\s*(.+)$", name)
    if paren_match:
        before = paren_match.group(1).strip()
        after = paren_match.group(2).strip()
        if after and len(before) >= 3 and not before.endswith("-"):
            return before

    words = name.split()
    n = len(words)

    if n <= 1:
        return name

    # 3. Check for exact word-for-word duplication
    for half_len in range(1, n // 2 + 1):
        if n >= 2 * half_len:
            first_half = " ".join(words[:half_len])
            second_half = " ".join(words[half_len : 2 * half_len])
            if first_half.lower() == second_half.lower():
                return first_half

    # 4. Find IUPAC boundary by pattern matching
    for i in range(1, n):
        word = words[i]
        if word[0].isdigit():
            return " ".join(words[:i])
        if word[0] in "([":
            return " ".join(words[:i])
        if _looks_like_iupac_word(word):
            return " ".join(words[:i])
        if word[0].islower() and i >= 2:
            prev = words[i - 1]
            if prev[0].isupper():
                return " ".join(words[:i - 1])

    # 5. For 3-word entries: check if last word is IUPAC
    if n == 3:
        if _looks_like_iupac_name(words[2]):
            return " ".join(words[:2])
        if _has_iupac_suffix(words[2]) and words[2][0].isupper():
            return " ".join(words[:2])

    # 6. For 2-word entries
    if n == 2:
        if _looks_like_iupac_name(words[1]):
            return words[0]
        return name

    # 7. Fallback
    return name
