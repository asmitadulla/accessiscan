"""
AccessiScan Data Pipeline
Processes UI test results through persona matching, compliance checking, and gap analysis.
"""

import pandas as pd
from dataclasses import dataclass, field
from typing import Any

from src.personas.profiles import get_persona

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
}

_SEVERITY_RANK = {"minor": 1, "moderate": 2, "serious": 3, "critical": 4}


@dataclass
class ScanResult:
    url: str
    persona: str
    raw_results: dict[str, Any]
    wcag_violations: list = field(default_factory=list)
    section_508_violations: list = field(default_factory=list)
    gap_scores: dict = field(default_factory=dict)


def run_pipeline(url: str, persona: str, test_results: dict) -> ScanResult:
    """
    Main pipeline entry point.
    Ingests raw test results and returns a structured ScanResult.

    Steps:
      1. Normalize raw test input into a standard schema
      2. Match to synthetic user persona profile
      3. Run compliance checks (WCAG 2.2, Section 508)
      4. Score UX gaps by severity and user segment
    """
    result = ScanResult(url=url, persona=persona, raw_results=test_results)

    normalized = _normalize(test_results)
    result.wcag_violations = _check_wcag(normalized)
    result.section_508_violations = _check_section_508(normalized)
    result.gap_scores = _score_gaps(normalized, persona)

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

    if "rule" not in df.columns:
        df["rule"] = "unknown"
    if "severity" not in df.columns:
        df["severity"] = "moderate"
    df["severity"] = df["severity"].fillna("moderate").str.lower()
    df["rule"] = df["rule"].fillna("unknown")
    return df


def _check_wcag(df: pd.DataFrame) -> list:
    """Map issues to WCAG 2.2 success criteria."""
    violations = []
    for _, row in df.iterrows():
        criterion = _WCAG_RULE_MAP.get(row["rule"])
        if criterion:
            violations.append({
                "rule": row["rule"],
                "criterion": criterion,
                "severity": row["severity"],
                "selector": row.get("selector"),
            })
    return violations


def _check_section_508(df: pd.DataFrame) -> list:
    """Map issues to Section 508 technical standards."""
    violations = []
    for _, row in df.iterrows():
        clause = _SECTION_508_RULE_MAP.get(row["rule"])
        if clause:
            violations.append({
                "rule": row["rule"],
                "clause": clause,
                "severity": row["severity"],
                "selector": row.get("selector"),
            })
    return violations


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
