# Canonical data dictionary

| Variable | Meaning | Unit | Source / transformation | Role | Nullable |
| --- | --- | --- | --- | --- | --- |
| timestamp | Canonical hourly start timestamp | local source time; timezone not supplied | Year/Month/Day/Period reconstruction | index | no |
| actual_system_load | Observed system demand | MW context | mean of five-minute regional values, then regional sum | target | no |
| day_ahead_system_load | RTS day-ahead system demand forecast | MW context | hourly regional sum | external baseline | no |
| actual_wind | Observed aggregate wind | MW parameter context | mean then sum of four verified plants | target | no |
| day_ahead_wind | RTS day-ahead aggregate wind forecast | MW parameter context | sum of four verified plants | external baseline | no |
| actual_pv | Observed aggregate utility-scale PV | MW parameter context | mean then sum of 25 verified PV plants | target | no |
| day_ahead_pv | RTS day-ahead aggregate utility-scale PV forecast | MW parameter context | sum of 25 verified PV plants | external baseline | no |

Plant-level and regional columns are preserved in their resource-specific hourly Parquet files. RTPV is excluded from PV canonical output.
