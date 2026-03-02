#!/usr/bin/env python3
"""Fetch ClassyFire classifications for solvents.

Strategy:
  1. Try ClassyFire entity endpoint by InChIKey (fast, pre-classified compounds).
  2. For misses: fetch CanonicalSMILES from PubChem, then submit to ClassyFire
     query API for on-demand classification.

Cache: data/classyfire_cache.json  { CAS: {class, subclass, inchikey} }
Run once (or incrementally); generate_html.py reads the cache.
"""
import csv, json, os, sys, time
import urllib.request, urllib.parse
import concurrent.futures

BASE       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_PATH = os.path.join(BASE, "data", "classyfire_cache.json")
CHEM_CSV   = os.path.join(BASE, "data", "processed", "unified_chemicals.csv")

CF_ENTITY  = "http://classyfire.wishartlab.com/entities/{}.json"
CF_QUERY   = "http://classyfire.wishartlab.com/queries.json"
CF_RESULT  = "http://classyfire.wishartlab.com/queries/{}.json"
PUBCHEM    = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{}/property/{}/JSON"


def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2, sort_keys=True)


def fetch_url(url, timeout=15, data=None, headers=None):
    try:
        h = {"User-Agent": "Materialism/1.0 (research)"}
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, data=data, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8")
    except Exception:
        return None


def pubchem_props(cas, props="InChIKey,IsomericSMILES"):
    url = PUBCHEM.format(urllib.parse.quote(cas), props)
    raw = fetch_url(url)
    if raw:
        try:
            obj = json.loads(raw)
            items = obj.get("PropertyTable", {}).get("Properties", [])
            if items:
                return items[0]
        except Exception:
            pass
    return {}


def classyfire_entity(inchikey):
    raw = fetch_url(CF_ENTITY.format(inchikey))
    if raw:
        try:
            obj = json.loads(raw)
            if obj.get("class") or obj.get("subclass"):
                return {
                    "class":    (obj.get("class") or {}).get("name", ""),
                    "subclass": (obj.get("subclass") or {}).get("name", ""),
                }
        except Exception:
            pass
    return None


# ── Phase 1: entity lookup (fast path) ──────────────────────────────────────

def phase1_worker(cas, cache):
    props = pubchem_props(cas)
    inchikey = props.get("InChIKey", "")
    smiles   = props.get("SMILES", "") or props.get("IsomericSMILES", "") or props.get("CanonicalSMILES", "") or props.get("ConnectivitySMILES", "")
    if not inchikey:
        cache[cas] = {"class": "", "subclass": "", "inchikey": "", "smiles": ""}
        return
    cf = classyfire_entity(inchikey)
    if cf:
        cache[cas] = {"class": cf["class"], "subclass": cf["subclass"],
                      "inchikey": inchikey, "smiles": smiles}
    else:
        cache[cas] = {"class": "", "subclass": "", "inchikey": inchikey, "smiles": smiles}


def run_phase1(remaining, cache, workers=8):
    print(f"Phase 1: entity lookup for {len(remaining)} CAS numbers ({workers} workers)...")
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(phase1_worker, c, cache): c for c in remaining}
        for fut in concurrent.futures.as_completed(futs):
            fut.result()
            done += 1
            if done % 100 == 0 or done == len(remaining):
                save_cache(cache)
                hits = sum(1 for v in cache.values() if v.get("subclass") or v.get("class"))
                print(f"  {done}/{len(remaining)}  |  {hits} classified so far")


# ── Phase 2: query API for compounds with SMILES but no classification ───────

def submit_classyfire_query(smiles_list):
    """Submit a batch of SMILES to ClassyFire query API. Returns query_id or None."""
    body = json.dumps({
        "label":       "materialism_batch",
        "query_input": "\n".join(smiles_list),
        "query_type":  "STRUCTURE",
    }).encode("utf-8")
    raw = fetch_url(
        CF_QUERY, data=body, timeout=30,
        headers={"Content-Type": "application/json", "Accept": "application/json"}
    )
    if raw:
        try:
            obj = json.loads(raw)
            return str(obj.get("id", ""))
        except Exception:
            pass
    return None


def poll_classyfire_query(qid, max_wait=300, interval=10):
    """Poll until ClassyFire query is done. Returns list of entity dicts."""
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(interval)
        elapsed += interval
        raw = fetch_url(CF_RESULT.format(qid), timeout=20)
        if not raw:
            continue
        try:
            obj = json.loads(raw)
            if obj.get("classification_status") == "Done":
                return obj.get("entities", [])
        except Exception:
            pass
        print(f"    ... waiting ({elapsed}s)", flush=True)
    return []


def run_phase2(cache):
    """For compounds with SMILES but no classification, submit query to ClassyFire."""
    # Collect candidates: have smiles + inchikey, but no class yet
    to_classify = {
        cas: v for cas, v in cache.items()
        if v.get("smiles") and v.get("inchikey") and not v.get("class") and not v.get("subclass")
    }
    if not to_classify:
        print("Phase 2: nothing to classify via query API.")
        return

    print(f"Phase 2: submitting {len(to_classify)} SMILES to ClassyFire query API...")

    # Map inchikey → cas for result matching
    ik_to_cas = {v["inchikey"]: cas for cas, v in to_classify.items()}

    # Submit in batches of 100
    batch_size = 100
    items = list(to_classify.items())
    total_classified = 0

    for start in range(0, len(items), batch_size):
        batch = items[start:start + batch_size]
        smiles_list = [v["smiles"] for _, v in batch]
        print(f"  Submitting batch {start//batch_size + 1} ({len(batch)} SMILES)...", flush=True)

        qid = submit_classyfire_query(smiles_list)
        if not qid:
            print("    Failed to submit query — skipping batch.")
            continue

        print(f"    Query ID: {qid}  Polling...", flush=True)
        entities = poll_classyfire_query(qid)
        if not entities:
            print("    No results returned.")
            continue

        for ent in entities:
            ik = ent.get("inchikey", "").removeprefix("InChIKey=")
            cas = ik_to_cas.get(ik)
            if not cas:
                continue
            cf_class    = (ent.get("class")    or {}).get("name", "")
            cf_subclass = (ent.get("subclass") or {}).get("name", "")
            if cf_class or cf_subclass:
                cache[cas]["class"]    = cf_class
                cache[cas]["subclass"] = cf_subclass
                total_classified += 1

        save_cache(cache)
        print(f"    Batch done, {total_classified} classified so far.")

    return total_classified


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    cas_list = []
    seen = set()
    with open(CHEM_CSV) as f:
        for row in csv.DictReader(f):
            cas = row.get("cas_number", "").strip()
            if cas and cas not in seen:
                cas_list.append(cas)
                seen.add(cas)

    cache = load_cache()
    remaining = [c for c in cas_list if c not in cache]
    print(f"Total CAS: {len(cas_list)}  |  Cached: {len(cache)}  |  To fetch: {len(remaining)}")

    workers = int(os.environ.get("CF_WORKERS", "8"))

    if remaining:
        run_phase1(remaining, cache, workers=workers)

    # Phase 2: query API for any with SMILES but still unclassified
    run_phase2(cache)

    # Summary
    hits     = sum(1 for v in cache.values() if v.get("subclass") or v.get("class"))
    subclass = sum(1 for v in cache.values() if v.get("subclass"))
    no_ik    = sum(1 for v in cache.values() if not v.get("inchikey"))
    print(f"\nFinal: {len(cache)} cached | {hits} classified | {subclass} with subclass | {no_ik} no InChIKey")


if __name__ == "__main__":
    main()
