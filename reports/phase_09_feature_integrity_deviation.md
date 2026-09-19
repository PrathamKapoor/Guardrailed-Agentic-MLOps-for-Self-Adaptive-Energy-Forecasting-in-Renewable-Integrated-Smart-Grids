# P9-DEV-002 — feature-integrity deviation

## Status: RESOLVED

Artifact: `data/processed/features/load/h24/combined_v1.parquet`.

- Manifest binary SHA-256: `1e4ca9fcb391587136b2def464da0685c6f6a9644b43cf9ff9b062e095ee61a1`
- Current binary SHA-256: `dc831266e3aab8f55534de91dcf9d744cedad2c0aa0997d2a7796944aeedc83d`

The original artifact is preserved at `artifacts/integrity/phase_09/p9_dev_002/combined_v1_current.parquet`.

## Findings to date

- The incident is isolated at byte level: load/H1, wind/H1, wind/H24, PV/H1, and PV/H24 all match the feature manifest. `feature_checksum_audit.csv` records the six-way audit.
- Suspect metadata: 567,414 bytes; modified `2026-08-14T04:43:35.017155+00:00`; 8,592 rows; 16 columns; one ZSTD row group; writer `parquet-cpp-arrow version 25.0.1`; Parquet format 2.6.
- Current environment: Python 3.13.2, NumPy 2.5.2, PyArrow 25.0.1, scikit-learn 1.9.0, Torch 2.13.0; pandas is not installed. Phase 8 records Python 3.13.2 and Torch 2.13.0+cpu. No historical PyArrow version was found in the inspected Phase 4/migration/Phase 5–8 records.
- The present feature logic uses the canonical `research_hourly_index.parquet`, load target `actual_system_load`, horizon 24, calendar features from forecast origin, lags 1/24/168, rolling means 24/168, and one-hour ramp. The manifest has no historical source-code/configuration hash, and the project Git worktree is untracked, so prior configuration identity cannot be proven from Git.

## Access-control blocker

Controlled final-test integrity access was explicitly authorized: `FINAL_TEST_INTEGRITY_AUDIT_ACCESS = YES`, reason `P9-DEV-002`. Final-test modeling, performance evaluation, model selection, and HPO access remain **NO**. The integrity utility performed only deterministic reconstruction, hashes, exact equality checks, metadata checks, and non-disclosing spot checks.

Both isolated rebuilds reproduce the current production binary exactly: `dc831266e3aab8f55534de91dcf9d744cedad2c0aa0997d2a7796944aeedc83d`. Current, rebuild #1, and rebuild #2 logical-content SHA-256 are all `e96842a2c7ac3eeb64d54c29985f5ca3d56268e1f12c137440b783c965b4d5fb`. Schema, row/column count, column order, timestamps, targets, all feature values, and null masks are exactly equal (0 unequal cells; maximum numeric difference 0.0). The two rebuilds are binary and logically deterministic. Five predefined feature checks—first usable row, middle year, leap-day, month boundary, and last usable row—pass without emitting values.

Classification: **MANIFEST STALENESS**. The current artifact is reproducible under PyArrow 25.0.1, but the original manifest binary checksum references a superseded serialization. The historical hash remains recorded; the manifest revision adds current binary, original binary, logical-content fingerprint, serialization environment, revision reason, and deviation ID. No feature values, timestamps, row count, schema, or production artifact were changed.

Experiment feature provenance is PASS for Phase 7, Phase 8, and Phase 9, as recorded in `experiment_feature_provenance.yaml`; no experiment used logically different load/H24 combined_v1 data. Therefore scientific feature integrity is PASS, binary integrity is **REPAIRED / VERSIONED**, and feature-pipeline reproducibility is PASS.

## Verification after forensic tooling changes

`.venv\Scripts\python.exe -m pytest`: recorded after final closure. `.venv\Scripts\python.exe -m compileall -q src scripts tests`: recorded after final closure. `.venv\Scripts\python.exe scripts\bootstrap_rts_gmlc.py --verify-only`: recorded after final closure. No HPO, training, model evaluation, frozen-protocol mutation, or Phase 10 work was performed.
