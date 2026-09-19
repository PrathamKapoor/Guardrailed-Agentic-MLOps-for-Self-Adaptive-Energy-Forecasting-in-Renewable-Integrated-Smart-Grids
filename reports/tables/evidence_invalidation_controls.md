# Evidence invalidation controls

| Deviation | Nature | Scientific status | Registry/import control |
| --- | --- | --- | --- |
| P9-DEV-001 | sklearn MLP violated the frozen PyTorch implementation identity | Scientific model evidence INVALIDATED | Excluded from official experiments; audit-only MLflow run allowed; reference registration rejected |
| P9-DEV-002 | Historical and current Parquet binary checksums differ after serialization change | Scientific feature integrity PASS | Historical binary SHA, current binary SHA, logical-content SHA, and deviation history are all preserved; logical identity governs scientific validity |
