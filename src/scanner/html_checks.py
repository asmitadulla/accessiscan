"""
AccessiScan URL Scanner
Fetches a page and runs static HTML accessibility checks, producing issues in the
same shape the pipeline accepts from axe-core / Lighthouse:

    {"rule": "image-alt", "severity": "critical", "selector": "img.hero", "message": "..."}

These checks read the HTML the server returns. They can't see content that
JavaScript renders later, and rules that need a real browser (color contrast,
keyboard traps, focus order) still require pasted results from axe-core or Lighthouse.
"""

import ipaddress
import socket
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag

# Severities follow axe-core's defaults for the equivalent rules.
_SEVERITY = {
    "image-alt": "critical",
    "label": "critical",
    "button-name": "critical",
    "link-name": "serious",
    "html-has-lang": "serious",
    "document-title": "serious",
    "heading-order": "moderate",
}

_MAX_BYTES = 5 * 1024 * 1024
_TIMEOUT_SECONDS = 10
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36 AccessiScan/0.2"
)

# Phrases that mark a bot-check / CAPTCHA interstitial instead of the real page.
_BOT_WALL_PHRASES = (
    "not a robot", "captcha", "verify you are human", "verify that you're not a robot",
    "enable javascript and then reload", "checking your browser",
)

# Input types that don't need a <label> (they're labeled by their value or aren't visible).
_UNLABELED_INPUT_TYPES = {"hidden", "submit", "reset", "button", "image"}


class ScanError(Exception):
    """Raised when a page can't be fetched or scanned. The message is safe to show users."""


def scan_url(url: str) -> dict:
    """Fetch a URL and return {"issues": [...]} ready for run_pipeline."""
    html = fetch_html(url)
    return {"issues": check_html(html)}


def fetch_html(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ScanError("Enter a full URL starting with http:// or https://.")
    _reject_private_host(parsed.hostname)

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": _USER_AGENT, "Accept": "text/html"},
            timeout=_TIMEOUT_SECONDS,
            stream=True,
        )
    except requests.RequestException:
        raise ScanError(f"Couldn't reach {parsed.hostname}. Check the URL and try again.")

    with resp:
        if resp.status_code >= 400:
            raise ScanError(f"{parsed.hostname} responded with HTTP {resp.status_code}.")
        # Redirects can land somewhere else, so re-check the final host.
        _reject_private_host(urlparse(resp.url).hostname or "")
        content_type = resp.headers.get("Content-Type", "text/html")
        if "html" not in content_type:
            raise ScanError("That URL isn't an HTML page.")
        body = resp.raw.read(_MAX_BYTES, decode_content=True)

    # requests assumes ISO-8859-1 when no charset is declared; UTF-8 is the web's default.
    encoding = resp.encoding if "charset" in content_type.lower() else "utf-8"
    html = body.decode(encoding or "utf-8", errors="replace")
    if not html.strip() or _is_bot_wall(html):
        raise ScanError(
            f"{parsed.hostname} blocked the scan with a bot check, so there's no real page to "
            "analyze. Some sites (like Amazon) block automated requests; try another site, "
            "or paste axe-core results under Advanced."
        )
    return html


def _is_bot_wall(html: str) -> bool:
    """True for short CAPTCHA / 'enable JavaScript' interstitials served to automated clients."""
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True).lower()
    return len(text) < 2000 and any(p in text for p in _BOT_WALL_PHRASES)


def _reject_private_host(hostname: str) -> None:
    """Block requests to localhost / private networks so the scanner can't be used to probe them."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ScanError(f"Couldn't find a site at {hostname}.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ScanError("Scanning local or private network addresses isn't allowed.")


def check_html(html: str) -> list:
    """Run every static check against an HTML document and return a list of issues."""
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    for check in (_check_lang, _check_title, _check_images, _check_labels,
                  _check_links, _check_buttons, _check_headings):
        issues.extend(check(soup))
    return issues


def _issue(rule: str, el: Tag | None, message: str) -> dict:
    return {
        "rule": rule,
        "severity": _SEVERITY[rule],
        "selector": _selector(el) if el is not None else "html",
        "message": message,
    }


def _selector(el: Tag) -> str:
    """A short, readable CSS-style selector for pointing developers at an element."""
    if el.get("id"):
        return f"{el.name}#{el['id']}"
    classes = el.get("class") or []
    return el.name + "".join(f".{c}" for c in classes[:2])


def _is_hidden(el: Tag) -> bool:
    return (
        el.get("aria-hidden") == "true"
        or el.has_attr("hidden")
        or "display:none" in (el.get("style") or "").replace(" ", "")
    )


def _accessible_name(el: Tag, soup: BeautifulSoup) -> str:
    """Approximate the accessible name: aria-label, aria-labelledby, text, image alt, or title."""
    if el.get("aria-label", "").strip():
        return el["aria-label"].strip()
    for ref in (el.get("aria-labelledby") or "").split():
        target = soup.find(id=ref)
        if target and target.get_text(strip=True):
            return target.get_text(strip=True)
    text = el.get_text(strip=True)
    if text:
        return text
    for img in el.find_all(["img", "svg"]):
        alt = img.get("alt") or img.get("aria-label") or ""
        if alt.strip():
            return alt.strip()
    # A title on the element or a descendant (e.g. an icon <div title="upvote">) also names it.
    for node in [el, *el.find_all(title=True)]:
        if (node.get("title") or "").strip():
            return node["title"].strip()
    return ""


def _check_lang(soup):
    html = soup.find("html")
    if html is None or not (html.get("lang") or "").strip():
        return [_issue("html-has-lang", html, "The <html> element has no lang attribute.")]
    return []


def _check_title(soup):
    title = soup.find("title")
    if title is None or not title.get_text(strip=True):
        return [_issue("document-title", None, "The page has no <title>.")]
    return []


def _check_images(soup):
    return [
        _issue("image-alt", img, "Image has no alt attribute.")
        for img in soup.find_all("img")
        if not img.has_attr("alt") and img.get("role") not in ("presentation", "none") and not _is_hidden(img)
    ]


def _check_labels(soup):
    labeled_ids = {lbl["for"] for lbl in soup.find_all("label") if lbl.get("for")}
    issues = []
    for field in soup.find_all(["input", "select", "textarea"]):
        if field.name == "input" and (field.get("type") or "text").lower() in _UNLABELED_INPUT_TYPES:
            continue
        if _is_hidden(field):
            continue
        has_label = (
            field.get("id") in labeled_ids
            or field.find_parent("label") is not None
            or (field.get("aria-label") or "").strip()
            or field.get("aria-labelledby")
            or (field.get("title") or "").strip()
        )
        if not has_label:
            issues.append(_issue("label", field, "Form field has no associated label."))
    return issues


def _check_links(soup):
    return [
        _issue("link-name", a, "Link has no text or accessible name.")
        for a in soup.find_all("a", href=True)
        if not _is_hidden(a) and not _accessible_name(a, soup)
    ]


def _check_buttons(soup):
    issues = []
    for btn in soup.find_all(["button", "input"]):
        if btn.name == "input":
            if (btn.get("type") or "").lower() not in ("button", "submit", "reset"):
                continue
            # Submit/reset inputs get a default name from the browser.
            if btn.get("value", "").strip() or btn.get("type").lower() in ("submit", "reset"):
                continue
        if _is_hidden(btn):
            continue
        if not _accessible_name(btn, soup):
            issues.append(_issue("button-name", btn, "Button has no text or accessible name."))
    return issues


def _check_headings(soup):
    issues = []
    previous = 0
    for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        level = int(h.name[1])
        if previous and level > previous + 1:
            issues.append(_issue(
                "heading-order", h, f"Heading jumps from h{previous} to h{level}, skipping a level."
            ))
        previous = level
    return issues
