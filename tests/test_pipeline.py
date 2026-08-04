"""
Tests for AccessiScan pipeline and persona modules.
"""

import pytest
from src.personas.profiles import get_persona, list_personas
from src.pipeline.processor import run_pipeline, ScanResult
from src.api.app import app as flask_app


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

    def test_run_pipeline_maps_known_issues(self):
        result = run_pipeline(
            url="https://example.com",
            persona="screen_reader",
            test_results={"issues": [
                {"rule": "image-alt", "severity": "critical", "selector": "img.hero"},
            ]},
        )
        assert result.wcag_violations == [
            {"rule": "image-alt", "criterion": "1.1.1", "severity": "critical", "selector": "img.hero"}
        ]
        assert result.gap_scores["image-alt"] > 0


class TestAPI:
    @pytest.fixture
    def client(self):
        flask_app.config["TESTING"] = True
        return flask_app.test_client()

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_scan_and_report_round_trip(self, client):
        scan_resp = client.post("/api/v1/scan", json={
            "url": "https://example.com",
            "persona": "low_vision",
            "test_results": {"issues": [
                {"rule": "color-contrast", "severity": "serious", "selector": "p"}
            ]},
        })
        assert scan_resp.status_code == 202
        scan_id = scan_resp.get_json()["scan_id"]

        report_resp = client.get(f"/api/v1/report/{scan_id}")
        assert report_resp.status_code == 200
        report = report_resp.get_json()
        assert report["status"] == "complete"
        assert len(report["wcag_violations"]) == 1

    def test_scan_rejects_unknown_persona(self, client):
        resp = client.post("/api/v1/scan", json={
            "url": "https://example.com",
            "persona": "not_a_persona",
            "test_results": {"issues": []},
        })
        assert resp.status_code == 400

    def test_report_unknown_id_404s(self, client):
        resp = client.get("/api/v1/report/does-not-exist")
        assert resp.status_code == 404
