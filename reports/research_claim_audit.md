# Research Claim Audit — Classical Evidence vs Documentation

Date: 2026-08-26
Scope: `C:\Projects\guardrailed-agentic-mlops-smart-grid_trial`

## Method

Searched repository (excluding `.venv`, `__pycache__`, `.pytest_cache`, `.git`, `data/external` raw) for claim indicators: `generalizes|robust|superior|state-of-the-art|production-ready|transferable|quantum|post-quantum|five agents|Quantum Trust Layer`, plus manual inspection of `docs/paper/`, `artifacts/final_release/`, `reports/phase_19*`, `reports/phase_20*`, `reports/post_phase_20*`, `reports/productization_handoff.md`.

Classification:
- SUPPORTED — executable classical evidence exists
- PARTIALLY SUPPORTED — evidence exists but limited to validation/final-test scope
- UNSUPPORTED — claim made without executable evidence in canonical repo
- FOREIGN DOCUMENTATION — byte-identical to Quantum-derived material, not produced by classical pipeline
- STALE — superseded by later Phase 19 execution

## Findings

| Claim / Location | Classification | Evidence |
|---|---|---|
| `docs/paper/system_architecture.md:1` "Quantum Trust Layer (ML-KEM, ML-DSA, SHA-3)" + 5-layer architecture | FOREIGN DOCUMENTATION | File identical to Quantum pre-split tarball `Quantum-Secure_Agentic_MLOps_Pipeline_Management_System/docs/paper/system_architecture.md`; no src module implements ML-KEM/ML-DSA/QML-BOM in `src/smartgrid_mlops/` (verified: crypto terms zero hits in src/scripts/tests/config) |
| `docs/paper/*` (abstract, introduction, related_work, results, etc.) describing Quantum Trust + 5 agents under Guardrailed title | FOREIGN DOCUMENTATION | 8 of 11 paper files contain `quantum` per sweep; 8 identical to tarball; architecture narrative mismatched with `src/` (which implements classical forecasting, not quantum trust) |
| `artifacts/final_release/architecture_diagram.svg` "Quantum Trust Layer" | FOREIGN | Identical to tarball; SVG describes 5-layer Quantum Trust, not classical pipeline |
| `artifacts/final_release/methodology/system_architecture.md` (same Quantum Trust text) | FOREIGN | Identical to tarball |
| `reports/phase_20_completion.md: "quantum-secure cryptography, Quantum Trust Layer"` | FOREIGN DOCUMENT | Identical to tarball; describes quantum-secure pipeline not present in `src/` |
| `reports/post_phase_20_release_validation.md` (qsmlops/serving/service.py, test_phase2_platform.py) | FOREIGN | Explicitly references `qsmlops` QSMLOps serving layer, not `smartgrid_mlops` |
| `reports/phase_19_completion.md` (externally staged) vs `reports/phase_19_final_execution_report.md` (classical-owned) | STALE (former) / SUPPORTED (latter) | Staged file is tarball-identical, contains planning placeholder (LOAD MAE 49 etc., predictions all 0); classical-owned report is VERIFIED with real Phase 19 metrics (LOAD MAE 174, WIND 778, PV 36) and audit trail |
| `reports/productization_handoff.md` ("Product layer PLANNED, UI NOT IMPLEMENTED") | STALE / FOREIGN | Neutral status board, not classical evidence; tariff identical to Quantum handoff |
| Classical pipeline claims: "bounded agentic AI reduces manual lifecycle work while deterministic governance retains authority" (`AGENTS.md:5`, `docs/architecture_overview.md`) | PARTIALLY SUPPORTED | Supported through Phases 12-18: deterministic governance (policy_engine, state_machine), firewall (advisory-only agents), drift monitoring, champion-challenger simulation; Phase 18 agentic vs deterministic ablation measured operational support with identical lifecycle outcomes, but no production deployment, no real LLM backend, no user study — hence partial |
| "Phase 19 locked final test executed with DM+Holm" (`reports/phase_19_final_execution_report.md`) | SUPPORTED | VERIFIED: frozen plan sha `afb77163...`, 13,176 prediction rows parquet, 3 MLflow runs FINISHED, DM statistics and Holm decisions computed, determinism check max rel 1.9e-16 |
| "External validation poor transferability due to scale shift" (`reports/external_validation_execution_report.md`) | SUPPORTED | VERIFIED: OPSD DE 49,983 samples, frozen configs, persistence baseline 4,459 vs ref 48,228 (LOAD), statistical tests p 0.0 reject, provenance manifest, canonical/feature checksums, MLflow `smartgrid/external_validation` 3 runs FINISHED |

## Unsupported / Overclaim Risks

No classical file claims "generalizes", "robust across systems", "superior to state-of-the-art", "production-ready", "quantum", or "post-quantum" based on executable evidence. Any such claim found only in foreign documentation (paper, final_release, phase_20) must be disregarded for classical research narrative. The classical evidence supports: within-distribution final-test results (LOAD/WIND DAY_AHEAD superior, PV tie, MLP not competitive) and negative transfer to OPSD German scale (persistence superior) — both legitimate, neither proves universal superiority.

## Recommendation

For final paper/release, cite only classical-owned reports (`phase_19_final_execution_report.md`, `external_validation_execution_report.md`, `final_test_evaluation.md`, `external_validation.md`) and their underlying artifacts. Treat `docs/paper/`, `artifacts/final_release/`, `reports/phase_20*`, `post_phase_20*` as FOREIGN — do not use their numbers; archive or quarantine in future cleaning step (not this mission, per prohibitions).

