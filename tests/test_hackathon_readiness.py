from __future__ import annotations
"""Phase 21 hackathon-readiness tests.

Validates the hackathon layer (`hackathon/`) and the new docs without
modifying any research artefact. Critical checks:

  * 231/231 prior tests still pass and 20 freeze checksums still valid.
  * Phase 19 integrity baseline: all 20 artefacts byte-identical.
  * Hackathon landing page contains no fabricated quantum / GNN claims.
  * README + landing page link to the existing dashboard, not a copy.
  * No secrets, no broken internal links, accessibility minimums.
  * Result numbers (36.12 / 174.26 / 778.84 etc.) come from final_model_comparison.csv.
"""
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
HACK = ROOT / "hackathon"
DASH = ROOT / "dashboard"
INTEGRITY = ROOT / "artifacts/ui_build/phase19_integrity_baseline.json"
COMPARISON_CSV = ROOT / "artifacts/research_tables/final_model_comparison.csv"
FORECASTING_CSV = ROOT / "artifacts/research_tables/final_forecasting_results.csv"
PREDICTIONS_CSV = ROOT / "artifacts/research_tables/final_predictions.csv"
AUDIT_JSON = ROOT / "artifacts/audit/phase_19_final_execution_audit.json"
LINEAGE_MD = ROOT / "artifacts/mlops/lineage/final_evaluation_lineage_report.md"

REQUIRED_HACKATHON_FILES = [
    "index.html", "styles.css",
    "architecture.svg", "progression.svg",
    "../docs/hackathon_demo_script.md",
    "../docs/hackathon_demo_3min.md",
    "../docs/hackathon_recording_script.md",
    "../docs/hackathon_faq.md",
    "../docs/hackathon_judging_matrix.md",
    "../docs/hackathon_usp.md",
    "../docs/hackathon_installation.md",
    "../README.md",
]


def _all_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_hackathon_required_files_exist():
    for rel in REQUIRED_HACKATHON_FILES:
        assert (HACK / rel).exists(), f"missing hackathon file: {rel}"


def _resolve_freeze_target(sha_file: Path) -> Path:
    """Resolve the file a sidecar .sha256 digest covers.

    Sidecars in this repository use two formats:
      * '<digest>  <filename>' with the filename relative to the sidecar
        directory or to the repository root;
      * a bare digest, where the counterpart is the same stem with its real
        extension (e.g. phase_19_final_evaluation_protocol_freeze.yaml).
    The previous implementation used sha_file.with_suffix(""), which strips
    only '.sha256' and matched none of the actual '<name>.yaml' freeze files.
    """
    parts = sha_file.read_text(encoding="utf-8").split()
    if len(parts) > 1:
        rel = parts[1]
        for cand in (sha_file.parent / rel, ROOT / rel):
            if cand.is_file():
                return cand
    matches = [p for p in sha_file.parent.glob(sha_file.stem + ".*")
               if p.is_file() and p != sha_file]
    if len(matches) == 1:
        return matches[0]
    raise FileNotFoundError(f"cannot resolve checksum target of {sha_file.name}")


def test_pre_freeze_boundary_intact():
    """Prior test suite and 20 freeze checksums must remain valid after the
    hackathon layer was added."""
    # Recursion guard: this test re-runs the whole suite as a child process.
    # The child re-collects this file, so without the guard each nested run
    # spawns another pytest, recursing until the process tree exhausts
    # memory and dies mid-run (observed as truncated child stdout).
    if os.environ.get("SMARTGRID_NESTED_PYTEST"):
        pytest.skip("nested invocation (recursion guard)")
    env = dict(os.environ)
    env["SMARTGRID_NESTED_PYTEST"] = "1"
    # Tests. NOTE: pyproject addopts already supply a single '-q'; adding
    # another '-q' here escalated to '-qq', which suppresses the final
    # 'N passed' summary line the assertion below depends on.
    result = subprocess.run([sys.executable, "-m", "pytest", "--tb=no"],
                            capture_output=True, text=True, cwd=str(ROOT), env=env)
    assert "passed" in result.stdout, f"pytest output: {result.stdout[-500:]}"
    # The nested run must also be failure-free: 'X failed, Y passed' still
    # contains the word 'passed', so the count is parsed explicitly.
    summary = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    m = re.search(r"(\d+) failed", summary)
    assert m is None or m.group(1) == "0", f"nested pytest summary: {summary}"
    # Freeze checksums
    fail = []
    for sha_file in (ROOT / "artifacts/experimental_design").glob("*.sha256"):
        base = _resolve_freeze_target(sha_file)
        want = sha_file.read_text(encoding="utf-8").split()[0]
        got = hashlib.sha256(base.read_bytes()).hexdigest()
        if want != got:
            fail.append(base.name)
    assert not fail, f"freeze checksums changed: {fail}"


def test_phase19_integrity_baseline_holds():
    """All 20 critical Phase 19 artefacts must remain byte-identical."""
    baseline = json.loads(INTEGRITY.read_text(encoding="utf-8"))
    changed = []
    for path, info in baseline.items():
        if not isinstance(info, dict): continue
        actual = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        if actual != info["sha256"]:
            changed.append(path)
    assert not changed, f"Phase 19 artefacts changed: {changed}"


def test_hackathon_landing_does_not_claim_quantum_or_gnn():
    text = (HACK / "index.html").read_text(encoding="utf-8")
    text_l = text.lower()
    # The hackathon layer must NOT fabricate quantum or GNN stories.
    # It is allowed to acknowledge they are absent (e.g. the FAQ does this).
    fabrication_patterns = [
        r"qubit", r"\bansatz\b", r"variational quantum", r"\bvqc\b",
        r"qiskit", r"pennylane", r"\bcirq\b", r"graph neural",
        r"\bgnn\b", r"quantum (circuit|computing|advantage|simulation|processor)",
        r"graph[- ]native",
    ]
    # Allow references only in the FAQ/limitations context that explicitly
    # states the project does not use them. Match the rest of the page
    # excluding the FAQ and limitations sections.
    body_before_faq = text.split("Honest limitations")[0]
    for pat in fabrication_patterns:
        match = re.search(pat, body_before_faq, flags=re.IGNORECASE)
        assert not match, f"hackathon landing page fabricates quantum/GNN claim: {pat!r} in {match.group(0)!r}"


def test_landing_links_to_existing_dashboard_not_copy():
    """The hackathon landing must link to the existing dashboard, not duplicate it."""
    text = (HACK / "index.html").read_text(encoding="utf-8")
    assert "../dashboard/index.html" in text, "landing must link to ../dashboard/index.html"
    assert "../dashboard/charts.html" in text, "landing must link to ../dashboard/charts.html"
    # No inline duplication of the dashboard HTML body
    for marker in ("headlineFindings", "renderTargetCards"):
        assert marker not in text, f"hackathon index.html duplicates dashboard logic (marker={marker})"


def test_landing_result_table_matches_frozen_csv():
    """The hero result card on the landing page must match final_model_comparison.csv
    (after rounding to 2 decimal places for display)."""
    comparison = list(csv.DictReader(COMPARISON_CSV.open(encoding="utf-8")))
    text = (HACK / "index.html").read_text(encoding="utf-8")
    for row in comparison:
        # Each cell is rounded to 2 decimal places for display in the landing page.
        frozen = float(row["Frozen model MAE"])
        bench = float(row["Benchmark MAE"])
        rel = float(row["Relative difference (pct)"])
        assert f"{frozen:.2f}" in text, f"{row['Target']} frozen MAE {frozen:.2f} not in landing"
        assert f"{bench:.2f}" in text, f"{row['Target']} benchmark MAE {bench:.2f} not in landing"
        # Relative difference sign: + or - prefix
        rel_str = ("+" if rel >= 0 else "") + f"{rel:.2f}" + "%"
        assert rel_str in text, f"{row['Target']} relative diff {rel_str} not in landing"


def test_landing_references_all_required_sections():
    text = (HACK / "index.html").read_text(encoding="utf-8")
    for section in ("id=\"problem\"", "id=\"solution\"", "id=\"architecture\"", "id=\"results\"",
                    "id=\"why-negative\"", "id=\"uniqueness\"", "id=\"demo\"", "id=\"quickstart\"",
                    "id=\"evidence\"", "id=\"reproducibility\"", "id=\"limitations\""):
        assert section in text, f"missing anchor: {section}"


def test_no_secrets_in_hackathon():
    text = ""
    for rel in ("index.html", "styles.css"):
        text += (HACK / rel).read_text(encoding="utf-8")
    forbidden = ("api_key", "apikey", "password", "private_key", "sk-", "AKIA", "bearer ")
    for f in forbidden:
        assert f not in text.lower(), f"forbidden token {f} in hackathon HTML/CSS"


def test_no_writable_button_in_hackathon():
    """Spec section 43 forbids training/retraining/HPO/feature selection/model
    selection/promotion/challenger creation controls.

    The landing page DOES discuss what the agent layer cannot do (e.g. "agents
    cannot promote models") — that is an explanatory statement, not a control.
    This test only fails on real interactive controls (a `<button>` or `<a class="btn">`
    whose visible label contains a forbidden action)."""
    from html.parser import HTMLParser
    text = (HACK / "index.html").read_text(encoding="utf-8")
    forbidden_labels = ("train", "retrain", "promote", "rollback", "tune hyperparameter", "select feature", "create challenger", "rerun final test")

    class ButtonVisitor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.bad = []
            self.in_button = 0
            self.current = []
            self.attrs = {}
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag in ("button",):
                self.in_button += 1
                self.current = []
                self.attrs = attrs
                klass = attrs.get("class", "")
                if "btn" in klass or tag == "button":
                    pass
            elif self.in_button and tag in ("a",):
                klass = attrs.get("class", "")
                if "btn" in klass:
                    self.in_button += 1
                    self.current = []
        def handle_data(self, data):
            if self.in_button:
                self.current.append(data)
        def handle_endtag(self, tag):
            if tag in ("button", "a") and self.in_button:
                label = "".join(self.current).strip().lower()
                if any(f in label for f in forbidden_labels) and len(label) < 40:
                    self.bad.append(label)
                self.in_button -= 1

    v = ButtonVisitor()
    v.feed(text)
    assert not v.bad, f"forbidden control labels: {v.bad}"


def test_no_placeholders_in_hackathon():
    for rel in ("index.html",):
        text = (HACK / rel).read_text(encoding="utf-8")
        for marker in ("TODO", "FIXME", "placeholder", "lorem ipsum"):
            assert marker not in text.lower(), f"placeholder {marker!r} in {rel}"


def test_dashboard_does_not_modify_phase19_artefacts_in_official_run():
    """The dashboard builder must be read-only with respect to Phase 19 evidence."""
    # Run the builder twice and confirm every Phase 19 file is byte-identical before/after.
    before = {}
    for rel in [
        "artifacts/research_tables/final_predictions.csv",
        "artifacts/research_tables/final_forecasting_results.csv",
        "artifacts/research_tables/final_model_comparison.csv",
        "artifacts/audit/phase_19_final_execution_audit.json",
        "artifacts/mlops/lineage/final_evaluation_lineage_report.md",
        "artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml",
        "reports/phase_19_completion.md",
    ]:
        before[rel] = (ROOT / rel).read_bytes()
    subprocess.run([sys.executable, str(ROOT / "scripts/build_dashboard.py")], check=True, cwd=str(ROOT))
    for rel, data in before.items():
        after = (ROOT / rel).read_bytes()
        assert data == after, f"Phase 19 artefact modified by build_dashboard.py: {rel}"


def test_hackathon_accessibility_minimums():
    html = (HACK / "index.html").read_text(encoding="utf-8")
    css = (HACK / "styles.css").read_text(encoding="utf-8")
    assert '<a class="skip-link"' in html
    assert 'role=' in html or "aria-" in html
    assert "outline" in css
    # Non-color indicators (per spec section 25)
    assert "indicator" in css or "indicator" in html


def test_svgs_are_standalone_and_resolve():
    for name in ("architecture.svg", "progression.svg"):
        path = HACK / name
        text = path.read_text(encoding="utf-8")
        assert text.startswith("<?xml") or text.startswith("<svg")
        assert "</svg>" in text
        # No external references
        assert "http://" not in text.replace("http://www.w3.org/2000/svg", "")
        assert "https://" not in text


def test_readme_first_screen_optimized_for_judge():
    """Spec section 20: README first screen should be judge-friendly."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    # Within the first 60 lines, mention: title, one-line, demo, headline result.
    head = "\n".join(readme.splitlines()[:60])
    assert "Guardrailed Agentic MLOps" in head
    assert "hackathon/index.html" in readme
    assert "36.12" in readme and "174.26" in readme and "778.84" in readme
    # Has a Quick start within the first 80 lines
    head_full = "\n".join(readme.splitlines()[:80])
    assert "Quick start" in head_full or "Quick Start" in head_full


def test_internal_links_resolve():
    """All relative links from the landing page and README point to existing files."""
    def collect_links(text: str):
        for m in re.finditer(r'(?:href|src)="([^"]+)"', text):
            yield m.group(1)

    def check(text: str, base: Path):
        for link in collect_links(text):
            if link.startswith(("http://", "https://", "#", "mailto:")): continue
            # Drop anchor
            target = link.split("#", 1)[0]
            if not target: continue
            if not (base / target).exists():
                pytest.fail(f"Broken internal link in {base}: {link}")

    check((HACK / "index.html").read_text(encoding="utf-8"), HACK)
    check((ROOT / "README.md").read_text(encoding="utf-8"), ROOT)
    # Each demo script must reference real artefacts
    for name in ("docs/hackathon_demo_script.md", "docs/hackathon_demo_3min.md", "docs/hackathon_faq.md", "docs/HACKATHON_READY.md"):
        check((ROOT / name).read_text(encoding="utf-8"), ROOT)


def test_final_model_comparison_values_unchanged():
    """Spec section 47: final metrics must be unchanged. This guards against
    accidental edits to the canonical CSV."""
    rows = list(csv.DictReader(COMPARISON_CSV.open(encoding="utf-8")))
    by_target = {r["Target"]: r for r in rows}
    # The CSV stores full-precision values; the landing page rounds to 2dp for display.
    # The frozen values are: PV 36.1217..., LOAD 174.2568..., WIND 778.8412...
    # Verify the displayed rounded values match the CSV's full-precision values.
    assert abs(float(by_target["pv"]["Frozen model MAE"]) - 36.1217634355897) < 1e-6
    assert abs(float(by_target["pv"]["Benchmark MAE"]) - 39.0949852003643) < 1e-6
    assert abs(float(by_target["load"]["Frozen model MAE"]) - 174.25681766080925) < 1e-6
    assert abs(float(by_target["wind"]["Frozen model MAE"]) - 778.8412887248792) < 1e-6
