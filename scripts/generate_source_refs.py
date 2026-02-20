"""Generate source reference data for the CAS review tool.

For each candidate chemical, this script:
1. hansen_a1 entries: finds the chemical in the PDF, renders a cropped row image
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


def main():
    os.makedirs(CROP_DIR, exist_ok=True)

    with open(CANDIDATES_JSON) as f:
        candidates = json.load(f)

    print(f"Loading source data...")
    wolfram_idx = _load_wolfram_index()
    pang_idx = _load_pang_index()
    doc = fitz.open(PDF_PATH)
    print(f"PDF: {len(doc)} pages")

    pdf_found = 0
    csv_found = 0

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
                entry["source_ref"] = {
                    "type": "pdf",
                    "page": page_idx + 1,  # 1-indexed for display
                    "total_pages": len(doc),
                    "crop_file": crop_file,
                    "raw_line": raw_line,
                }
                pdf_found += 1
            else:
                entry["source_ref"] = {
                    "type": "pdf",
                    "page": None,
                    "crop_file": None,
                    "raw_line": None,
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
    print(f"  CSV rows found: {csv_found}")
    print(f"  Total candidates enriched: {pdf_found + csv_found}/{len(candidates)}")


if __name__ == "__main__":
    main()
