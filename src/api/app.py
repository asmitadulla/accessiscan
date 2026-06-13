"""
AccessiScan REST API
Ingests UI test results and routes them through the accessibility pipeline.
"""

from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "0.1.0"})


@app.route("/api/v1/scan", methods=["POST"])
def scan():
    """
    Accepts a UI test result payload and runs it through the accessibility pipeline.

    Expected JSON body:
    {
        "url": "https://example.com",
        "persona": "low_vision",          # see personas/ for supported types
        "test_results": { ... }            # raw UI test output
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400

    required_fields = ["url", "persona", "test_results"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {missing}"}), 400

    # TODO: wire into pipeline/processor.py
    result = {
        "url": data["url"],
        "persona": data["persona"],
        "status": "queued",
        "message": "Scan received. Processing pipeline not yet connected."
    }
    return jsonify(result), 202


@app.route("/api/v1/report/<scan_id>", methods=["GET"])
def get_report(scan_id):
    """
    Returns the accessibility report for a completed scan.
    """
    # TODO: fetch from report store
    return jsonify({
        "scan_id": scan_id,
        "status": "pending",
        "message": "Report generation in progress."
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
