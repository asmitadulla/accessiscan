/**
 * AccessiScan web UI
 * Loads personas, submits scans to the REST API, and renders the ranked report.
 */

const SAMPLE_ISSUES = {
  issues: [
    { rule: "image-alt", severity: "critical", selector: "img.hero" },
    { rule: "color-contrast", severity: "serious", selector: ".btn-primary" },
    { rule: "label", severity: "serious", selector: "input#email" },
    { rule: "keyboard-trap", severity: "critical", selector: "div.modal" },
    { rule: "heading-order", severity: "minor", selector: "h4.card-title" },
    { rule: "target-size", severity: "moderate", selector: "a.icon-link" },
  ],
};

const SEVERITIES = ["critical", "serious", "moderate", "minor"];

const form = document.getElementById("scan-form");
const personaSelect = document.getElementById("persona");
const personaDesc = document.getElementById("persona-desc");
const issuesInput = document.getElementById("issues");
const formError = document.getElementById("form-error");
const submitBtn = document.getElementById("submit-btn");
const results = document.getElementById("results");
const resultsHeading = document.getElementById("results-heading");
const resultsStatus = document.getElementById("results-status");
const summaryList = document.getElementById("summary");
const violationsBody = document.getElementById("violations");

let personas = [];

function humanize(id) {
  return id.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

function showError(message) {
  formError.textContent = message;
  formError.hidden = false;
}

function clearError() {
  formError.hidden = true;
  formError.textContent = "";
}

function updatePersonaDescription() {
  const p = personas.find((x) => x.id === personaSelect.value);
  personaDesc.textContent = p ? p.description : "";
}

async function loadPersonas() {
  const resp = await fetch("/api/v1/personas");
  personas = await resp.json();
  for (const p of personas) {
    const option = document.createElement("option");
    option.value = p.id;
    option.textContent = humanize(p.id);
    personaSelect.append(option);
  }
  updatePersonaDescription();
}

function renderSummary(summary) {
  summaryList.replaceChildren(
    ...SEVERITIES.map((level) => {
      const li = document.createElement("li");
      li.className = `sev-${level}`;
      const count = document.createElement("span");
      count.className = "count";
      count.textContent = summary.by_severity[level] ?? 0;
      const label = document.createElement("span");
      label.className = `sev sev-${level}`;
      label.textContent = humanize(level);
      li.append(count, label);
      return li;
    })
  );
}

function renderViolations(violations) {
  violationsBody.replaceChildren(
    ...violations.map((v) => {
      const tr = document.createElement("tr");

      const sev = document.createElement("td");
      const sevLabel = document.createElement("span");
      sevLabel.className = `sev sev-${v.severity}`;
      sevLabel.textContent = humanize(v.severity);
      sev.append(sevLabel);

      const issue = document.createElement("td");
      issue.textContent = v.rule;
      if (v.message) {
        const msg = document.createElement("span");
        msg.className = "issue-message";
        msg.textContent = v.message;
        issue.append(msg);
      }
      if (v.selector) {
        const code = document.createElement("code");
        code.textContent = v.selector;
        issue.append(code);
      }

      const criterion = document.createElement("td");
      criterion.textContent = v.criterion;

      const affected = document.createElement("td");
      for (const id of v.affected_personas) {
        const tag = document.createElement("span");
        tag.className = "persona-tag";
        tag.textContent = humanize(id);
        affected.append(tag);
      }
      if (!v.affected_personas.length) affected.textContent = "All users";

      const fix = document.createElement("td");
      fix.textContent = v.remediation;

      tr.append(sev, issue, criterion, affected, fix);
      return tr;
    })
  );
}

async function runScan(event) {
  event.preventDefault();
  clearError();

  // Accept bare domains like "amazon.com" by assuming https.
  const rawUrl = form.url.value.trim();
  if (rawUrl && !/^https?:\/\//i.test(rawUrl)) form.url.value = `https://${rawUrl}`;

  if (!form.url.checkValidity()) {
    showError("Enter a full URL, like https://www.wikipedia.org.");
    form.url.focus();
    return;
  }

  // Pasted results are optional; without them the server fetches and scans the URL.
  let testResults;
  if (issuesInput.value.trim()) {
    try {
      testResults = JSON.parse(issuesInput.value);
    } catch {
      showError("Test results must be valid JSON.");
      issuesInput.focus();
      return;
    }
  }

  submitBtn.disabled = true;
  submitBtn.textContent = testResults ? "Analyzing…" : "Fetching page…";
  try {
    const scanResp = await fetch("/api/v1/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: form.url.value,
        persona: personaSelect.value,
        ...(testResults && { test_results: testResults }),
      }),
    });
    const scan = await scanResp.json();
    if (!scanResp.ok) throw new Error(scan.error || "Scan failed.");

    const report = await (await fetch(`/api/v1/report/${scan.scan_id}`)).json();

    renderSummary(report.summary);
    renderViolations(report.wcag_violations);
    results.hidden = false;
    const n = report.summary.total;
    const persona = humanize(report.persona).toLowerCase();
    const source = report.source === "url_scan" ? `on ${new URL(report.url).hostname}` : "in the pasted results";
    resultsStatus.textContent = n
      ? `${n} WCAG ${n === 1 ? "violation" : "violations"} found ${source}, ranked for the ${persona} persona.`
      : `No WCAG violations found ${source}. Static checks can't see content rendered by JavaScript or test color contrast.`;
    // Move focus to the results so keyboard and screen reader users land on them.
    resultsHeading.focus();
  } catch (err) {
    showError(err.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Run scan";
  }
}

personaSelect.addEventListener("change", updatePersonaDescription);
document.getElementById("sample-btn").addEventListener("click", () => {
  if (!form.url.value) form.url.value = "https://example.com";
  issuesInput.value = JSON.stringify(SAMPLE_ISSUES, null, 2);
  issuesInput.focus();
});
form.addEventListener("submit", runScan);

loadPersonas().catch(() => showError("Could not load personas. Is the API running?"));
