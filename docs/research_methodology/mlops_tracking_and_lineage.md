# MLOps tracking and artifact lineage

## Research objective, questions, and preregistered hypotheses

Phase 12 establishes a reproducible experiment-tracking and artifact-lineage framework from dataset provenance through registry state. RQ-MLOPS-1 asks whether every reference can be traced to dataset, features, protocol, model specification, hyperparameters, seeds, and evidence. RQ-MLOPS-2 asks whether provenance-aware controls reject invalid or inconsistent artifacts. RQ-MLOPS-3 asks whether benchmark eligibility can remain independent from internal ranking. RQ-MLOPS-4 asks whether metadata remains portable across devices.

Before implementation, H-MLOPS-1 proposed that lineage-aware tracking can reconstruct valid reference provenance without undocumented assumptions; H-MLOPS-2 proposed that evidence-status and specification checks reject invalid artifacts; H-MLOPS-3 proposed that separate benchmark status prevents weak internal references from being labeled promotion-ready. Phase 12 metadata validation supports these hypotheses within the local research scope; it makes no forecasting-accuracy claim.

## Experiment Tracking Architecture

MLflow 3.15.1 uses repository-local SQLite and repository-local artifacts. Operational file URIs are separate from canonical repository-relative research paths.

## Historical Evidence Import

Phases 6–11 are explicitly `HISTORICAL_ARTIFACT_IMPORT`; they are not represented as native runs. Missing original fields remain `UNKNOWN`. P9-DEV-001 is audit-only and invalid metrics are not imported.

## Native Experiment Tracking

Future runs use `NATIVE_MLFLOW` through `tracked_run`. Phase 12 created one metadata-only `NON_EVIDENCE_SMOKE`, excluded from research aggregation.

## Evidence Validity and Artifact Lineage

The existing valid-only evidence policy is reused. Stable typed nodes and deterministic edges connect raw data, canonical data, feature specifications, protocols, model specifications, evaluations, evidence, and registry records. P9-DEV-002 retains historical binary, current binary, and logical-content hashes.

## Model Specification, Dataset, and Feature Fingerprints

Canonical JSON SHA-256 fingerprints exclude timestamps and paths. Model fingerprints cover implementation, features, hyperparameters, scaling, training, and horizon. Feature fingerprints cover names, transformations, availability, and logical identity. Dataset fingerprints index raw checksums, the processed manifest, and logical feature identities; detailed manifests remain authoritative.

## Research Registry and Benchmark Eligibility

Research role and `DEVELOPMENT_BENCHMARK_GATE` are independent. A valid reference may have gate FAIL, but `promotion_eligible` remains false. No champion, production, or deployed state exists.

## Audit Events, Portability, and Reproducibility

Append-oriented JSONL events name SYSTEM or IMPORTER actors. Canonical paths are repository-relative and were tested under two temporary roots. Reference metadata status is categorical, not numeric.

## Final-Test Isolation and Limitations

Training, HPO, model selection, feature selection, and performance access remain NO. The P9-DEV-002 integrity exception is historical only; Phase 12 new reads are zero. Historical backfill cannot recover metadata that was never recorded, and a local backend does not establish distributed production scalability.
