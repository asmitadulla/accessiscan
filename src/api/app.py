"""
AccessiScan REST API
Ingests UI test results and routes them through the accessibility pipeline.
"""

import uuid
from dataclasses import asdict
from pathlib import Path

from flask import Flask, request, jsonify

from src.pipeline.processor import run_pipeline
from src.scanner.html_checks import ScanError, scan_url
from src.personas.profiles import PERSONAS, list_personas

# Serve the web UI from src/web at the site root.
app = Flask(__name__, static_folder=str(Path(__file__).resolve().parent.parent / "web"), static_url_path="")

# In-memory report store. Fine for an MVP / single-process dev server;
# swap for a real datastore (Redis, Postgres, etc.) before production use.
_REPORTS: dict[str, dict] = {}


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "0.1.0"})


@app.route("/", methods=["GET"])
def index():
    return app.send_static_file("index.html")


@app.route("/api/v1/personas", methods=["GET"])
def personas():
    """Lists the synthetic personas so clients can offer them as scan options."""
    return jsonify([
        {"id": name, "description": p["description"], "key_criteria": p["wcag_criteria_weight"]}
        for name, p in PERSONAS.items()
    ])


@app.route("/api/v1/scan", methods=["POST"])
def scan():
    """
    Runs a URL (or pasted UI test results) through the accessibility pipeline.

    Expected JSON body:
    {
        "url": "https://example.com",
        "persona": "low_vision",          # see personas/ for supported types
        "test_results": { ... }            # optional raw UI test output; if omitted,
                                           # the page at `url` is fetched and scanned
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400

    required_fields = ["url", "persona"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    if data["persona"] not in list_personas():
        return jsonify({
            "error": f"Unknown persona '{data['persona']}'",
            "available_personas": list_personas(),
        }), 400

    test_results = data.get("test_results")
    source = "pasted"
    if test_results is None:
        try:
            test_results = scan_url(data["url"])
        except ScanError as e:
            return jsonify({"error": str(e)}), 422
        source = "url_scan"

    scan_result = run_pipeline(
        url=data["url"],
        persona=data["persona"],
        test_results=test_results,
    )

    scan_id = str(uuid.uuid4())
    report = asdict(scan_result)
    report["scan_id"] = scan_id
    report["status"] = "complete"
    report["source"] = source
    _REPORTS[scan_id] = report

    return jsonify({
        "scan_id": scan_id,
        "url": data["url"],
        "persona": data["persona"],
        "status": "complete",
    }), 202


@app.route("/api/v1/report/<scan_id>", methods=["GET"])
def get_report(scan_id):
    """
    Returns the accessibility report for a completed scan.
    """
    report = _REPORTS.get(scan_id)
    if report is None:
        return jsonify({"error": "Unknown scan_id"}), 404
    return jsonify(report)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
