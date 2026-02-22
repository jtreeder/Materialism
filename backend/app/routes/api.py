"""Flask API blueprint for dataset management.

Endpoints:
    POST /api/datasets/upload      — Upload and analyze a file
    POST /api/datasets/analyze-url — Fetch a URL and analyze it
    POST /api/datasets/search      — Claude-powered HSP database search
    POST /api/datasets/import      — Import an analyzed dataset
    GET  /api/datasets             — List all datasets
    PATCH /api/datasets/<id>       — Update dataset metadata
    DELETE /api/datasets/<id>      — Remove a dataset
    POST /api/build                — Rebuild unified database + HTML
"""

import json
import os
import subprocess
import sys
import tempfile
import uuid

from flask import Blueprint, jsonify, request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, BASE_DIR)

from lib.import_utils import (
    analyze_dataset,
    detect_file_type,
    load_manifest,
    normalize_and_write,
    remove_dataset,
    save_manifest,
    DATASETS_DIR,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")

# Server-side storage for pending analyses (analysis_id -> filepath)
_pending_analyses = {}


@api_bp.route("/datasets/upload", methods=["POST"])
def upload_dataset():
    """Accept a file upload and return an analysis report."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400

    # Save to temp location
    suffix = os.path.splitext(f.filename)[1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=tempfile.gettempdir())
    f.save(tmp.name)
    tmp.close()

    try:
        report = analyze_dataset(tmp.name)
        report["original_filename"] = f.filename
        _pending_analyses[report["analysis_id"]] = tmp.name
        return jsonify(report)
    except Exception as e:
        os.unlink(tmp.name)
        return jsonify({"error": str(e)}), 500


@api_bp.route("/datasets/analyze-url", methods=["POST"])
def analyze_url():
    """Fetch a URL and analyze the downloaded file."""
    data = request.get_json(force=True)
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    import requests as req

    try:
        resp = req.get(url, timeout=30, stream=True)
        resp.raise_for_status()
    except Exception as e:
        return jsonify({"error": f"Failed to fetch URL: {e}"}), 400

    # Determine extension from URL or content-type
    from urllib.parse import urlparse
    parsed = urlparse(url)
    ext = os.path.splitext(parsed.path)[1]
    if not ext:
        ct = resp.headers.get("content-type", "")
        if "csv" in ct:
            ext = ".csv"
        elif "json" in ct:
            ext = ".json"
        elif "excel" in ct or "spreadsheet" in ct:
            ext = ".xlsx"
        elif "pdf" in ct:
            ext = ".pdf"
        else:
            ext = ".csv"  # default guess

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext, dir=tempfile.gettempdir())
    for chunk in resp.iter_content(chunk_size=8192):
        tmp.write(chunk)
    tmp.close()

    try:
        report = analyze_dataset(tmp.name)
        report["original_url"] = url
        report["original_filename"] = os.path.basename(parsed.path) or "download" + ext
        _pending_analyses[report["analysis_id"]] = tmp.name
        return jsonify(report)
    except Exception as e:
        os.unlink(tmp.name)
        return jsonify({"error": str(e)}), 500


@api_bp.route("/datasets/search", methods=["POST"])
def search_databases():
    """Use Claude API to search the web for HSP databases."""
    data = request.get_json(force=True)
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "No search query provided"}), 400

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not set. Set it in the environment to enable search."}), 503

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        system_prompt = """You are helping find Hansen Solubility Parameter (HSP) databases and datasets on the web.

Search for datasets matching the user's query. For each result, provide structured JSON:

Return a JSON array of results, each with these fields:
- "name": Database/dataset name
- "url": Direct URL to the data or its landing page
- "description": 1-2 sentence description
- "estimated_materials": Approximate number of materials/compounds (integer or null if unknown)
- "material_types": Array of types like ["solvents", "polymers", "pigments"]
- "has_cas": true/false/null — whether CAS numbers are included
- "has_smiles": true/false/null — whether SMILES are included
- "hsp_parameters": Array like ["delta_d", "delta_p", "delta_h"] (what HSP data is present)
- "download_format": File format available like "CSV", "Excel", "JSON", "PDF", "HTML table"
- "quality": "high" / "medium" / "low" — your assessment of data quality
- "relevance": "high" / "medium" / "low"

Return ONLY valid JSON (an array). No markdown, no explanation."""

        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Search for: {query}"}],
        )

        result_text = response.content[0].text.strip()
        # Try to parse JSON from the response
        if result_text.startswith("```"):
            # Strip markdown code fences
            result_text = result_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        results = json.loads(result_text)
        return jsonify({"results": results, "query": query})

    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse search results", "raw": result_text}), 500
    except Exception as e:
        return jsonify({"error": f"Search failed: {e}"}), 500


@api_bp.route("/datasets/import", methods=["POST"])
def import_dataset():
    """Import an analyzed dataset."""
    data = request.get_json(force=True)
    analysis_id = data.get("analysis_id", "")
    dataset_id = data.get("dataset_id", "").strip()
    if not dataset_id:
        return jsonify({"error": "dataset_id is required"}), 400

    # Validate dataset_id format
    import re
    if not re.match(r"^[a-z0-9_]+$", dataset_id):
        return jsonify({"error": "dataset_id must be lowercase alphanumeric with underscores"}), 400

    # Get the temp file from pending analyses
    filepath = _pending_analyses.get(analysis_id)
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": f"Analysis {analysis_id} not found or expired. Re-upload the file."}), 404

    column_mapping = data.get("column_mapping")
    metadata = {
        "name": data.get("name", dataset_id),
        "source_url": data.get("source_url", ""),
        "description": data.get("description", ""),
        "quality_notes": data.get("quality_notes", ""),
    }
    confidence_tier = data.get("confidence_tier", 0.30)

    try:
        entry = normalize_and_write(
            filepath=filepath,
            dataset_id=dataset_id,
            column_mapping=column_mapping,
            metadata=metadata,
            confidence_tier=confidence_tier,
        )
        # Clean up temp file
        _pending_analyses.pop(analysis_id, None)
        try:
            os.unlink(filepath)
        except OSError:
            pass

        return jsonify({"success": True, "dataset": entry})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/datasets", methods=["GET"])
def list_datasets():
    """List all datasets from the manifest."""
    manifest = load_manifest()
    return jsonify(manifest)


@api_bp.route("/datasets/<dataset_id>", methods=["PATCH"])
def update_dataset(dataset_id):
    """Update dataset metadata (toggle active, edit name, etc.)."""
    manifest = load_manifest()
    if dataset_id not in manifest["datasets"]:
        return jsonify({"error": "Dataset not found"}), 404

    data = request.get_json(force=True)
    ds = manifest["datasets"][dataset_id]

    # Updatable fields
    for field in ("active", "name", "description", "confidence_tier", "quality_notes"):
        if field in data:
            ds[field] = data[field]

    save_manifest(manifest)
    return jsonify({"success": True, "dataset": ds})


@api_bp.route("/datasets/<dataset_id>", methods=["DELETE"])
def delete_dataset(dataset_id):
    """Remove a dataset."""
    if remove_dataset(dataset_id):
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Dataset not found"}), 404


@api_bp.route("/build", methods=["POST"])
def trigger_build():
    """Rebuild unified database and regenerate HTML."""
    try:
        # Run build_unified.py
        result_build = subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, "build_unified.py")],
            capture_output=True, text=True, timeout=120, cwd=BASE_DIR,
        )

        # Run generate_html.py
        result_html = subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, "generate_html.py")],
            capture_output=True, text=True, timeout=120, cwd=BASE_DIR,
        )

        return jsonify({
            "success": result_build.returncode == 0 and result_html.returncode == 0,
            "build_output": result_build.stdout + result_build.stderr,
            "html_output": result_html.stdout + result_html.stderr,
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Build timed out"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500
