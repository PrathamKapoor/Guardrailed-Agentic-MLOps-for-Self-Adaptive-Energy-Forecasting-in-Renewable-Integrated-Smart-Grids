# Data directory layout

- `data/external/RTS-GMLC/` — the approved RTS-GMLC source archive as acquired
  (ZIP extracted). Checksums are recorded in `data/manifests/rts_gmlc_manifest.yaml`
  and `data/manifests/rts_gmlc_checksums.sha256`. This is the canonical input.
- `data/processed/` — hourly canonical parquet datasets produced from
  `data/external/` by the ingestion pipeline; checksums in
  `data/manifests/processed_dataset_manifest.yaml`.
- `data/raw/RTS-GMLC/` — historical landing location from the Phase 00
  scaffold. If present, it is a copy of the same archive content kept for
  provenance; the ingestion pipeline reads `data/external/` only. Do not edit
  either location by hand.

All other `data/` subdirectories (`interim/`, `manifests/`) are pipeline-managed.
