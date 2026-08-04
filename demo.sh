#!/usr/bin/env bash
# Quick demo: starts the API, submits a scan with sample accessibility issues,
# and prints the resulting compliance report.
set -e

echo "Starting AccessiScan API..."
python -m src.api.app > /tmp/accessiscan.log 2>&1 &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null" EXIT

sleep 2

echo
echo "--- Health check ---"
curl -s http://127.0.0.1:5000/health
echo
echo

echo "--- Submitting a scan (screen_reader persona) ---"
SCAN_RESP=$(curl -s -X POST http://127.0.0.1:5000/api/v1/scan \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "persona": "screen_reader",
    "test_results": {
      "issues": [
        {"rule": "image-alt", "severity": "critical", "selector": "img.hero"},
        {"rule": "color-contrast", "severity": "moderate", "selector": ".btn-primary"},
        {"rule": "label", "severity": "serious", "selector": "input#email"},
        {"rule": "keyboard-trap", "severity": "critical", "selector": "div.modal"}
      ]
    }
  }')
echo "$SCAN_RESP"
SCAN_ID=$(echo "$SCAN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['scan_id'])")

echo
echo "--- Fetching the compliance report ---"
curl -s http://127.0.0.1:5000/api/v1/report/$SCAN_ID | python3 -m json.tool
echo
echo "Demo complete."
