# P9-DEV-001

## Status: RESOLVED

Expected implementation: `PYTORCH_MLP_V1` (PyTorch). Incorrect implementation: scikit-learn `MLPRegressor`. The mismatch changed training, scaling, and architecture semantics; its impact is restricted to the invalid neural HPO evidence. Classical evidence is unaffected and the final test was not contaminated.

Corrective PyTorch search is complete and the frozen selected configurations were evaluated in 30/30 F05/F06 seed runs. The quarantined studies remain retained for audit history with `evidence_status: INVALIDATED` and `deviation_id: P9-DEV-001`; official invalid evidence count is 0.

Preventive controls are implementation identity assertions, selected-config freeze checksums, framework/implementation validation, valid-only aggregation, and exclusion regression tests.
