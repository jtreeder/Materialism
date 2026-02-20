#!/usr/bin/env python3
"""
Parse and clean Hansen Solubility Parameter tables A.1 and A.2 from
pdftotext -layout output of the 2007 Hansen book appendix.

Produces:
  data/processed/table_a1.csv  (solvents)
  data/processed/table_a2.csv  (polymers)
"""

import csv
import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_TXT = os.path.join(BASE_DIR, "data", "raw", "raw_ocr.txt")
OUT_A1 = os.path.join(BASE_DIR, "data", "processed", "table_a1.csv")
OUT_A2 = os.path.join(BASE_DIR, "data", "processed", "table_a2.csv")


# ─── helpers ────────────────────────────────────────────────────────────────

def is_page_marker(line):
    """Detect page header/footer lines from the PDF."""
    s = line.strip()
    if re.match(r'^7248_A00[12]', s):
        return True
    if re.match(r'^Appendix A:', s):
        return True
    if re.search(r'Hansen Solubility Parameters', s):
        return True
    return False


def is_table_header(line):
    """Detect repeated column header lines."""
    s = line.strip()
    if s.startswith('TABLE A.1') or s.startswith('TABLE A.2'):
        return True
    if re.match(r'^No\.\s+Solvent Name', s):
        return True
    if re.match(r'^Number\s+Polymer', s):
        return True
    if s.startswith('Autonom/') or s.startswith('ACD Name'):
        return True
    if re.match(r'^\s*Hydrogen\s+(Molar|Interaction)', s):
        return True
    if s == 'Hansen Solubility Parameters for Selected Correlations':
        return True
    if re.match(r'^\s*Bonding\s+(Volume|Radius)', s):
        return True
    if re.match(r'^\s*Dispersion\s+Pola', s):
        return True
    return False


def is_structure_line(line):
    """Lines that are purely chemical structure diagram artifacts."""
    s = line.strip()
    if not s:
        return True

    # If the line has any decimal number (like 14.7), it's data, not structure
    if re.search(r'\d+\.\d', s):
        return False

    # If line starts with a row number followed by alphabetic text, it's data
    if re.match(r'^\d{1,4}\s{2,}[A-Za-z]', s):
        return False

    # Chemical structure tokens
    tokens = s.split()
    chem_pattern = re.compile(
        r'^(?:'
        r'[A-Z][a-z]?[0-9]*'     # element symbols: O, N, S, Cl, Br, F, Si, etc.
        r'|H[0-9]*C[0-9]*'        # H3C, H2C
        r'|CH[0-9]*'              # CH3, CH2
        r'|NH[0-9]*'              # NH2
        r'|OH[0-9]*'              # OH
        r'|HO'
        r'|SH'
        r'|NO[0-9]*'
        r'|CN'
        r'|CO[0-9]*'
        r'|CF[0-9]*'
        r'|OCH[0-9]*'
        r'|SO[0-9]*'
        r'|PO[0-9]*'
        r'|SnCl[0-9]*'
        r'|[+\-\(\)\*]'
        r'|[0-9]'
        r')$'
    )

    if all(chem_pattern.match(t) for t in tokens) and len(tokens) <= 15:
        # Guard: don't match real short names that look chemical
        # If the whole line is a single token >=4 chars with mixed case, it's probably a name
        if len(tokens) == 1 and len(tokens[0]) >= 4 and re.match(r'^[A-Z][a-z]', tokens[0]):
            return False
        return True

    return False


def extract_trailing_floats(text, expected_count):
    """Extract `expected_count` trailing float values from text.
    Returns (prefix_text, [floats]) or (text, []) if not enough found.
    """
    # Find the rightmost sequence of expected_count floats
    # Float: optional negative (- or –), digits, optional decimal
    float_pat = r'[-–]?\d+\.?\d*'
    # Build pattern for N trailing floats
    parts = [f'({float_pat})'] * expected_count
    pat = r'\s+'.join(parts) + r'\s*$'
    m = re.search(pat, text)
    if m:
        prefix = text[:m.start()].strip()
        vals = [float(m.group(i + 1).replace('–', '-').replace('−', '-')) for i in range(expected_count)]
        return prefix, vals
    return text.strip(), []


# ─── Table A.1 parsing ─────────────────────────────────────────────────────

def split_solvent_autonom(name_text, original_line):
    """Split combined name text into solvent_name and autonom_name
    using column positions from the original PDF layout line."""

    # Find where the row number ends
    m = re.match(r'^(\s*\d{1,4}\s+)', original_line)
    if not m:
        return name_text.strip(), ''

    name_start = m.end()

    # Get the portion of the line between the row number and the numeric columns
    # Find where the numeric columns start (from the right)
    line_after_num = original_line[name_start:]
    _, nums = extract_trailing_floats(line_after_num, 4)
    if nums:
        # Remove the numeric portion
        float_pat = r'[-–]?\d+\.?\d*'
        parts = [f'({float_pat})'] * 4
        pat = r'\s+'.join(parts) + r'\s*$'
        nm = re.search(pat, line_after_num)
        if nm:
            name_portion = line_after_num[:nm.start()].rstrip()
        else:
            name_portion = name_text
    else:
        name_portion = line_after_num.rstrip()

    # Split at a gap of 3+ spaces within the name portion
    gap_match = re.search(r'(\S)\s{3,}(\S)', name_portion)
    if gap_match:
        solvent = name_portion[:gap_match.start() + 1].strip()
        autonom = name_portion[gap_match.end() - 1:].strip()
        return solvent, autonom

    return name_portion.strip(), ''


def parse_table_a1(lines):
    """Parse Table A.1 lines into structured rows."""
    rows = []
    pending = None

    for line in lines:
        if is_page_marker(line) or is_table_header(line):
            continue
        if is_structure_line(line):
            continue

        stripped = line.strip()
        if not stripped:
            continue

        # Data row: starts with a number followed by 2+ spaces then name text
        m = re.match(r'^\s*(\d{1,4})\s{2,}(\S.*)', line)
        # Also match 4-digit numbers with single space, but ONLY if line has 3+ trailing floats
        if not m:
            m4 = re.match(r'^\s*(\d{4})\s([A-Za-z(].*)', line)
            if m4:
                _, test_nums = extract_trailing_floats(m4.group(2), 4)
                if not test_nums:
                    _, test_nums = extract_trailing_floats(m4.group(2), 3)
                if test_nums:
                    m = m4
        if m:
            no = int(m.group(1))
            rest = m.group(2)

            # Extract 4 trailing floats: dispersion, polarity, h-bonding, molar_volume
            name_part, nums = extract_trailing_floats(rest, 4)

            matched = False
            if nums and len(nums) == 4:
                if pending:
                    rows.append(pending)
                    pending = None

                solvent, autonom = split_solvent_autonom(name_part, line)
                solvent = re.sub(r'\*+$', '', solvent).strip()
                autonom = re.sub(r'\*+$', '', autonom).strip()

                rows.append({
                    'no': no,
                    'solvent_name': solvent,
                    'autonom_acd_name': autonom,
                    'dispersion': nums[0],
                    'polarity': nums[1],
                    'hydrogen_bonding': nums[2],
                    'molar_volume': nums[3],
                })
                matched = True
            elif not nums:
                # Try 3 trailing floats (some amine/acid salts have no molar volume)
                name_part3, nums3 = extract_trailing_floats(rest, 3)
                if nums3 and len(nums3) == 3 and no >= 1000:
                    if pending:
                        rows.append(pending)
                        pending = None

                    solvent, autonom = split_solvent_autonom(name_part3, line)
                    solvent = re.sub(r'\*+$', '', solvent).strip()
                    autonom = re.sub(r'\*+$', '', autonom).strip()

                    rows.append({
                        'no': no,
                        'solvent_name': solvent,
                        'autonom_acd_name': autonom,
                        'dispersion': nums3[0],
                        'polarity': nums3[1],
                        'hydrogen_bonding': nums3[2],
                        'molar_volume': '',
                    })
                    matched = True

            if not matched:
                # No trailing floats — multi-line entry, save as pending
                if pending:
                    rows.append(pending)

                solvent, autonom = split_solvent_autonom(name_part, line)
                solvent = re.sub(r'\*+$', '', solvent).strip()
                autonom = re.sub(r'\*+$', '', autonom).strip()

                pending = {
                    'no': no,
                    'solvent_name': solvent,
                    'autonom_acd_name': autonom,
                    'dispersion': None,
                    'polarity': None,
                    'hydrogen_bonding': None,
                    'molar_volume': None,
                    '_line': line,
                }
        else:
            # Continuation line
            if pending:
                # Try to complete with numeric data
                _, nums = extract_trailing_floats(stripped, 4)
                if nums and len(nums) == 4:
                    pending['dispersion'] = nums[0]
                    pending['polarity'] = nums[1]
                    pending['hydrogen_bonding'] = nums[2]
                    pending['molar_volume'] = nums[3]
                    rows.append(pending)
                    pending = None
                else:
                    # Name continuation text (autonom/ACD name wrapping)
                    txt = stripped.strip()
                    if len(txt) > 3 and not is_structure_line(line):
                        if not pending.get('autonom_acd_name'):
                            pending['autonom_acd_name'] = txt
                        else:
                            pending['autonom_acd_name'] += ' ' + txt
            else:
                # Continuation of the previous row's autonom name
                if rows and stripped and not is_structure_line(line):
                    leading = len(line) - len(line.lstrip())
                    txt = stripped.strip()
                    # ACD name continuations are indented well past column 30
                    if leading > 30 and len(txt) > 3 and not re.match(r'^\d', txt):
                        rows[-1]['autonom_acd_name'] += ' ' + txt

    if pending:
        rows.append(pending)

    # Split into valid and incomplete
    valid = []
    incomplete = []
    for r in rows:
        r.pop('_line', None)
        if r['dispersion'] is not None:
            valid.append(r)
        else:
            incomplete.append(r)

    return valid, incomplete


# ─── Table A.2 parsing ─────────────────────────────────────────────────────

def parse_table_a2(lines):
    """Parse Table A.2 lines into structured rows."""
    rows = []
    current_category = ''

    for line in lines:
        if is_page_marker(line) or is_table_header(line):
            continue

        stripped = line.strip()
        if not stripped:
            continue

        # Data row: starts with number (1-466), 2+ spaces, then polymer name + 4 numbers
        m = re.match(r'^\s*(\d{1,3})\s{2,}(\S.*)', line)
        if m:
            num = int(m.group(1))
            rest = m.group(2)

            # Only accept row numbers in range 1-466
            if num < 1 or num > 466:
                continue

            # Extract 4 trailing floats: dispersion, polar, h-bonding, radius
            name_part, nums = extract_trailing_floats(rest, 4)

            if nums and len(nums) == 4:
                polymer = name_part.strip()
                rows.append({
                    'number': num,
                    'polymer_name': polymer,
                    'category': current_category,
                    'dispersion': nums[0],
                    'polar': nums[1],
                    'hydrogen_bonding': nums[2],
                    'interaction_radius': nums[3],
                })
            else:
                # Some entries have dispersion merged into the name
                # e.g. "HDPE 18.00" with remaining 3 numbers
                name_part2, nums2 = extract_trailing_floats(rest, 3)
                if nums2 and len(nums2) == 3:
                    # Check if the name ends with what looks like the dispersion value
                    dm = re.search(r'\s+([-–]?\d+\.?\d*)\s*$', name_part2)
                    if dm:
                        disp = float(dm.group(1).replace('–', '-').replace('−', '-'))
                        polymer = name_part2[:dm.start()].strip()
                        rows.append({
                            'number': num,
                            'polymer_name': polymer,
                            'category': current_category,
                            'dispersion': disp,
                            'polar': nums2[0],
                            'hydrogen_bonding': nums2[1],
                            'interaction_radius': nums2[2],
                        })
                    else:
                        print(f"  WARN: A2 row {num} could not be fully parsed: {rest.strip()[:80]}")
                else:
                    print(f"  WARN: A2 row {num} has unexpected format: {rest.strip()[:80]}")
        else:
            # Category header: centered text, no leading number
            if (not re.match(r'^\s*\d', stripped) and
                len(stripped) > 3 and
                not is_structure_line(line) and
                not stripped.startswith('COMMENTS') and
                not stripped.startswith('POLYMER') and
                not stripped.startswith('These') and
                not stripped.startswith('This') and
                not stripped.startswith('The ') and
                not stripped.startswith('Data ') and
                not stripped.startswith('See ') and
                not stripped.startswith('Impro') and
                not stripped.startswith('Results') and
                not stripped.startswith('Based')):
                leading = len(line) - len(line.lstrip())
                if leading > 20:
                    current_category = stripped

    return rows


# ─── Post-processing cleanup ────────────────────────────────────────────────

# OCR word-split repairs: single letter separated from rest of word
OCR_WORD_FIXES = [
    (r'\bb utoxy', 'butoxy'),
    (r'\bb utyl', 'butyl'),
    (r'\bb uta-', 'buta-'),
    (r'\bb enzyl', 'benzyl'),
    (r'\bh ydroxy', 'hydroxy'),
    (r'\bEt ylene', 'Ethylene'),
    (r'\bIsopropen yl', 'Isopropenyl'),
    (r'\bEth yl', 'Ethyl'),
    (r'\bMeth yl', 'Methyl'),
    (r'\b([a-z]) ([a-z]{3,})', r'\1\2'),  # generic: single lowercase + space + 3+ lowercase
]

# Specific entry corrections based on PDF verification
A1_CORRECTIONS = {
    743: {
        'solvent_name': 'Bromotrichloro Methane (P from Dipole Moment)',
        'autonom_acd_name': 'Bromo-trichloro-methane',
    },
    744: {
        'solvent_name': 'Bromotrichloro Methane (P and H from Group cont.)',
        'autonom_acd_name': 'Bromo-trichloro-methane',
    },
    745: {
        'solvent_name': 'Bromotrichloro Methane (P from Group cont.)',
        'autonom_acd_name': 'Bromo-trichloro-methane',
    },
    79: {
        'solvent_name': 'Bromotrifluoromethane (Freon 1381)',
        'autonom_acd_name': 'Bromo-trifluoro methane',
    },
    154: {
        'solvent_name': 'Chlorodifluoromethane (Freon 22)',
        'autonom_acd_name': 'Chloro-difluoro-methane',
    },
    236: {
        'solvent_name': 'Dichlorodifluoromethane (Freon 12)',
        'autonom_acd_name': 'Dichloro-difluoro methane',
    },
    242: {
        'solvent_name': 'Dichloromonofluoromethane (Freon 21)',
        'autonom_acd_name': 'Dichloro-fluoro-methane',
    },
    133: {
        'solvent_name': '2-Chloro Propene (Isopropenyl Chloride)',
        'autonom_acd_name': '2-Chloro-propene',
    },
    264: {
        'solvent_name': 'Diethylene Glycol Butyl Ether Acetate Commercial',
        'autonom_acd_name': 'Acetic acid 2-(2-butoxy-ethoxy)-ethyl ester',
    },
    650: {
        'solvent_name': 'Trichlorofluoromethane (Freon 11)',
        'autonom_acd_name': 'Trichloro-fluoro methane',
    },
    652: {
        'solvent_name': '1,1,2-Trichlorotrifluoroethane (Freon 113)',
        'autonom_acd_name': '1,1,2-Trichloro-1,2,2-trifluoro-ethane',
    },
    662: {
        'solvent_name': 'Trifluoromethane (Freon 23)',
        'autonom_acd_name': 'Trifluoro-methane',
    },
    917: {
        'solvent_name': '1,4-Dihydroxybenzene (1,4-Benzenediol)',
        'autonom_acd_name': 'Benzene-1,4-diol',
    },
    555: {
        'solvent_name': 'Perfluoro Ethylene (Tetrafluoro Ethylene)',
        'autonom_acd_name': '1,1,2,2-Tetrafluoro ethene',
    },
    59: {
        'solvent_name': 'Benzyl Butyl Phthalate',
        'autonom_acd_name': 'Terephthalic acid 1-benzyl ester 4-butyl ester',
    },
    235: {
        'solvent_name': 'Di-(2-Chloroethyl) Ether',
        'autonom_acd_name': '1-Chloro-2-(2-chloro-ethoxy)-ethane',
    },
    557: {
        'solvent_name': 'Perfluoroheptane',
        'autonom_acd_name': '1,1,1,2,2,3,3,4,4,5,5,6,6,7,7,7-Hexadecafluoro heptane',
    },
    276: {
        'solvent_name': 'Dihydrogen Disulfide',
    },
    424: {
        'solvent_name': 'Hydrogen Sulfide',
    },
}


def cleanup_a1(rows):
    """Apply OCR word-split fixes and manual corrections to A.1 rows."""
    corrected = []
    for r in rows:
        no = r['no']

        # Step 1: Apply OCR word-split fixes FIRST (so prefix matching works)
        for field in ['solvent_name', 'autonom_acd_name']:
            val = r.get(field, '')
            for pat, repl in OCR_WORD_FIXES:
                val = re.sub(pat, repl, val)
            # Remove stray structure fragments that got into names
            val = re.sub(r'\s+[A-Z]\s+[A-Z](?:\s+[A-Z])*\s*$', '', val)
            # Clean up extra whitespace
            val = re.sub(r'\s{2,}', ' ', val).strip()
            r[field] = val

        # Step 2: Apply manual corrections for verified entries
        if no in A1_CORRECTIONS:
            corr = A1_CORRECTIONS[no]
            expected_prefix = corr.get('solvent_name', '')[:15]
            if r['solvent_name'].startswith(expected_prefix) or not r.get('autonom_acd_name'):
                for k, v in corr.items():
                    r[k] = v
                corrected.append(no)

    return rows, corrected


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    with open(RAW_TXT) as f:
        all_lines = f.readlines()

    # Find section boundaries
    a1_end = None
    a2_start = None
    for i, line in enumerate(all_lines):
        if 'COMMENTS TO TABLE A.2' in line:
            a1_end = i
        if re.match(r'\s*TABLE A\.2\s*$', line.strip()) and a2_start is None and a1_end is not None:
            a2_start = i

    if a1_end is None or a2_start is None:
        print("ERROR: Could not find table boundaries")
        sys.exit(1)

    a1_lines = all_lines[:a1_end]
    a2_lines = all_lines[a2_start:]

    print(f"Table A.1: lines 1–{a1_end} ({a1_end} lines)")
    print(f"Table A.2: lines {a2_start + 1}–{len(all_lines)} ({len(all_lines) - a2_start} lines)")

    # Parse
    a1_rows, a1_incomplete = parse_table_a1(a1_lines)
    a2_rows = parse_table_a2(a2_lines)

    print(f"\nTable A.1: {len(a1_rows)} rows parsed, {len(a1_incomplete)} incomplete")
    print(f"Table A.2: {len(a2_rows)} rows parsed")

    # Cleanup
    a1_rows, corrected_nos = cleanup_a1(a1_rows)
    if corrected_nos:
        print(f"\nLLM-equivalent corrections applied to {len(corrected_nos)} A.1 entries: {corrected_nos}")

    if a1_incomplete:
        print("\nIncomplete A.1 rows:")
        for r in a1_incomplete:
            print(f"  #{r['no']}: {r['solvent_name'][:60]}")

    # ─── Validation ─────────────────────────────────────────────────────
    print("\n=== Validation ===")
    errors = []

    a1_empty_mv = 0
    for r in a1_rows:
        for col in ['dispersion', 'polarity', 'hydrogen_bonding', 'molar_volume']:
            val = r[col]
            if col == 'molar_volume' and val == '':
                a1_empty_mv += 1
                continue
            try:
                float(val)
            except (ValueError, TypeError):
                errors.append(f"A1 #{r['no']}: non-numeric {col}={val}")
    if a1_empty_mv:
        print(f"  ({a1_empty_mv} entries with no molar volume — amine/acid salts)")

    for r in a2_rows:
        for col in ['dispersion', 'polar', 'hydrogen_bonding', 'interaction_radius']:
            try:
                float(r[col])
            except (ValueError, TypeError):
                errors.append(f"A2 #{r['number']}: non-numeric {col}={r[col]}")

    if errors:
        print(f"Found {len(errors)} errors:")
        for e in errors:
            print(f"  {e}")
    else:
        print("All numeric columns parse cleanly as float.")

    # Check A2 coverage
    a2_nums = {r['number'] for r in a2_rows}
    expected_a2 = set(range(1, 467))
    missing_a2 = sorted(expected_a2 - a2_nums)
    if missing_a2:
        print(f"\nA2 missing row numbers ({len(missing_a2)}): {missing_a2}")
    else:
        print(f"\nA2: all 466 rows present!")

    # ─── Sample rows ────────────────────────────────────────────────────
    print("\n=== Sample A.1 rows ===")
    for r in a1_rows[:8]:
        print(f"  #{r['no']:4d}  {r['solvent_name'][:35]:35s}  {r['autonom_acd_name'][:35]:35s}  "
              f"{r['dispersion']:5.1f} {r['polarity']:5.1f} {r['hydrogen_bonding']:5.1f} {r['molar_volume']:6.1f}")
    print(f"  ... ({len(a1_rows)} total)")

    print("\n=== Sample A.2 rows ===")
    for r in a2_rows[:8]:
        print(f"  #{r['number']:3d}  {r['polymer_name'][:35]:35s}  [{r['category'][:20]}]  "
              f"{r['dispersion']:6.2f} {r['polar']:6.2f} {r['hydrogen_bonding']:6.2f} {r['interaction_radius']:6.2f}")
    print(f"  ... ({len(a2_rows)} total)")

    # ─── Suspicious entries ─────────────────────────────────────────────
    print("\n=== Suspicious A.1 entries ===")
    suspicious_a1 = []
    for r in a1_rows:
        name = r['solvent_name']
        if not r['autonom_acd_name']:
            suspicious_a1.append(f"  #{r['no']:4d}: missing autonom — '{name}'")
        if len(name) < 3:
            suspicious_a1.append(f"  #{r['no']:4d}: very short name — '{name}'")

    if suspicious_a1:
        print(f"{len(suspicious_a1)} entries:")
        for s in suspicious_a1[:25]:
            print(s)
        if len(suspicious_a1) > 25:
            print(f"  ... and {len(suspicious_a1) - 25} more")
    else:
        print("None.")

    # ─── Write CSVs ─────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(OUT_A1), exist_ok=True)

    with open(OUT_A1, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['no', 'solvent_name', 'autonom_acd_name',
                                           'dispersion', 'polarity', 'hydrogen_bonding',
                                           'molar_volume'])
        w.writeheader()
        w.writerows(a1_rows)

    with open(OUT_A2, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['number', 'polymer_name', 'category',
                                           'dispersion', 'polar', 'hydrogen_bonding',
                                           'interaction_radius'])
        w.writeheader()
        w.writerows(a2_rows)

    print(f"\nWrote {OUT_A1} ({len(a1_rows)} rows)")
    print(f"Wrote {OUT_A2} ({len(a2_rows)} rows)")


if __name__ == '__main__':
    main()
