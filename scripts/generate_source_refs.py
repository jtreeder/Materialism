"""Generate source reference data for the CAS review tool.

For each candidate chemical, this script:
1. hansen_a1 entries: finds the chemical in the PDF, renders a cropped row image
   AND extracts a separate structure diagram image + ACD/Autonom name
2. wolfram entries: extracts the raw row from wolfram_hsp.csv
3. pang2024 entries: extracts the raw row from hansen_1k_smiles_shorter.csv
4. Writes enriched candidates JSON with source_ref data

Requires: PyMuPDF (fitz)

Usage: python scripts/generate_source_refs.py
"""

import csv
import json
import os
import re

import fitz  # PyMuPDF

SCRIPT_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROC_DIR = os.path.join(DATA_DIR, "processed")
CROP_DIR = os.path.join(PROC_DIR, "source_crops")
STRUCT_DIR = os.path.join(PROC_DIR, "structure_crops")
CANDIDATES_JSON = os.path.join(PROC_DIR, "cas_candidates.json")
PDF_PATH = os.path.join(RAW_DIR, "a1 and a2 only.pdf")
WOLFRAM_CSV = os.path.join(RAW_DIR, "wolfram_hsp.csv")
PANG_CSV = os.path.join(RAW_DIR, "hansen_1k_smiles_shorter.csv")

# Crop settings
CROP_DPI = 200       # resolution for rendered page
ROW_PAD_TOP = 8      # points above the found text
ROW_PAD_BOTTOM = 8   # points below the found text
PAGE_MARGIN_LEFT = 55   # left margin to start crop (skip page number gutter)
PAGE_MARGIN_RIGHT = 10  # right margin
STRUCT_DPI = 250     # higher DPI for structure diagrams
STRUCT_X_RIGHT = 210 # right boundary of structure column (before ACD name column)


def _load_wolfram_index():
    """Load wolfram CSV into a dict keyed by cleaned solvent name."""
    index = {}
    with open(WOLFRAM_CSV) as f:
        for row in csv.DictReader(f):
            name = row.get("Solvent", "").strip()
            index[name] = row
            # Also index without commas/spaces for fuzzy matching
            key = re.sub(r"[^a-zA-Z0-9]", "", name).lower()
            index[key] = row
    return index


def _load_pang_index():
    """Load pang2024 CSV into a dict keyed by molecule name."""
    index = {}
    with open(PANG_CSV) as f:
        for row in csv.DictReader(f):
            name = row.get("Molecule", "").strip()
            index[name] = row
            key = re.sub(r"[^a-zA-Z0-9]", "", name).lower()
            index[key] = row
    return index


def _find_in_pdf(doc, name):
    """Search for a chemical name across all PDF pages.
    Returns (page_index, rect) or (None, None)."""
    # Try exact search first
    for i in range(len(doc)):
        page = doc[i]
        rects = page.search_for(name)
        if rects:
            return i, rects[0]

    # Try case-insensitive by searching lowercase
    name_lower = name.lower()
    for i in range(len(doc)):
        page = doc[i]
        text = page.get_text()
        # Find approximate position by line
        for line_idx, line in enumerate(text.split("\n")):
            if name_lower in line.lower():
                # Get text instances near this area
                rects = page.search_for(name[:min(len(name), 20)])
                if rects:
                    return i, rects[0]
                # Fallback: search for first significant word
                words = name.split()
                if len(words) >= 2:
                    rects = page.search_for(words[0])
                    if rects:
                        return i, rects[0]
    return None, None


def _render_crop(doc, page_idx, rect, out_path):
    """Render a cropped strip of the PDF page around the given rect."""
    page = doc[page_idx]
    page_rect = page.rect

    # Define crop area: full table width, centered on the found text
    y_top = max(0, rect.y0 - ROW_PAD_TOP)
    y_bottom = min(page_rect.height, rect.y1 + ROW_PAD_BOTTOM)

    # Ensure minimum height for readability
    if y_bottom - y_top < 30:
        y_top = max(0, rect.y0 - 15)
        y_bottom = min(page_rect.height, rect.y1 + 15)

    clip = fitz.Rect(
        PAGE_MARGIN_LEFT,
        y_top,
        page_rect.width - PAGE_MARGIN_RIGHT,
        y_bottom
    )

    # Render at target DPI
    zoom = CROP_DPI / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, clip=clip)
    pix.save(out_path)
    return True


def _find_raw_line_in_pdf(doc, page_idx, rect):
    """Extract the raw text line from the PDF around the found rect."""
    page = doc[page_idx]
    # Get text in a wider band around the rect
    clip = fitz.Rect(
        PAGE_MARGIN_LEFT,
        rect.y0 - 2,
        page.rect.width - PAGE_MARGIN_RIGHT,
        rect.y1 + 2
    )
    text = page.get_text("text", clip=clip).strip()
    # Clean up to single line
    return " ".join(text.split())


def _get_entry_positions(page):
    """Get all table entry positions on a PDF page.
    Returns list of dict with y, number, name sorted by y."""
    blocks = page.get_text("dict")["blocks"]
    text_items = []
    for b in blocks:
        if b["type"] == 0:
            for line in b["lines"]:
                for span in line["spans"]:
                    t = span["text"].strip()
                    if t:
                        text_items.append({
                            "x": span["origin"][0],
                            "y": span["origin"][1],
                            "text": t
                        })
    text_items.sort(key=lambda x: (x["y"], x["x"]))

    # Group into rows by y proximity
    rows = []
    current_row = []
    current_y = None
    for item in text_items:
        if current_y is None or abs(item["y"] - current_y) < 3:
            current_row.append(item)
            if current_y is None:
                current_y = item["y"]
        else:
            if current_row:
                rows.append(current_row)
            current_row = [item]
            current_y = item["y"]
    if current_row:
        rows.append(current_row)

    # Identify table entry rows (have a row number at x<70)
    entries = []
    for row in rows:
        num_items = [r for r in row if r["x"] < 70 and r["text"].isdigit()]
        name_items = [r for r in row if 70 <= r["x"] < 210]
        acd_items = [r for r in row if 210 <= r["x"] < 295]
        if num_items and name_items:
            name = " ".join(n["text"] for n in sorted(name_items, key=lambda x: x["x"]))
            acd = " ".join(a["text"] for a in sorted(acd_items, key=lambda x: x["x"]))
            entries.append({
                "y": row[0]["y"],
                "number": num_items[0]["text"],
                "name": name,
                "acd_name": acd.strip(),
            })
    entries.sort(key=lambda e: e["y"])
    return entries


def _extract_acd_name(raw_line, original_name):
    """Parse the ACD/Autonom name from a raw text line.
    Format: '[num] [solvent_name] [acd_name] [delta_d] [delta_p] [delta_h] [mv]'
    """
    if not raw_line:
        return None
    # Remove the row number prefix
    line = re.sub(r"^\d+\s+", "", raw_line)
    # Find the numeric HSP values at the end (3-4 numbers)
    m = re.search(r"\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s*$", line)
    if not m:
        return None
    # Everything between original name and the HSP values is the ACD name
    before_numbers = line[:m.start()].strip()
    # Try to remove the original name prefix
    # The original name might have OCR errors, so try prefix matching
    name_clean = original_name.strip()
    if before_numbers.startswith(name_clean):
        acd = before_numbers[len(name_clean):].strip()
    else:
        # Try removing first word group that looks like the solvent name
        # Split at double space or at the ACD name column position
        parts = re.split(r"\s{2,}", before_numbers)
        if len(parts) >= 2:
            acd = parts[-1].strip()
        else:
            acd = None
    if acd and len(acd) > 2:
        return acd
    return None


def _render_structure_crop(doc, page_idx, rect, out_path):
    """Render the molecular structure diagram below the name text row.
    The structure sits between the name row and the next entry."""
    page = doc[page_idx]
    page_rect = page.rect

    # Get all entry positions on this page to find the next entry
    entries = _get_entry_positions(page)
    current_y = rect.y0
    next_y = None
    for e in entries:
        # Next entry must be significantly below (at least 20pt gap)
        if e["y"] > current_y + 20:
            next_y = e["y"]
            break

    # Structure region: from below the name text to above the next entry
    y_top = rect.y1 + 2
    if next_y:
        y_bottom = next_y - 5
    else:
        # Last entry on page: use remaining space, capped at 60pt
        y_bottom = min(page_rect.height - 20, rect.y1 + 60)

    # Structure must have meaningful height
    if y_bottom - y_top < 15:
        return False

    # Crop the structure column (left portion where structures are drawn)
    clip = fitz.Rect(
        PAGE_MARGIN_LEFT,
        y_top,
        STRUCT_X_RIGHT,
        y_bottom
    )

    zoom = STRUCT_DPI / 72.0
    mat = fitz.Matrix(zoom, zoom)
    try:
        pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
    except Exception:
        return False

    if pix.width < 5 or pix.height < 5:
        return False

    # Check if the image has any actual drawn content (not all white)
    samples = pix.samples
    dark_count = sum(1 for i in range(0, len(samples), 30) if samples[i] < 180)
    if dark_count < 5:
        return False

    pix.save(out_path)
    return True


def main():
    os.makedirs(CROP_DIR, exist_ok=True)
    os.makedirs(STRUCT_DIR, exist_ok=True)

    with open(CANDIDATES_JSON) as f:
        candidates = json.load(f)

    print(f"Loading source data...")
    wolfram_idx = _load_wolfram_index()
    pang_idx = _load_pang_index()
    doc = fitz.open(PDF_PATH)
    print(f"PDF: {len(doc)} pages")

    pdf_found = 0
    csv_found = 0
    struct_found = 0
    acd_found = 0

    for entry in candidates:
        source = entry.get("source", "")
        name = entry["original_name"]

        if source == "hansen_a1":
            page_idx, rect = _find_in_pdf(doc, name)
            if page_idx is not None:
                crop_file = f"source_crops/{entry['row_index']}.png"
                crop_path = os.path.join(PROC_DIR, crop_file)
                _render_crop(doc, page_idx, rect, crop_path)
                raw_line = _find_raw_line_in_pdf(doc, page_idx, rect)

                # Extract ACD name from the raw text line
                acd_name = _extract_acd_name(raw_line, name)
                if not acd_name:
                    # Try getting ACD name from page entry positions
                    page_entries = _get_entry_positions(doc[page_idx])
                    for pe in page_entries:
                        if pe["name"].startswith(name[:10]):
                            acd_name = pe.get("acd_name")
                            break
                if acd_name:
                    acd_found += 1

                # Extract structure diagram image
                struct_file = f"structure_crops/{entry['row_index']}.png"
                struct_path = os.path.join(PROC_DIR, struct_file)
                has_struct = _render_structure_crop(doc, page_idx, rect, struct_path)
                if has_struct:
                    struct_found += 1
                else:
                    struct_file = None

                entry["source_ref"] = {
                    "type": "pdf",
                    "page": page_idx + 1,  # 1-indexed for display
                    "total_pages": len(doc),
                    "crop_file": crop_file,
                    "structure_file": struct_file,
                    "raw_line": raw_line,
                    "acd_name": acd_name,
                }
                pdf_found += 1
            else:
                entry["source_ref"] = {
                    "type": "pdf",
                    "page": None,
                    "crop_file": None,
                    "structure_file": None,
                    "raw_line": None,
                    "acd_name": None,
                    "note": "Could not locate in PDF"
                }

        elif source == "wolfram":
            key = re.sub(r"[^a-zA-Z0-9]", "", name).lower()
            row = wolfram_idx.get(name) or wolfram_idx.get(key)
            if row:
                entry["source_ref"] = {
                    "type": "csv",
                    "file": "wolfram_hsp.csv",
                    "url": "https://datarepository.wolframcloud.com/resources/JoshuaSchrier_Hansen-Solubility-Parameters/",
                    "raw_row": dict(row),
                }
                csv_found += 1
            else:
                entry["source_ref"] = {
                    "type": "csv",
                    "file": "wolfram_hsp.csv",
                    "raw_row": None,
                    "note": "Could not find in source CSV"
                }

        elif source == "pang2024":
            key = re.sub(r"[^a-zA-Z0-9]", "", name).lower()
            row = pang_idx.get(name) or pang_idx.get(key)
            if row:
                entry["source_ref"] = {
                    "type": "csv",
                    "file": "hansen_1k_smiles_shorter.csv",
                    "url": "https://github.com/jiayunpang/hsp_embedding",
                    "raw_row": dict(row),
                }
                csv_found += 1
            else:
                entry["source_ref"] = {
                    "type": "csv",
                    "file": "hansen_1k_smiles_shorter.csv",
                    "raw_row": None,
                    "note": "Could not find in source CSV"
                }

    doc.close()

    # Save enriched candidates
    with open(CANDIDATES_JSON, "w") as f:
        json.dump(candidates, f, indent=1)

    print(f"\nDone!")
    print(f"  PDF crops generated: {pdf_found}")
    print(f"  Structure images extracted: {struct_found}")
    print(f"  ACD names extracted: {acd_found}")
    print(f"  CSV rows found: {csv_found}")
    print(f"  Total candidates enriched: {pdf_found + csv_found}/{len(candidates)}")


if __name__ == "__main__":
    main()
