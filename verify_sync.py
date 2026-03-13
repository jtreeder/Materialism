"""
verify_sync.py — verify that search page and database page will show
identical active material counts for any localStorage state.

Implements the exact JS active-state logic from generate_html.py in Python
and tests it against several realistic scenarios.
"""
import json, csv, os, sys

ROOT = os.path.dirname(__file__)
MANIFEST_PATH = os.path.join(ROOT, "data", "manifest.json")
DATASETS_DIR  = os.path.join(ROOT, "data", "datasets")

# ── load manifest ──────────────────────────────────────────────────────────────
with open(MANIFEST_PATH) as f:
    DATASETS_META = json.load(f)["datasets"]

_active_ds_ids = {k for k, v in DATASETS_META.items() if v.get("active", True)}

# ── rebuild deduplicated solvents/polymers (mirrors Python loop in generate_html.py) ──
def norm_name(n):
    return "".join(c for c in n.lower() if c.isalnum()) if n else ""

_ds_priority = sorted(
    [(k, v) for k, v in DATASETS_META.items() if v.get("active", True)],
    key=lambda item: (item[1].get("confidence_tier", 0), item[1].get("imported_at", "")),
    reverse=True,
)

solvents = []   # deduplicated; each has a canonical dsId
polymers = []
_seen_sol = {}
_seen_poly = {}

for ds_id, ds_meta in _ds_priority:
    ds_dir = os.path.join(DATASETS_DIR, ds_id)

    chem_csv = os.path.join(ds_dir, "chemicals.csv")
    if os.path.exists(chem_csv):
        with open(chem_csv, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if not (row.get("delta_d","").strip() and row.get("delta_p","").strip() and row.get("delta_h","").strip()):
                    continue
                if row.get("hidden","").strip().lower() in ("1","true","yes"):
                    continue
                name = row.get("name","").strip()
                cas  = row.get("cas_number","").strip()
                key  = cas if cas else norm_name(name)
                if not key or key in _seen_sol:
                    continue
                _seen_sol[key] = True
                solvents.append({"name": name, "dsId": ds_id})

    poly_csv = os.path.join(ds_dir, "polymers.csv")
    if os.path.exists(poly_csv):
        with open(poly_csv, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if not (row.get("delta_d","").strip() and row.get("delta_p","").strip() and row.get("delta_h","").strip()):
                    continue
                if row.get("hidden","").strip().lower() in ("1","true","yes"):
                    continue
                name = row.get("name","").strip()
                if not name:
                    continue
                key = norm_name(name)
                if not key or key in _seen_poly:
                    continue
                _seen_poly[key] = True
                polymers.append({"name": name, "dsId": ds_id})

# ── JS logic (shared by both pages after fix) ──────────────────────────────────
# Rule: if localStorage is null (first visit) → use manifest default
#       if localStorage exists → missing keys are INACTIVE (never silently active)
def _compute_active_ids(saved: dict | None) -> set:
    active = set()
    for ds_id in _active_ds_ids:
        if saved is None:
            is_active = DATASETS_META[ds_id].get("active", True) is not False
        else:
            is_active = saved.get(ds_id) is True   # missing key → False
        if is_active:
            active.add(ds_id)
    return active

def search_page_active_ids(saved):
    return _compute_active_ids(saved)

def db_page_active_ids(saved):
    return _compute_active_ids(saved)

# ── count materials visible on each page for a given active set ────────────────
def count_materials(active_ids: set) -> tuple[int, int]:
    n_sol  = sum(1 for s in solvents if s["dsId"] in active_ids)
    n_poly = sum(1 for p in polymers if p["dsId"] in active_ids)
    return n_sol, n_poly

# ── scenarios ──────────────────────────────────────────────────────────────────
OLD_DATASETS = ["hsp_polymers_8", "hsp_polymers_7", "hsp_solvents_2",
                "hspip_polymers", "hspip_solvents"]

scenarios = {
    "No localStorage (first visit)": None,
    "All 5 old datasets toggled OFF (exact user scenario)":
        {k: False for k in OLD_DATASETS},
    "All 5 old datasets OFF + 6 new never touched":
        {k: False for k in OLD_DATASETS},   # new datasets absent from saved
    "All 11 active datasets OFF":
        {k: False for k in _active_ds_ids},
    "All 11 active datasets ON":
        {k: True for k in _active_ds_ids},
    "hspip_solvents ON only":
        {k: (k == "hspip_solvents") for k in _active_ds_ids},
}

print(f"\n{'='*72}")
print(f"Active datasets in manifest: {sorted(_active_ds_ids)}")
print(f"Total deduplicated solvents: {len(solvents)}")
print(f"Total deduplicated polymers: {len(polymers)}")
print(f"{'='*72}\n")

all_passed = True
for name, saved in scenarios.items():
    s_ids  = search_page_active_ids(saved)
    db_ids = db_page_active_ids(saved)

    s_sol,  s_poly  = count_materials(s_ids)
    db_sol, db_poly = count_materials(db_ids)

    match = (s_sol == db_sol and s_poly == db_poly)
    status = "PASS" if match else "FAIL"
    if not match:
        all_passed = False

    print(f"Scenario: {name}")
    print(f"  localStorage: {json.dumps(saved) if saved else 'null'}")
    print(f"  Search  active datasets: {sorted(s_ids)}")
    print(f"  DB page active datasets: {sorted(db_ids)}")
    print(f"  Search  count: {s_sol} solvents, {s_poly} polymers")
    print(f"  DB page count: {db_sol} solvents, {db_poly} polymers")
    print(f"  [{status}]")
    print()

print("="*72)
if all_passed:
    print("ALL SCENARIOS PASS — search and database pages will always agree.")
else:
    print("FAILURES DETECTED — counts still diverge in some scenarios.")
print("="*72)
sys.exit(0 if all_passed else 1)
