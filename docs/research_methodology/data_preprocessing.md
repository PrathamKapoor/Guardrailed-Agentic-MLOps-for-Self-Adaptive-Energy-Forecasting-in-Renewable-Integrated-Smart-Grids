# Data preprocessing methodology

## Objective and RQ-DATA-1

Phase 3 constructs reproducible, temporally consistent hourly datasets for system load, aggregate wind, and aggregate utility-scale PV from RTS-GMLC. **RQ-DATA-1:** How can heterogeneous day-ahead hourly forecasts and five-minute real-time observations be aligned into a common forecasting dataset without temporal leakage or physically invalid aggregation?

The methodological expectation—not an experimental result—is that explicit timestamp reconstruction and physically justified aggregation permit alignment while retaining immutable source data.

## Temporal harmonization

The source uses one-based `Year, Month, Day, Period` fields. The canonical convention maps Period 1 to the start of the interval (00:00), hourly Period 24 to 23:00, and five-minute Period 288 to 23:55. This convention was validated through leap day and year-end continuity. Documentation does not unambiguously specify whether labels denote starts or ends; the convention is versioned here and must remain fixed within an experiment.

DAY_AHEAD is natively hourly. Each REAL_TIME hour contains twelve five-minute values. For a power quantity in MW, the canonical hourly actual is \(\bar P_h = \frac{1}{12}\sum_{i=1}^{12}P_{h,i}\). A mean preserves average power; summing MW readings would change the physical quantity and is therefore not used. Native five-minute data is retained in `data/interim/`.

## Target construction and integrity

System load is the sum of three verified regional columns. Wind and utility-scale PV are sums over their Phase 2 verified generators (four and 25, respectively). RTPV is deliberately excluded from utility-scale PV. All source checksums are compared before and after processing. The builder writes only derived Parquet datasets and artifacts.

## Leakage safeguards and limitations

No random split, imputation, normalization, or feature construction occurs here. Day-ahead values are external baselines, not default ML inputs: they may only be used in an explicitly declared forecast-correction/residual experiment. Otherwise they would leak an existing forecast into an independently claimed prediction task.

Limitations are one year of test-system data, no native raw weather variables, uncertain source interval-label semantics, and limited direct multi-year drift inference. Later work needs external validation and a versioned temporal contract.
