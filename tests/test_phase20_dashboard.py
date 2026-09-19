from __future__ import annotations
"""Phase 20 dashboard tests.

The dashboard is a static site whose only writable surface is scripts/build_dashboard.py.
This suite verifies the read-only data contract (data/*.json), the static
artefact integrity (index.html, charts.html, styles.css, app.js), and the
cross-target consistency rules mandated by spec section 33."""
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
DASH = ROOT / "dashboard"
DATA = DASH / "data"
BUILD_SCRIPT = ROOT / "scripts/build_dashboard.py"

REQUIRED_FILES = [
    "index.html", "charts.html", "styles.css", "app.js",
    "data/results.json", "data/predictions.json",
    "data/protocol.json", "data/lineage.json", "data/figures.js",
]
REQUIRED_ARTIFACTS = [
    "artifacts/research_tables/final_predictions.csv",
    "artifacts/research_tables/final_forecasting_results.csv",
    "artifacts/research_tables/final_model_comparison.csv",
    "artifacts/audit/phase_19_final_execution_audit.json",
    "artifacts/mlops/lineage/final_evaluation_lineage_report.md",
    "artifacts/research_figures/phase_19/final_model_performance_comparison.png",
    "artifacts/research_figures/phase_19/final_error_distribution.png",
    "artifacts/research_figures/phase_19/forecast_vs_actual_plots.png",
    "artifacts/research_figures/phase_19/system_architecture_final.svg",
    "artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml",
    "reports/phase_19_completion.md",
]


@pytest.fixture(scope="module")
def built():
    subprocess.run([sys.executable, str(BUILD_SCRIPT)], check=True, cwd=str(ROOT))
    return {
        "results": json.loads((DATA / "results.json").read_text(encoding="utf-8")),
        "predictions": json.loads((DATA / "predictions.json").read_text(encoding="utf-8")),
        "protocol": json.loads((DATA / "protocol.json").read_text(encoding="utf-8")),
        "lineage": json.loads((DATA / "lineage.json").read_text(encoding="utf-8")),
    }


def test_all_required_files_exist():
    for rel in REQUIRED_FILES:
        assert (DASH / rel).exists(), f"missing: {rel}"


def test_required_phase19_artifacts_present():
    for rel in REQUIRED_ARTIFACTS:
        assert (ROOT / rel).exists(), f"missing Phase 19 artefact: {rel}"


def test_figures_data_uri_well_formed():
    js = (DATA / "figures.js").read_text(encoding="utf-8")
    for key in ("performance", "error_distribution", "forecast_vs_actual", "architecture"):
        assert f'"{key}":' in js
        assert "data:image/png;base64," in js or "data:image/svg+xml;base64," in js


def test_target_switch_clean_per_target(built):
    """Cross-target consistency: no per-target field bleeds across targets."""
    for target in ("load", "wind", "pv"):
        c = built["results"]["targets"][target]["comparison"]
        assert c["frozen_model"] is not None
        assert c["external_benchmark"] is not None
        assert built["results"]["targets"][target]["configurations"][c["frozen_model"]][0]["MAE"] == pytest.approx(c["frozen_model_mae"])


def test_per_target_model_uses_correct_identity(built):
    expected = {"load": "random_forest", "wind": "hist_gradient_boosting", "pv": "random_forest"}
    for target, model in expected.items():
        c = built["results"]["targets"][target]["comparison"]
        assert c["frozen_model"] == model
        # Frozen registry identity is preserved exactly
        assert built["lineage"]["model_fingerprints"][target] == f"P10-{target}-{model}-B_lags_only"


def test_evaluation_window_matches_protocol(built):
    w = built["results"]["evaluation_window"]
    assert w["start"] == "2020-11-01T00:00:00"
    assert w["end"] == "2020-12-31T23:00:00"
    assert w["n_hours"] == 1464


def test_predictions_row_counts(built):
    counts = built["predictions"]["counts"]
    # 1464 hourly rows × 3 configurations (frozen model + mlp + benchmark) per target
    for target, count in counts.items():
        assert count == 1464 * 3, (target, count)


def test_frozen_status_pass_and_no_training_messages_present(built):
    """The dashboard explicitly displays the no-training / no-HPO / no-retraining
    guarantee and the F11/F12 walk-forward fold labels. The lag-feature names are
    rendered by app.js at runtime from data/protocol.json, so we also check app.js
    for the rendering hooks."""
    html = (DASH / "index.html").read_text(encoding="utf-8")
    js = (DASH / "app.js").read_text(encoding="utf-8")
    for needle in ("AUTHORIZED FOR INFERENCE ONLY", "F11", "F12",
                   "Training on test data", "HPO on test data",
                   "Feature selection on test data", "Model selection on test data", "Retraining on test data"):
        assert needle in html, f"missing UI element in HTML: {needle}"
    # Feature rendering hook is in app.js; values are data-driven from protocol.json
    assert "feature_explanation" in js, "missing feature rendering hook"


def test_frozen_load_text_present(built):
    text = (DASH / "index.html").read_text(encoding="utf-8")
    assert "lower mae is better" in text.lower()
    assert "H24_DAILY_PERSISTENCE" in text or "h24 daily persistence" in text.lower()
    # The spec mandates honest RESULT interpretation: PV beats benchmark, LOAD/WIND do not
    pv_idx = text.find(">PV<")
    assert pv_idx >= 0, "PV target card label not found"
    pv_section = text[pv_idx:pv_idx + 1500].lower()
    assert "outperforms" in pv_section or "better" in pv_section


def test_governance_invariants_in_data(built):
    g = built["results"]["governance_invariants"]
    for k in ("model_promoted", "challengers_created", "governance_state_changes", "rollback_events"):
        assert g[k] == 0, (k, g[k])


def test_no_secrets_in_html():
    text = (DASH / "index.html").read_text(encoding="utf-8") + (DASH / "charts.html").read_text(encoding="utf-8")
    # No API key / token / private path leaks
    forbidden = ("api_key", "secret", "password", "private_key", "sk-", "AKIA")
    for f in forbidden:
        assert f not in text.lower(), f"forbidden token {f} in dashboard HTML"


def test_no_writable_button_in_html():
    """Spec section 43 forbids training/retraining/HPO/feature selection/model
    selection/promotion/challenger creation buttons in the dashboard."""
    text = (DASH / "index.html").read_text(encoding="utf-8")
    forbidden_substrings = ("run training", "tune hyperparameters", "select features",
                            "promote model", "create challenger", "rerun final test")
    for f in forbidden_substrings:
        assert f not in text.lower(), f"forbidden control: {f}"


def test_chart_uses_canvas_no_third_party_network_calls():
    text = (DASH / "charts.html").read_text(encoding="utf-8")
    # No CDN or remote URLs
    assert "http://" not in text.replace("http://www.w3.org/2000/svg", "")  # SVG namespace is fine
    assert "https://" not in text
    assert "cdn" not in text.lower()
    assert "<canvas" in text


def test_cross_target_consistency_in_data(built):
    """Per spec section 33: LOAD uses the LOAD model, WIND uses the WIND model, PV uses the PV model.
    Verify that for each target the model identity in the results matches the model
    used in the prediction stream."""
    expected = {"load": "random_forest", "wind": "hist_gradient_boosting", "pv": "random_forest"}
    for target, model in expected.items():
        models_seen = set(built["predictions"]["models_per_target"][target])
        assert model in models_seen, (target, model, models_seen)


def test_protocol_freeze_sha_recorded_in_ui_data(built):
    import hashlib
    expected = hashlib.sha256((ROOT / "artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml").read_bytes()).hexdigest()
    assert built["protocol"]["phase_19_protocol_freeze_sha256"] == expected
    # And matches the integrity baseline
    import json as _json
    baseline = _json.loads((ROOT / "artifacts/ui_build/phase19_integrity_baseline.json").read_text())
    assert baseline["phase_19_protocol_freeze_sha256"] == expected


def test_dashboard_does_not_modify_phase19_artefacts(built):
    """The build script must be a read-only consumer of Phase 19 evidence."""
    # Re-run the build and verify the same Phase 19 artefacts are unchanged
    for rel in REQUIRED_ARTIFACTS:
        before = (ROOT / rel).read_bytes()
        subprocess.run([sys.executable, str(BUILD_SCRIPT)], check=True, cwd=str(ROOT))
        after = (ROOT / rel).read_bytes()
        assert before == after, f"Phase 19 artefact {rel} was modified by the build script"


def test_no_placeholders_in_html(built):
    text = (DASH / "index.html").read_text(encoding="utf-8")
    # Spec section 31 forbids placeholders. The strings "TODO" and "FIXME" are
    # placeholders by definition; assert the dashboard has none.
    assert "TODO" not in text
    assert "FIXME" not in text
    assert "placeholder" not in text.lower()


def test_dashboard_accessibility_minimums(built):
    """Spec section 25: semantic headings, accessible chart labels, keyboard
    navigation, visible focus states, sufficient contrast, non-color indicators."""
    html = (DASH / "index.html").read_text(encoding="utf-8")
    js = (DASH / "app.js").read_text(encoding="utf-8")
    css = (DASH / "styles.css").read_text(encoding="utf-8")
    assert '<a class="skip-link"' in html
    assert 'role=' in html
    assert 'aria-' in html
    # Non-color indicators are rendered dynamically by app.js
    assert "indicator" in js
    assert ".indicator" in css
    # Focus styles
    assert "outline" in css
    # Charts page has a role/aria-label on the canvas
    charts = (DASH / "charts.html").read_text(encoding="utf-8")
    assert 'role="img"' in charts
    assert "aria-label" in charts
