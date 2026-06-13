"""
Tests for AccessiScan pipeline and persona modules.
"""

import pytest
from src.personas.profiles import get_persona, list_personas
from src.pipeline.processor import run_pipeline, ScanResult


class TestPersonas:
    def test_get_known_persona(self):
        p = get_persona("low_vision")
        assert "description" in p
        assert "severity_multiplier" in p

    def test_get_unknown_persona_raises(self):
        with pytest.raises(ValueError):
            get_persona("nonexistent_persona")

    def test_list_personas_returns_all(self):
        personas = list_personas()
        assert len(personas) >= 5
        assert "screen_reader" in personas


class TestPipeline:
    def test_run_pipeline_returns_scan_result(self):
        result = run_pipeline(
            url="https://example.com",
            persona="low_vision",
            test_results={"issues": []}
        )
        assert isinstance(result, ScanResult)
        assert result.url == "https://example.com"
        assert result.persona == "low_vision"

    def test_run_pipeline_empty_issues(self):
        result = run_pipeline("https://example.com", "cognitive", {"issues": []})
        assert result.wcag_violations == []
        assert result.section_508_violations == []
