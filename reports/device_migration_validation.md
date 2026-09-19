# Device migration validation

- Detected project root: `C:\Projects\guardrailed-agentic-mlops-smart-grid\guardrailed-agentic-mlops-smart-grid`
- Platform: Windows 10.0.26200 / Windows NT 10.0.26200.0
- Python version: 3.13.2 (`py -3.13`)
- Virtual environment recreated: yes (`.venv`); old environment reused: **NO**.
- Dependency installation: fresh `python -m pip install -e .`, then `python -m pip install pytest`.
- Git availability: absent in ZIP; initialized locally in this project only; no remote, commit, or push.
- RTS dataset integrity: PASS (`python scripts/bootstrap_rts_gmlc.py --verify-only`).
- Processed dataset integrity: PASS (existing test suite).
- Feature manifest: PASS, SHA-256 `0e46baae741f41da7cfdad57c94d66881df368638412837a019e4f4c22b800ee`.
- Protocol freeze: PASS, SHA-256 `666eb745de5ae01ba2033e825a4c6b0ba0cea1f9574c32426de8a5996581c0f9`.
- Absolute-path issues: old POSIX paths only in immutable historical provenance fields; no runtime path issue or fix.
- Pre-Phase-6 test command: `.venv\Scripts\python.exe -m pytest`.
- Tests: 33 passed, 0 failed, 0 skipped; no pytest warnings.
