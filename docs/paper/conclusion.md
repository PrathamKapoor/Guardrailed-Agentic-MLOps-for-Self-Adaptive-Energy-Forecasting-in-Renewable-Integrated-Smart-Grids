This work introduces a guardrailed agentic MLOps framework for self-adaptive energy forecasting in renewable-integrated smart grids. By coupling deterministic governance with a bounded, deterministic agent layer, the system achieves governed automation across the forecasting lifecycle - from checksummed data provisioning to candidate evaluation - without compromising integrity or safety.

Key contributions include:
- A leakage-safe evaluation protocol over the RTS-GMLC dataset: checksummed manifests, census sampling of 8,784 matched hourly observations per target, strictly chronological partitions, and a sealed 1,464-hour final-test window behind a protocol freeze.
- A bounded agent layer in which five advisory recommendation types are permitted and seven lifecycle action types are structurally blocked and audited, with memory restricted to structured summaries and evidence references.
- A deterministic governance engine (13-state lifecycle, 13 ordered gates, 16 reason codes, SHA-256 decision fingerprints) that denied all seven packaged candidates - including one whose residual-correction research result reduced load MAE to 1.54 - because formal evidence deficiencies outweigh superior offline metrics.
- An honest empirical account: the PV candidate beat its persistence benchmark (-7.6%) while the load and wind candidates lost to the published day-ahead forecasts (+72.3% and +135.1% MAE), and these outcomes are reported without post-hoc tuning.

The results support a governance-first conclusion: strong research metrics do not confer promotion eligibility, and bounded agent authority - advisory analysis under a capability firewall - is a practical architecture for research-grade MLOps in critical energy infrastructure.

Future work includes multi-year dataset evaluation across decadal weather patterns, real-time streaming adapters for IEEE synchrophasor telemetry, benchmarking foundation time-series architectures (e.g., Chronos, TimesFM) alongside classical ML in the challenger pool, and formal human-in-the-loop user studies with grid operators and compliance officers.
