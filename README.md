# AccessiScan

**AI Accessibility & Usability Testing Platform**

AccessiScan is a Python and JavaScript platform that evaluates web accessibility using synthetic user personas. It ingests UI test results via REST API, processes them through a structured data pipeline, and outputs compliance findings against WCAG 2.2, Section 508, and EN 301 549 standards.

---

## Project status

**MVP complete.** The REST API, data pipeline, and persona engine are fully wired end-to-end: submit a scan, get back real WCAG 2.2 / Section 508 findings and persona-weighted gap scores. Report generation (PDF) and the dashboard visualization are still on the roadmap.

---

## Features

- [x] REST API layer to ingest UI test results and persona input data
- [x] Synthetic user persona engine — 5 profiles spanning visual, motor, and cognitive accessibility needs
- [x] Compliance report generation mapped to WCAG 2.2 and Section 508
- [ ] EN 301 549 mapping
- [ ] Dashboard visualization of UX gaps across demographic and cognitive user groups
- [ ] Persistent report storage (currently in-memory, resets on server restart)

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend / pipeline | Python 3.11+ |
| API | Flask / REST |
| Data processing | Pandas, NumPy |
| Visualization | Matplotlib, Seaborn |
| Frontend | JavaScript, HTML, CSS |
| Testing | pytest |

---

## Project structure

```
accessiscan/
├── src/
│   ├── api/            # REST API endpoints for ingesting test results
│   ├── pipeline/       # Data pipeline: ingest → process → output
│   ├── personas/       # Synthetic user persona definitions and engine
│   └── reports/        # Report generation logic (WCAG, Section 508, EN 301 549)
├── tests/              # Unit and integration tests
├── docs/               # Architecture diagrams and API documentation
├── requirements.txt
└── README.md
```

---

## Getting started

```bash
# Clone the repo
git clone https://github.com/asmitadulla/accessiscan.git
cd accessiscan

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the API server (must be run as a module from the repo root)
python -m src.api.app
```

---

## Architecture overview

```
UI Test Input
     │
     ▼
REST API (Flask)
     │
     ▼
Data Pipeline
  ├── Persona Matcher    → maps inputs to synthetic user profiles
  ├── Compliance Checker → validates against WCAG 2.2 / Section 508
  └── Gap Analyzer       → scores UX gaps by severity and user segment
     │
     ▼
Structured Output Schema
     │
     ▼
Dashboard (Matplotlib) + Report (JSON/PDF)
```

---

## Compliance standards

- **WCAG 2.2** — Web Content Accessibility Guidelines
- **Section 508** — U.S. federal accessibility requirements
- **EN 301 549** — European accessibility standard for ICT products

---

## Contributing

This project is part of an ongoing portfolio. Contributions and feedback welcome — open an issue or submit a pull request.

---

## Author

Asmita Dulla · [linkedin.com/in/asmita-dulla](https://linkedin.com/in/asmita-dulla) · [github.com/asmitadulla](https://github.com/asmitadulla)
