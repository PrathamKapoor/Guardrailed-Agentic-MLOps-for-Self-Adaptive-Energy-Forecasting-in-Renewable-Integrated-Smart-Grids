# RTS-GMLC forecasting task definition

This document defines Phase 2 target choices from the audited source data. It does not create an aggregated dataset, features, splits, or model inputs.

| Task | Target | Priority | Actual file | Baseline file | Frequency | Unit | Mapping confidence | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Demand | System total electricity load | PRIMARY | `Load/REAL_TIME_regional_Load.csv` | `Load/DAY_AHEAD_regional_Load.csv` | 5-minute actual vs hourly baseline | MW context | VERIFIED | Sum of the three documented regional columns for later analysis; audit-only total is not a processed dataset. |
| Wind | Aggregate wind generation | PRIMARY | `WIND/REAL_TIME_wind.csv` | `WIND/DAY_AHEAD_wind.csv` | 5-minute actual vs hourly baseline | MW parameter context | VERIFIED | Four metadata-verified Wind generators. |
| Solar | Aggregate utility-scale PV generation | PRIMARY | `PV/REAL_TIME_pv.csv` | `PV/DAY_AHEAD_pv.csv` | 5-minute actual vs hourly baseline | MW parameter context | VERIFIED | 25 metadata-verified Solar PV generators. Nighttime zeros remain valid observations. |
| Demand/wind/PV | Regional load and plant-level series | SECONDARY | corresponding real-time files | corresponding day-ahead files | native | source context | VERIFIED | Retain for disaggregated experiments after Phase 3 canonical preprocessing. |
| Solar | Aggregate rooftop PV | SECONDARY | `RTPV/REAL_TIME_rtpv.csv` | `RTPV/DAY_AHEAD_rtpv.csv` | native | MW parameter context | VERIFIED | Separate from utility-scale PV; RTS documentation calls it rooftop PV and typically non-dispatchable in PCM. |
| Renewable | CSP and Hydro | OUT_OF_SCOPE | available directories | not selected | not selected | not selected | not applicable | Present but not selected for the initial demand/wind/solar scope. |

## Selected primary tasks

1. **System total electricity load** represents demand forecasting and uses all three documented regional series. It is primary because it supplies a clear system-level demand target while retaining regional targets for secondary work.
2. **Aggregate wind generation** represents weather-sensitive variable renewable output across the four source-verified wind plants.
3. **Aggregate utility-scale PV generation** represents solar intermittency across the 25 source-verified utility-scale plants.

Together these directly cover demand, wind, and solar in the project’s stated smart-grid forecasting focus.

## Baseline and actual semantics

The RTS-GMLC time-series README identifies day-ahead load/wind/PV/RTPV files as forecasted hourly series and real-time counterparts as actual 5-minute profiles. Consequently, the day-ahead files are the provided forecast-like baselines and real-time files are the candidate observations, resource by resource. This is a semantic validation only, not a forecast benchmark.

## Later resolution alignment recommendation

**Recommendation:** align real-time five-minute values to an hour using their arithmetic mean when comparing to hourly day-ahead series.

**Confidence:** medium. The source calls load values power demand, and `timeseries_pointers.csv`/metadata use `MW Load` and `PMax MW`; for a power quantity, an hourly mean preserves average power. The time-series README also uses “available energy generation” wording for renewable profiles, so Phase 3 must preserve the source unit contract and explicitly confirm this choice before canonicalization. No aggregation was saved in Phase 2.

## PV handling and limitations

PV/RTPV zeros occur frequently in the audited source and are consistent with nighttime behavior; they must not be imputed as missing just because their value is zero. Later PV evaluation should not rely solely on MAPE because near-zero actuals can make it unstable or undefined; MAE, RMSE, sMAPE, nMAE, and nRMSE are suitable candidates for a later evaluation phase.

The dataset has one observed year (2020), is a research/test system, has no native raw meteorological observations in this experiment, and has day-ahead/real-time resolution differences. It supports controlled research but motivates later external validation, weather extension, and controlled drift simulation.
