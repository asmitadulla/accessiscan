# AccessiScan

**AI Accessibility & Usability Testing Platform**

AccessiScan scans a web page (or takes pasted axe-core / Lighthouse results) and produces a report that shows **which users each issue affects, how severe it is, and how to fix it**. Issues are mapped to **WCAG 2.2** and **Section 508**, weighted against **5 synthetic user personas**, and ranked most-severe first — through a Flask REST API and an accessible web UI.

---

## Features

- **URL scanning** — fetches a page and runs 7 static HTML checks: image alt text, form labels, link names, button names, heading order, page language, and page title. Blocks private/local addresses and detects bot-check pages
- **REST API** (Flask) — 4 endpoints to list personas, submit a scan, fetch a report, and check health
- **Compliance mapping** — 12 rule types mapped to WCAG 2.2 success criteria and Section 508
- **Persona engine** — 5 synthetic users spanning visual, motor, and cognitive needs, each with key WCAG criteria and a severity multiplier used for gap scoring
- **Actionable reports** — every violation includes the affected personas and plain-language remediation guidance, ranked by severity with a per-severity summary
- **Accessible web UI** — vanilla HTML/CSS/JavaScript front end built to WCAG 2.2 AA: skip link, labeled form controls, visible focus styles, `aria-live` status updates, focus management after a scan, severity shown with text + shape (not color alone), 44px touch targets, light/dark themes, and reduced-motion support
- **Tests** — 32 pytest tests covering the scanner, personas, pipeline, and API (all offline, no network needed)

---

## Tech stack

| Layer | Technology |
|---|---|
| API | Python 3.11+, Flask |
| URL scanning | requests, Beautiful Soup |
| Data pipeline | pandas |
| Front end | HTML, CSS, JavaScript (no framework) |
| Testing | pytest |

---

## Getting started

```bash
git clone https://github.com/asmitadulla/accessiscan.git
cd accessiscan

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start the server (run from the repo root)
python -m src.api.app
```

Open **http://localhost:5000**, enter a URL (for example `news.ycombinator.com`), pick a persona, and click **Run scan**.

> On macOS, AirPlay Receiver can occupy port 5000. If so, run `flask --app src.api.app run --port 5055` and open http://localhost:5055 instead.

Run the tests:

```bash
pytest
```

Or run `./demo.sh` for a command-line walkthrough of the API.

---

## API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health check |
| `GET` | `/api/v1/personas` | List personas with descriptions and key WCAG criteria |
| `POST` | `/api/v1/scan` | Scan a URL for a persona (or analyze pasted `test_results`); returns a `scan_id` |
| `GET` | `/api/v1/report/<scan_id>` | Fetch the full compliance report |

**Example scan request** — scan a live page:

```json
{ "url": "https://news.ycombinator.com", "persona": "screen_reader" }
```

…or analyze results from axe-core / Lighthouse, which cover checks that need a real browser (color contrast, keyboard traps):

```json
{
  "url": "https://example.com",
  "persona": "screen_reader",
  "test_results": {
    "issues": [
      { "rule": "image-alt", "severity": "critical", "selector": "img.hero" },
      { "rule": "color-contrast", "severity": "serious", "selector": ".btn-primary" }
    ]
  }
}
```

**Example violation in the report**

```json
{
  "rule": "color-contrast",
  "criterion": "1.4.3",
  "severity": "serious",
  "selector": ".btn-primary",
  "affected_personas": ["low_vision", "color_blind"],
  "remediation": "Raise the text/background contrast ratio to at least 4.5:1 (3:1 for large text)."
}
```

Each report also includes `section_508_violations`, persona-weighted `gap_scores`, and a `summary` with counts by severity.

---

## Personas

| Persona | Needs | Key WCAG criteria |
|---|---|---|
| `low_vision` | Screen magnification, high contrast | 1.4.3, 1.4.4, 1.4.10, 1.4.11 |
| `screen_reader` | Navigates entirely by screen reader | 1.1.1, 1.3.1, 2.1.1, 3.1.1, 4.1.2 |
| `motor_impairment` | Keyboard-only navigation | 2.1.1, 2.1.2, 2.4.3, 2.4.7 |
| `cognitive` | Simplified, predictable interfaces | 1.3.5, 2.4.2, 2.4.6, 3.1.5, 3.3.2 |
| `color_blind` | Deuteranopia / protanopia | 1.4.1, 1.4.3 |

---

## How it works

```
URL ──► fetch + static HTML checks ─┐
                                    ├──► POST /api/v1/scan  (Flask)
Pasted axe-core / Lighthouse JSON ──┘            │
                                                 ▼
Pipeline (pandas)
  1. Normalize issues into a standard schema
  2. Map rules → WCAG 2.2 criteria and Section 508 clauses
  3. Attach affected personas + remediation guidance
  4. Score gaps, weighting the selected persona's key criteria
  5. Rank by severity and summarize
        │
        ▼
GET /api/v1/report/<id>  →  JSON report  →  web UI
```

---

## Project structure

```
accessiscan/
├── src/
│   ├── api/app.py              # Flask app: REST endpoints + serves the web UI
│   ├── scanner/html_checks.py  # Fetch a URL and run static HTML accessibility checks
│   ├── pipeline/processor.py   # Normalize, map to WCAG/508, score, rank, summarize
│   ├── personas/profiles.py    # Synthetic persona definitions
│   └── web/                    # Accessible front end (HTML, CSS, JS)
├── tests/                      # pytest suite (scanner, pipeline, personas, API)
├── demo.sh                     # CLI demo of the API
└── requirements.txt
```

---

## Roadmap

- EN 301 549 mapping
- Headless-browser scanning (Playwright + axe-core) to check JavaScript-rendered content, color contrast, and keyboard traps
- Persistent report storage (reports are currently in memory and reset on restart)
- Exportable PDF reports

---

## Author

Asmita Dulla · [linkedin.com/in/asmita-dulla](https://linkedin.com/in/asmita-dulla) · [github.com/asmitadulla](https://github.com/asmitadulla)
