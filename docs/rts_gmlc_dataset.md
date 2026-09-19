# RTS-GMLC dataset provenance and Phase 1 inspection

## Dataset and selection rationale

The acquired dataset is the Reliability Test System, Grid Modernization Lab Consortium (RTS-GMLC), obtained from the official GridMod repository archive. The source repository describes it as an updated RTS-96 test system developed to facilitate production-cost modeling. This makes it a useful controlled power-system research dataset for developing and testing a governed MLOps forecasting lifecycle: it contains demand and renewable-generation time series without implying that they are measurements from a real operating utility grid.

RTS-GMLC can support later electricity-demand, wind, utility-scale PV, and rooftop-PV forecasting work; comparison of day-ahead forecasts with real-time actual profiles; and controlled future drift/retraining experiments. It is a research/test system, and real-world external validation remains a later-phase requirement.

## Source and integrity

- Official repository: `https://github.com/GridMod/RTS-GMLC`
- Acquisition: local `RTS-GMLC-master.zip`, validated before extraction
- Archive SHA-256: `8c1530b008a5180b6fc11c6e70ec9269f58868e6b68f4fbfc19bba600411d6be`
- Archive-embedded Git commit: `3ece0d3725c844056132393ee252b3083dd4eab4`
- Installed immutable source root: `data/external/RTS-GMLC/`
- Source-data checksum inventory: `data/manifests/rts_gmlc_checksums.sha256`
- Full structural inventory: `data/manifests/rts_gmlc_manifest.yaml`

The archive passed ZIP CRC validation, was checked for path traversal before extraction, and contained the required `README.md`, `RTS_Data/SourceData/`, and `RTS_Data/timeseries_data_files/` structure. Source files are not transformed or edited in this phase.

## Repository documentation findings

`RTS_Data/timeseries_data_files/README.md` is the primary semantic source used here.

- **Load:** `DAY_AHEAD_regional_Load.csv` is forecasted power demand for each of three regions by hour. `REAL_TIME_regional_Load.csv` is actual power demand for those regions at 5-minute intervals. The same README says nodal load is obtained by applying the regional-load proportion recorded in `SourceData/bus.csv`.
- **Wind:** day-ahead wind is forecasted available energy generation for each wind plant by hour; real-time wind is actual available energy generation by wind plant at 5-minute intervals.
- **PV:** the PV files are utility-scale PV. Day-ahead is forecasted available energy generation by plant hourly; real-time is actual available energy generation by plant at 5-minute intervals.
- **RTPV:** the RTPV files are rooftop PV, not interchangeable with utility-scale PV. Day-ahead is forecasted energy generation by rooftop PV plant hourly; real-time is actual generation at 5-minute intervals. The source notes that RTPV is typically non-dispatchable in production-cost models.

The included `RTS-GMLC.pdf` further describes hourly day-ahead forecasts as best-available 24-hour-ahead forecasts and real-time profiles as 5-minute actuals. It identifies wind/PV source context and distinguishes utility-scale and rooftop-PV site sampling. The time-series README uses power/energy terminology but does not place a standalone unit label in each CSV header. `timeseries_pointers.csv` records `MW Load` for regional load and `PMax MW`/`PMin MW` generator parameters, providing the documented parameter-unit context; no unit conversion has been made or assumed.

## Observed temporal and column structure

All eight primary Load/WIND/PV/RTPV CSVs have `Year,Month,Day,Period` columns and cover `2020-01-01` through `2020-12-31`.

| Type | Day-ahead rows / periods | Real-time rows / periods | Value columns |
| --- | ---: | ---: | --- |
| Load | 8,784 / 1–24 | 105,408 / 1–288 | 3 regional columns (`1`, `2`, `3`) |
| WIND | 8,784 / 1–24 | 105,408 / 1–288 | 4 generator identifiers |
| PV | 8,784 / 1–24 | 105,408 / 1–288 | 25 utility-scale generator identifiers |
| RTPV | 8,784 / 1–24 | 105,408 / 1–288 | 31 rooftop-PV generator identifiers |

Thus, the expected leap-year hourly and 5-minute dimensions were observed programmatically rather than imposed. Detailed row-level quality analysis is deliberately deferred to Phase 2.

## Timeseries pointers

`SourceData/timeseries_pointers.csv` has 282 data rows and six fields: `Simulation`, `Category`, `Object`, `Parameter`, `Scaling Factor`, and `Data File`. It links a simulation mode (for example `DAY_AHEAD` or `REAL_TIME`), a generator or area object, a parameter such as `PMax MW` or `MW Load`, a scaling factor, and a relative source CSV path. Generator names in wind/PV/RTPV headers match pointer `Object` identifiers. The detailed, complete generator-to-column mapping remains Phase 2 work.

## Limitations and warnings

- The RTS-GMLC README identifies the system as a test system, so it must not be described as a real operating-utility measurement dataset.
- The bundled PDF contains an older production-cost-model date example that differs from the actual CSV timestamps. The extracted CSV values are the source of truth for the observed 2020 coverage.
- License language is recorded from the NREL data-use disclaimer in the source README; legal interpretation is out of scope for this phase.
- No preprocessing, feature engineering, split, model, or experiment has been performed.
