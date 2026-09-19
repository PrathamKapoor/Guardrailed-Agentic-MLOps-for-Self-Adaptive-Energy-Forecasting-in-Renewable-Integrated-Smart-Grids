# RTS-GMLC Phase 2 forensic data audit

## Executive Summary

The immutable RTS-GMLC source dataset passed the Phase 2 read-only forensic audit. All eight primary Load/WIND/PV/RTPV files cover leap-year 2020 with complete timestamp sequences: day-ahead has 8,784 hourly records (periods 1–24) and real-time has 105,408 five-minute records (periods 1–288). Critical source checksums before and after the audit are identical.

The recommended initial research targets are system total load, aggregate wind, and aggregate utility-scale PV. Their source-provided day-ahead series serve as forecast-like baselines and real-time series as actual observations, as documented by RTS-GMLC.

## Dataset Structure

The audit inspected `gen.csv` (158 rows, 57 columns), `bus.csv` (73 rows, 15 columns), `timeseries_pointers.csv` (282 rows, 6 columns), and the eight primary forecasting CSVs. Machine-readable structural facts are in `artifacts/data_audit/rts_gmlc_audit.json`; compact file profiles are in `artifacts/data_audit/file_profiles.csv`.

## Metadata Findings

`gen.csv` categories are: 31 Solar RTPV, 25 Solar PV, 20 Hydro, 16 Coal, 27 Gas CT, 10 Gas CC, 12 Oil CT, 7 Oil ST, 4 Wind, 3 synchronous condensers, and one each Nuclear, CSP, and Storage. Generator metadata contains bus ID, unit type/category/fuel, `PMax MW`, `PMin MW`, and other capacity/operating fields.

`bus.csv` maps generator bus IDs to Areas 1–3 (24, 24, and 25 buses respectively) and records the base `MW Load` field. `timeseries_pointers.csv` fields are `Simulation`, `Category`, `Object`, `Parameter`, `Scaling Factor`, and `Data File`; it has 142 DAY_AHEAD and 140 REAL_TIME entries. It supplies area `MW Load` pointers plus generator `PMax MW`/`PMin MW` pointers.

## Generator Mapping

`artifacts/data_audit/generator_mapping.csv` has 126 data rows: **126 VERIFIED, 0 PARTIAL, 0 AMBIGUOUS, 0 NOT_MAPPED**. Verification requires a matching time-series header, generator metadata (or load-area pointer), pointer-file relationship, and bus/area evidence where applicable. The real-time load pointer spells `regional_load` with a lowercase `l` while the installed filename is `regional_Load`; matching is case-insensitive only for this source spelling discrepancy and is recorded through the pointer evidence.

## Load Findings

Load has regional columns `1`, `2`, and `3`. No missing, duplicate, negative, or zero values were found. The audit-only system total ranges from 2,634.794 MW at reconstructed `2020-06-01T04:55:00` to 7,976.866 MW at `2020-08-26T14:40:00` in real time. Regional real-time means are 1,274.263, 1,384.979, and 1,505.305 respectively; regional maxima are each 2,850.0. These are descriptive facts only.

## Wind Findings

Wind has four verified plant identifiers. No missing, duplicate, negative, infinite, constant, or all-zero columns were found. The aggregate real-time range is 10.4–2,479.5; only 81 of all 421,632 wind value cells are zero. No observed plant maximum exceeds its metadata `PMax MW` in the audit’s direct comparison.

## PV Findings

Utility-scale PV has 25 verified plants. No missing, duplicate, negative, infinite, constant, or all-zero columns were found. Aggregate real-time PV ranges from 0 to 1,364.3. Individual real-time PV zero percentages are approximately 53.03%–54.60%, consistent with expected daily zero-generation periods; these zeros are valid observations rather than missingness.

## RTPV Findings

RTPV is documented as rooftop PV and is kept separate from utility-scale PV. Its 31 verified plant columns have no missing, duplicate, negative, infinite, constant, or all-zero columns. Aggregate real-time RTPV ranges from 0 to 1,021.7; plant zero percentages are approximately 54.37%–56.88%. It is a **secondary** task because its source role differs from utility-scale PV and it is typically non-dispatchable in RTS production-cost modeling.

## Timestamp Findings and Temporal Coverage

CSV `Year,Month,Day,Period` values reconstruct to continuous sequences using a one-based, start-of-interval audit convention: Period 1 maps to 00:00; period 24 maps to 23:00 for hourly data; period 288 maps to 23:55 for five-minute data. All files include 2020-02-28, leap day 2020-02-29, 2020-03-01, and 2020-12-31 with the expected 24 or 288 rows per date. There are no duplicate reconstructed timestamps, missing intervals, or out-of-order rows.

The exact source convention for whether a period label denotes interval start or interval end is not explicitly established in the inspected documentation. The reconstruction is therefore used only for continuity/audit evidence; Phase 3 must document its canonical label choice.

## Data Quality and Potential Outliers

Across all eight primary files: missing cells 0, missing rows 0, duplicate rows 0, duplicate timestamps 0, missing intervals 0, negative values 0, NaN values 0, and infinite values 0. No capacity-exceedance warnings were emitted.

`data_quality_issues.csv` contains 20 INFO records: 16 `POTENTIAL_OUTLIER_RAMP` records (largest positive and negative aggregate first differences per file) and four expected-PV/RTPV-zero records. These are descriptive flags, not bad-data labels. The largest real-time aggregate ramps are +385.727 / -357.871 for load, +530.8 / -612.5 for wind, and +165.9 / -235.2 for utility PV.

## Day-Ahead vs Real-Time Interpretation

The source README explicitly calls day-ahead load/wind/PV/RTPV series forecasted hourly profiles and real-time counterparts actual five-minute profiles. The audit verifies that they are not structurally identical: they differ in resolution, row counts, and observed values. No forecasting benchmark has been computed.

## Recommended Hourly Alignment Strategy

For later comparison, use the arithmetic **mean** of five-minute real-time values within an hour to align with hourly day-ahead profiles. Confidence is medium: the documented parameter context is MW/power, for which a mean preserves average power. The renewable wording caveat and interval-label ambiguity remain Phase 3 confirmation items; no aggregated source file was created.

## Forecasting Target Recommendations

See `docs/forecasting_tasks.md`. The selected primary tasks are system total load, aggregate wind generation, and aggregate utility-scale PV generation. Regional and plant-level targets are secondary; RTPV is secondary and separate; CSP/Hydro are out of scope for initial experiments.

## Dataset Limitations

The audited data has one year of CSV coverage, represents a research/test system, lacks native raw meteorological observations for this experiment, and cannot alone support multi-year drift claims. It also has distinct hourly day-ahead and five-minute real-time resolutions. The bundled PDF has a date example inconsistent with the actual CSV year; actual CSV contents remain authoritative.

## Phase 3 Recommendations

Phase 3 may define a canonical timestamp/interval contract, preserve raw data immutability, create explicitly versioned derived data outside `external/`, and formalize time-aware preprocessing. It must not silently resolve the documented unit or interval-label caveats.
