"""
Tests for the static HTML scanner. All run offline against HTML snippets.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.scanner.html_checks import ScanError, check_html, fetch_html
from src.api.app import app as flask_app


def rules(html):
    return [i["rule"] for i in check_html(html)]


GOOD_PAGE = """
<html lang="en"><head><title>Home</title></head><body>
  <h1>Welcome</h1><h2>Section</h2>
  <img src="a.png" alt="A chart">
  <img src="spacer.png" alt="">
  <label for="email">Email</label><input id="email" type="email">
  <label>Name <input type="text"></label>
  <input type="search" aria-label="Search">
  <input type="hidden" name="csrf">
  <a href="/about">About</a>
  <a href="/cart"><img src="cart.png" alt="Cart"></a>
  <button>Save</button>
  <button aria-label="Close"><svg></svg></button>
  <input type="submit">
</body></html>
"""


class TestCheckHtml:
    def test_accessible_page_has_no_issues(self):
        assert check_html(GOOD_PAGE) == []

    def test_missing_lang_and_title(self):
        assert set(rules("<html><head></head><body></body></html>")) == {"html-has-lang", "document-title"}

    def test_image_without_alt(self):
        issues = check_html('<html lang="en"><title>t</title><img class="hero big" src="x.png"></html>')
        assert issues == [{
            "rule": "image-alt",
            "severity": "critical",
            "selector": "img.hero.big",
            "message": "Image has no alt attribute.",
        }]

    def test_decorative_and_hidden_images_are_ignored(self):
        html = '<html lang="en"><title>t</title><img role="presentation"><img aria-hidden="true"></html>'
        assert rules(html) == []

    def test_unlabeled_form_fields(self):
        html = '<html lang="en"><title>t</title><input id="q" type="text"><select></select><textarea></textarea></html>'
        assert rules(html) == ["label", "label", "label"]

    def test_empty_link_and_icon_button(self):
        html = '<html lang="en"><title>t</title><a href="/x"><i class="icon"></i></a><button><svg></svg></button></html>'
        assert rules(html) == ["link-name", "button-name"]

    def test_icon_link_named_by_descendant_title(self):
        html = '<html lang="en"><title>t</title><a href="/vote"><div class="arrow" title="upvote"></div></a></html>'
        assert rules(html) == []

    def test_input_button_without_value(self):
        assert rules('<html lang="en"><title>t</title><input type="button"></html>') == ["button-name"]

    def test_skipped_heading_level(self):
        issues = check_html('<html lang="en"><title>t</title><h1>a</h1><h2>b</h2><h4 id="deep">c</h4><h2>d</h2></html>')
        assert [(i["rule"], i["selector"]) for i in issues] == [("heading-order", "h4#deep")]


class TestFetchHtml:
    def test_rejects_non_http_urls(self):
        with pytest.raises(ScanError, match="http"):
            fetch_html("ftp://example.com")

    def test_rejects_localhost(self):
        with pytest.raises(ScanError, match="private"):
            fetch_html("http://localhost:5000")

    def test_empty_response_explains_bot_blocking(self):
        resp = MagicMock(status_code=202, url="https://www.amazon.com/", headers={"Content-Type": "text/html"}, encoding="utf-8")
        resp.raw.read.return_value = b""
        resp.__enter__.return_value = resp
        with patch("src.scanner.html_checks._reject_private_host"), \
             patch("src.scanner.html_checks.requests.get", return_value=resp):
            with pytest.raises(ScanError, match="bot check"):
                fetch_html("https://www.amazon.com")

    def test_captcha_page_is_reported_as_blocked(self):
        page = b"<html><body>JavaScript is disabled. Verify that you're not a robot.</body></html>"
        resp = MagicMock(status_code=200, url="https://www.amazon.com/", headers={"Content-Type": "text/html"}, encoding="utf-8")
        resp.raw.read.return_value = page
        resp.__enter__.return_value = resp
        with patch("src.scanner.html_checks._reject_private_host"), \
             patch("src.scanner.html_checks.requests.get", return_value=resp):
            with pytest.raises(ScanError, match="bot check"):
                fetch_html("https://www.amazon.com")

    def test_defaults_to_utf8_without_declared_charset(self):
        resp = MagicMock(status_code=200, url="https://example.com/", headers={"Content-Type": "text/html"}, encoding="ISO-8859-1")
        resp.raw.read.return_value = "<html><title>Café</title><body>Plenty of real content here.</body></html>".encode()
        resp.__enter__.return_value = resp
        with patch("src.scanner.html_checks._reject_private_host"), \
             patch("src.scanner.html_checks.requests.get", return_value=resp):
            assert "Café" in fetch_html("https://example.com")


class TestUrlScanApi:
    @pytest.fixture
    def client(self):
        flask_app.config["TESTING"] = True
        return flask_app.test_client()

    def test_scan_without_test_results_scans_the_url(self, client):
        page_issues = {"issues": check_html('<html><title>t</title><img src="x.png"></html>')}
        with patch("src.api.app.scan_url", return_value=page_issues):
            resp = client.post("/api/v1/scan", json={"url": "https://example.com", "persona": "screen_reader"})
        assert resp.status_code == 202

        report = client.get(f"/api/v1/report/{resp.get_json()['scan_id']}").get_json()
        assert report["source"] == "url_scan"
        assert {v["rule"] for v in report["wcag_violations"]} == {"image-alt", "html-has-lang"}
        assert all("remediation" in v for v in report["wcag_violations"])

    def test_unreachable_site_returns_readable_error(self, client):
        with patch("src.api.app.scan_url", side_effect=ScanError("Couldn't reach nope.invalid.")):
            resp = client.post("/api/v1/scan", json={"url": "https://nope.invalid", "persona": "cognitive"})
        assert resp.status_code == 422
        assert "Couldn't reach" in resp.get_json()["error"]
