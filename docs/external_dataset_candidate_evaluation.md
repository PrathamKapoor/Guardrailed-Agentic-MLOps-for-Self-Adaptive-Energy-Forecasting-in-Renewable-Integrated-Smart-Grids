# External Dataset Candidate Evaluation

Date: 2026-08-26
Protocol: docs/research_methodology/external_validation.md

## Candidates Considered

### 1. GEFCom2012 / GEFCom2014 Load Forecasting Track

- **Source:** IEEE Power & Energy Society Global Energy Forecasting Competition, published as supplementary data to Hong et al. 2014 International Journal of Forecasting (doi:10.1016/j.ijforecast.2013.07.001 and 10.1016/j.ijforecast.2015.03.008); blog http://blog.drhongtao.com, Dropbox mirrors
- **Publisher:** IEEE Working Group on Energy Forecasting / Tao Hong et al.
- **Temporal coverage:** GEFCom2012 Load_history 2004-01-01 to 2008-06-30 (4.5 years, 8 missing weeks) hourly; GEFCom2014 2006-2014 (7 years hourly with temperature)
- **Targets:** Hierarchical load (20 zones + total), wind power (GEFCom2012 wind track); PV not in 2012, limited in 2014
- **Sampling:** Hourly
- **Features:** Load + temperature; wind features include NWP-like inputs
- **Licensing:** Supplementary material to journal article; access via ScienceDirect (paywall) or author Dropbox; no explicit open license documented on download page; Kaggle mirror incomplete (no solution data)
- **Compatibility:** Hierarchical zones require aggregation logic differing from RTS-GMLC system-load definition; feature sets B_lags_only derivable but temperature covariate not in frozen feature set; PV mapping absent for 2012
- **Verdict:** QUALIFIES technically but FAILS on provenance/licensing criterion: no stable official direct download with explicit research-permissive license and reproducible URL. Not preferred.

### 2. PJM Hourly Metered Load (Data Miner 2)

- **Source:** PJM Interconnection Data Miner 2 feed `hrl_load_metered` (https://dataminer2.pjm.com/feed/hrl_load_metered/definition), also historical metered load reports
- **Publisher:** PJM Interconnection LLC
- **Temporal coverage:** 1993-01-01 to present, hourly, per load area / zone
- **Targets:** LOAD only (metered demand); wind/solar not in this feed (separate generation feeds with 2-week lag)
- **Sampling:** Hourly (EPT/UTC)
- **Features:** Load only; no wind/PV in same table
- **Licensing:** PJM Data Miner requires account for API bulk download; no anonymous stable CSV URL; historical data via monthly reports; licensing is PJM terms of use, not clearly CC-BY for redistribution; Grid Status mirror (https://www.gridstatus.io) is third-party, not official primary source (violates preference for official source)
- **Verdict:** QUALIFIES partially (load only) but FAILS on acquisition reproducibility: requires account/API and third-party mirror would violate official-source preference. Wind/PV absent without additional feeds.

### 3. Open Power System Data (OPSD) Time Series — SELECTED

- **Source:** https://data.open-power-system-data.org/time_series/2020-10-06/  direct file `time_series_60min_singleindex.csv` (also `time_series.sqlite`); GitHub processing scripts https://github.com/Open-Power-System-Data/time_series
- **Publisher:** Open Power System Data, Neon Neue Energieökonomik, et al.
- **Temporal coverage:** 2015-01-01 to 2020-10-01 hourly (60min singleindex), 37 European countries plus aggregated; also 15min and 30min versions
- **Targets:** LOAD (e.g., `DE_load_actual_entsoe_transparency`), WIND (`DE_wind_generation_actual`, `DE_wind_onshore_generation_actual`), SOLAR (`DE_solar_generation_actual`) — all three present for DE and multiple countries; hourly
- **Sampling:** Hourly (CET/CEST, convertible to UTC), also 15/30min available; matches required hourly start-of-interval
- **Features:** Actuals for all three targets; calendar features derivable from timestamps; lag/rolling features derivable without leakage; no weather covariates needed (matches frozen B_lags_only/E_full which use only calendar + lags/rolling/ramp); external DAY_AHEAD forecast columns also available (`*_forecast`) as optional comparators
- **Licensing:** CC BY 4.0 (explicit on data platform: "published under Creative Commons Attribution"), scripts MIT; permits research use and redistribution with attribution — VERIFIED on https://open-power-system-data.org/
- **Compatibility:** B_lags_only requires lag_1/24/168 + rolling means over prior actuals — fully derivable from hourly actuals with 168h history. No semantic incompatibility. System is genuinely external: European TSO actuals (ENTSO-E Transparency) vs US synthetic RTS-GMLC 2020, different generation mix, different temporal window (2015-2020 real vs 2020 synthetic), independent data generating process.
- **Verdict:** SELECTED — satisfies all dataset requirements (temporal, targets, features, provenance, licensing, sampling, sample size, externality, reproducible official source). Well-established benchmark used in dozens of energy forecasting studies; primary data from TSOs via ENTSO-E; documented Jupyter notebooks; versioned DOI https://doi.org/10.25832/time_series/2020-10-06.

## Decision

**Selected:** OPSD Time Series 2020-10-06, file `time_series_60min_singleindex.csv` (124 MB) — hourly, CC BY 4.0, DOI 10.25832/time_series/2020-10-06.

Exactly one candidate selected after comparison. No dozens of downloads performed.

## Semantic Compatibility Mapping

OPSD → Research target:

- OPSD `DE_load_actual_entsoe_transparency` (Total load DE in MW, ENTSO-E Transparency) → research LOAD (system-level demand) — direct semantic match (country-aggregated demand, same unit MW, hourly)
- OPSD `DE_wind_generation_actual` (or `DE_wind_onshore_generation_actual`) → research WIND — aggregated wind generation, MW
- OPSD `DE_solar_generation_actual` → research PV — solar generation, MW (PV terminology mapping documented; OPSD calls solar, research calls PV)
- Forecast origin: hourly timestamp of OPSD row (CET/CEST converted to UTC, start-of-interval); horizon H24 = target at origin + 24h; H1 = origin +1h if needed diagnostic
- Feature availability: All 12 frozen features derivable from OPSD actuals + timestamps alone (no external weather). For DE: 168h history required → first 168h of OPSD series excluded as rows_lost per protocol.
- Prediction target: same as actual column per target; no DAY_AHEAD external comparator required initially (OPSD forecast columns exist but not needed for primary inference; persistence baseline derived via lag_24 as in final evaluation)
