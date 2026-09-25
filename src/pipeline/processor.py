"""
AccessiScan Data Pipeline
Processes UI test results through persona matching, compliance checking, and gap analysis.
"""

import pandas as pd
from dataclasses import dataclass, field
from typing import Any

from src.personas.profiles import PERSONAS, get_persona

# Maps common accessibility issue "rule" identifiers (as produced by tools like
# axe-core / Lighthouse) to WCAG 2.2 success criteria and Section 508 clauses.
# This is intentionally a small, extensible starter set covering the most
# frequently-flagged issue types.
_WCAG_RULE_MAP = {
    "image-alt": "1.1.1",
    "color-contrast": "1.4.3",
    "label": "1.3.1",
    "link-name": "2.4.4",
    "button-name": "4.1.2",
    "aria-required-attr": "4.1.2",
    "keyboard-trap": "2.1.2",
    "focus-order": "2.4.3",
    "heading-order": "1.3.1",
    "target-size": "2.5.8",
    "html-has-lang": "3.1.1",
    "document-title": "2.4.2",
}

_SECTION_508_RULE_MAP = {
    "image-alt": "502.3.1",
    "color-contrast": "502.3.1",
    "label": "502.3.1",
    "link-name": "502.3.1",
    "button-name": "502.3.1",
    "aria-required-attr": "502.3.1",
    "keyboard-trap": "502.2.1",
    "focus-order": "502.2.1",
    # E205.4 requires web content to conform to WCAG Level A/AA.
    "html-has-lang": "E205.4",
    "document-title": "E205.4",
}

_SEVERITY_RANK = {"minor": 1, "moderate": 2, "serious": 3, "critical": 4}

# Plain-language fix guidance for each supported rule, returned alongside
# every violation so a front end can show developers what to change.
_REMEDIATION = {
    "image-alt": "Add a descriptive alt attribute to meaningful images; use alt=\"\" for decorative ones.",
    "color-contrast": "Raise the text/background contrast ratio to at least 4.5:1 (3:1 for large text).",
    "label": "Associate every form control with a visible <label> or an aria-label.",
    "link-name": "Give each link text that describes its destination, not just \"click here\".",
    "button-name": "Give each button an accessible name via its text content or aria-label.",
    "aria-required-attr": "Add the ARIA attributes required by the element's role.",
    "keyboard-trap": "Make sure keyboard focus can move into and back out of the component (e.g. Esc closes modals).",
    "focus-order": "Order focusable elements to follow the visual reading order; avoid positive tabindex values.",
    "heading-order": "Use heading levels in sequence (h1 → h2 → h3) without skipping levels.",
    "target-size": "Make interactive targets at least 24×24 CSS pixels or add spacing around them.",
    "html-has-lang": "Add a lang attribute to the <html> element (e.g. lang=\"en\") so screen readers use the right pronunciation.",
    "document-title": "Give the page a unique, descriptive <title> so users can identify it in tabs and history.",
}


@dataclass
class ScanResult:
    url: str
    persona: str
    raw_results: dict[str, Any]
    wcag_violations: list = field(default_factory=list)
    section_508_violations: list = field(default_factory=list)
    gap_scores: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)


def run_pipeline(url: str, persona: str, test_results: dict) -> ScanResult:
    """
    Main pipeline entry point.
    Ingests raw test results and returns a structured ScanResult.

    Steps:
      1. Normalize raw test input into a standard schema
      2. Match to synthetic user persona profile
      3. Run compliance checks (WCAG 2.2, Section 508)
      4. Score UX gaps by severity and user segment
      5. Summarize violation counts by severity
    """
    result = ScanResult(url=url, persona=persona, raw_results=test_results)

    normalized = _normalize(test_results)
    result.wcag_violations = _check_wcag(normalized)
    result.section_508_violations = _check_section_508(normalized)
    result.gap_scores = _score_gaps(normalized, persona)
    result.summary = _summarize(result.wcag_violations)

    return result


def _normalize(raw: dict) -> pd.DataFrame:
    """Convert raw test output dict into a normalized DataFrame.

    Expected shape of each issue (fields are optional except "rule"):
        {"rule": "image-alt", "severity": "serious", "selector": "img.hero", "message": "..."}
    """
    issues = raw.get("issues", [])
    df = pd.DataFrame(issues)
    if df.empty:
        return pd.DataFrame(columns=["rule", "severity", "selector", "message"])

    for col, default in (("rule", "unknown"), ("severity", "moderate"), ("selector", None), ("message", None)):
        if col not in df.columns:
            df[col] = default
    df["severity"] = df["severity"].fillna("moderate").str.lower()
    df["rule"] = df["rule"].fillna("unknown")
    # Replace pandas NaN with None so reports serialize to valid JSON (null, not NaN).
    return df.astype(object).where(df.notna(), None)


def _affected_personas(criterion: str) -> list:
    """Return the personas whose key WCAG criteria include this criterion."""
    return [name for name, p in PERSONAS.items() if criterion in p["wcag_criteria_weight"]]


def _by_severity(violations: list) -> list:
    """Sort violations most-severe first (stable, so input order breaks ties)."""
    return sorted(violations, key=lambda v: _SEVERITY_RANK.get(v["severity"], 2), reverse=True)


def _check_wcag(df: pd.DataFrame) -> list:
    """Map issues to WCAG 2.2 success criteria, ranked most-severe first."""
    violations = []
    for _, row in df.iterrows():
        criterion = _WCAG_RULE_MAP.get(row["rule"])
        if criterion:
            violations.append({
                "rule": row["rule"],
                "criterion": criterion,
                "severity": row["severity"],
                "selector": row.get("selector"),
                "message": row.get("message"),
                "affected_personas": _affected_personas(criterion),
                "remediation": _REMEDIATION[row["rule"]],
            })
    return _by_severity(violations)


def _check_section_508(df: pd.DataFrame) -> list:
    """Map issues to Section 508 technical standards, ranked most-severe first."""
    violations = []
    for _, row in df.iterrows():
        clause = _SECTION_508_RULE_MAP.get(row["rule"])
        if clause:
            violations.append({
                "rule": row["rule"],
                "clause": clause,
                "severity": row["severity"],
                "selector": row.get("selector"),
                "remediation": _REMEDIATION[row["rule"]],
            })
    return _by_severity(violations)


def _score_gaps(df: pd.DataFrame, persona: str) -> dict:
    """
    Score UX gaps by severity for the given persona.
    Returns a dict of {gap_category: severity_score}, weighted by the
    persona's WCAG criteria of interest and severity multiplier.
    """
    if df.empty:
        return {}

    profile = get_persona(persona)
    weighted_criteria = set(profile["wcag_criteria_weight"])
    multiplier = profile["severity_multiplier"]

    scores: dict[str, float] = {}
    for _, row in df.iterrows():
        criterion = _WCAG_RULE_MAP.get(row["rule"])
        base_severity = _SEVERITY_RANK.get(row["severity"], 2)
        weight = multiplier if criterion in weighted_criteria else 1.0
        score = round(base_severity * weight, 2)

        category = row["rule"]
        scores[category] = round(scores.get(category, 0) + score, 2)

    return scores


def _summarize(wcag_violations: list) -> dict:
    """Count WCAG violations by severity and report the most severe level found."""
    counts = {level: 0 for level in _SEVERITY_RANK}
    for v in wcag_violations:
        counts[v["severity"]] = counts.get(v["severity"], 0) + 1
    worst = wcag_violations[0]["severity"] if wcag_violations else None
    return {"total": len(wcag_violations), "by_severity": counts, "highest_severity": worst}
