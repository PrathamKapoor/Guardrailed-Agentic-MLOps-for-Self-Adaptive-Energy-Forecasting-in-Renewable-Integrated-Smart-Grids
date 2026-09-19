# Installation and reproducibility

The project is designed to be cloned, installed, and inspected quickly. The following commands have been verified on Windows 10 + Python 3.13 (`.venv\Scripts\python.exe`) and on POSIX shells (`.venv/bin/python`) where the same commands apply.

## 1. System requirements

| Requirement | Version | Notes |
| --- | --- | --- |
| Python | 3.11+ | Project was developed and verified on 3.13. |
| pip | 21+ | Standard. |
| Disk | 200 MB | Includes the dataset, models, and frozen artefacts. |
| Network | not required for the demo | The preprocessed RTS-GMLC 2020 data is shipped under `data/processed/`. |
| GPU | not required | All training and inference is CPU-only. |
| Quantum simulator | not required | The project does not contain a quantum component. |
| Browser | any modern browser | For the static dashboard. |

## 2. Install (one-time, ~3 minutes)

Windows (PowerShell or Git Bash):

```bash
cd guardrailed-agentic-mlops-smart-grid
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

POSIX:

```bash
cd guardrailed-agentic-mlops-smart-grid
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## 3. Run the test suite (~90 seconds)

```bash
.venv\Scripts\python.exe -m pytest
```

Expected: **231 passed, 0 failed, 0 skipped, 0 warnings.** This includes 18 new tests for the Phase 20 read-only dashboard and 213 backend tests covering data, tracking, governance, drift, retraining, champion-challenger, agents, and the ablation.

## 4. Open the primary demo

The dashboard is a static page; no server is required.

Windows:

```bash
start dashboard/index.html
```

POSIX:

```bash
xdg-open dashboard/index.html   # Linux
open dashboard/index.html        # macOS
```

The dashboard is read-only. It consumes pre-built JSON snapshots under `dashboard/data/` that are loaded in milliseconds. No model is re-run, no prediction is recomputed, and no research artefact is modified.

For the interactive actual-vs-predicted chart, open `dashboard/charts.html`.

## 5. Open the hackathon landing page

```bash
start hackathon/index.html   # Windows
xdg-open hackathon/index.html # Linux
open hackathon/index.html    # macOS
```

The landing page links into the dashboard and is the recommended first stop for a judge.

## 6. (Optional) Rebuild the dashboard data

This is useful if Phase 19 evidence is ever re-run:

```bash
.venv\Scripts\python.exe scripts/build_dashboard.py
```

The script reads Phase 19 artefacts (read-only) and re-emits `dashboard/data/*.json`. The test `test_dashboard_does_not_modify_phase19_artefacts` in `tests/test_phase20_dashboard.py` verifies that the script leaves every Phase 19 artefact byte-identical.

## 7. (Optional) Run the RTS data integrity check

```bash
.venv\Scripts\python.exe scripts/bootstrap_rts_gmlc.py --verify-only
```

Expected: `Integrity: PASS; Manifest: PASS; Checksums: PASS`. The preprocessed data is shipped with the repository; this check confirms it is bit-identical to the dataset manifest.

## 8. (Optional) Full reproducibility of the frozen evaluation

The frozen Phase 19 evaluation is the only authorized final evaluation. It is already executed and its outputs are in `artifacts/experiments/final_evaluation/phase_19/official/`. Re-running it would create new runs and is not required for the submission.

The 20 protocol freezes under `artifacts/experimental_design/*.sha256` can be re-verified with:

```bash
.venv\Scripts\python.exe -c "
import hashlib
from pathlib import Path
for sha_file in Path('artifacts/experimental_design').glob('*.sha256'):
    base = sha_file.with_suffix('')
    want = sha_file.read_text(encoding='utf-8').split()[0]
    got = hashlib.sha256(base.read_bytes()).hexdigest()
    status = 'PASS' if want == got else 'FAIL'
    print(f'{status} {base.name}')
"
```

Expected: 20 × `PASS` lines, one per frozen protocol artefact.

## 9. (Optional) Inspect the integrity baseline

```bash
.venv\Scripts\python.exe -c "
import json, hashlib
b = json.loads(open('artifacts/ui_build/phase19_integrity_baseline.json').read())
for path, info in b.items():
    if not isinstance(info, dict): continue
    actual = hashlib.sha256(open(path, 'rb').read()).hexdigest()
    print(f\"{'intact' if actual == info['sha256'] else 'CHANGED'}: {path}\")
"
```

Expected: 20 × `intact` lines, confirming the Phase 19 evidence was not modified during the hackathon layer build.

## 10. (Optional) Visualising the architecture

The architecture diagram in `hackathon/architecture.svg` is a standalone SVG. Open it in a browser or embed it in a presentation. It reflects the actual 20-phase implementation; no conceptual boxes that do not exist in code.

## Commands a judge actually needs

For a judge, the minimum set is:

```bash
# Install
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Verify
.venv\Scripts\python.exe -m pytest

# Open the demo
start dashboard/index.html
```

That is three commands. Total time: under five minutes including the test suite.

## Known limitations of the install

- The full raw RTS-GMLC CSV is not shipped (the preprocessed parquet is). To obtain the raw CSV, see `scripts/bootstrap_rts_gmlc.py` (downloads from the official `GridMod/RTS-GMLC` GitHub).
- The venv is per-OS. On Windows use `.venv\Scripts\python.exe`; on POSIX use `.venv/bin/python`.
- No LLM, no quantum, no GPU stack. The system is CPU-only Python.

## Troubleshooting

- **`pip install` complains about the editable install:** run `python -m pip install --upgrade pip setuptools` first.
- **Tests fail with `ModuleNotFoundError: smartgrid_mlops`:** ensure you are in the project root and the venv is activated.
- **Dashboard shows a blank page:** open the browser DevTools console — the four required `data/*.json` files must be loadable. They are emitted by `scripts/build_dashboard.py`.
- **Need to reset all frozen artefacts:** `git clean -fdX` then re-install. (Do not run this in a CI environment that has been customised.)
