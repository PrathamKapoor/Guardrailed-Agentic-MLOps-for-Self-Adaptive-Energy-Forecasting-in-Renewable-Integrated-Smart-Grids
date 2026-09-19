# MLOps tracking coverage

Lineage completeness is `100 × imported valid records / valid records discovered`; every imported record retains source artifact, protocol hash, dataset version, model fingerprint, and deterministic research key. Missing metadata counts individual absent fold, seed, or framework fields and uses `UNKNOWN`; it is not fabricated.

| Phase | Valid experiment records | Imported | Skipped invalid | Missing metadata fields | Lineage complete % |
| --- | --- | --- | --- | --- | --- |
| Phase 6 | 108 | 108 | 0 | 108 | 100.0% |
| Phase 7 | 180 | 180 | 0 | 360 | 100.0% |
| Phase 8 | 324 | 324 | 0 | 0 | 100.0% |
| Phase 9 | 60 | 60 | 1 | 60 | 100.0% |
| Phase 10 | 276 | 276 | 0 | 0 | 100.0% |
| Phase 11 | 3 | 3 | 0 | 6 | 100.0% |
