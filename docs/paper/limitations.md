# Research Scope and Limitations

The following limitations delineate the demonstrated scope of this research and identify concrete avenues for future investigation:

---

## 1. Demonstrated Capabilities

1. **Deterministic Governance Enforcement:** A 13-gate policy engine successfully evaluates model transitions, preventing models with superior predictive metrics from bypassing lineage, fingerprint, protocol, and benchmark requirements. Both `DENY`, `REQUIRE_APPROVAL`, and genuine `ALLOW` outcomes are demonstrated and tested.
2. **Canary Deployment and Verified Rollback:** A complete lifecycle flow demonstrates candidate promotion to canary and automated artifact-level rollback verification upon canary failure (verifying serialized artifact existence, SHA-256 fingerprint, model loadability, and finite inference probe). This demonstrates artifact-level rollback verification in software; it does not demonstrate physical grid or utility-level dispatch rollback.
3. **Multi-Horizon Forecasting:** Evaluation across H1, H6, H12, and H24 horizons proves that classical ML models outperform statistical baselines (persistence and seasonal naive) across operational horizons, while published day-ahead operational forecasts dominate at H24 for Load and Wind.
4. **Renewable-Integration Analytics:** Evaluates net load forecasting, renewable matching ratios, and potential renewable surplus ($P_{\text{Wind}} + P_{\text{PV}} > L$) detection accuracy. We explicitly distinguish potential renewable surplus from actual grid curtailment, as RTS-GMLC does not model transmission or redispatch constraints. Potential surplus occurred in 16 hours (2,944.36 MWh) of the test partition and 21 hours (3,380.00 MWh) annually. This metric indicates forecast-derived potential surplus and does not represent observed or simulated grid curtailment.
5. **Deterministic Agent Firewall Enforcement:** The tested forbidden lifecycle mutation actions (7 enumerated action types) were deterministically blocked and audited within the implemented policy surface. This provides implementation-level enforcement for the defined action set, not a proof of security against arbitrary external attackers.
6. **Autocorrelation-Aware Statistical Testing:** 24-hour block bootstrap 95% confidence intervals, Wilcoxon signed-rank tests, and Diebold-Mariano tests with 24-step Harvey-Leybourne-Newbold autocorrelation correction. Under the autocorrelation-corrected DM test, PV Random Forest outperformance over H24 Daily Persistence is not statistically significant at $\alpha = 0.05$ ($p = 0.4265$), demonstrating the necessity of accounting for serial correlation.

---

## 2. Demonstrated Boundaries & Scientific Limitations

1. **Single-Year Primary Dataset:** Evaluation is conducted on the calendar year 2020 of the RTS-GMLC dataset (8,784 hourly observations). Multi-year climate extremes, decadal weather patterns, and inter-annual variability are not represented.
2. **Zero-Shot Cross-Dataset Transfer Divergence:** Uncalibrated transfer to the German OPSD dataset (49,983 hourly rows) resulted in severe scale divergence due to order-of-magnitude differences in national grid capacity (~60 GW peak load vs. ~3 GW in RTS-GMLC). The zero-shot OPSD result demonstrates poor transfer under the evaluated cross-dataset preprocessing, but does not isolate whether the degradation arises from distribution shift, scale mismatch, feature mismatch, or their combination.
3. **Negative Day-Ahead Benchmark Outcomes on Load and Wind:** The standalone ML models achieve higher error on H24 Load (+72.3%) and Wind (+135.1%) than published day-ahead operating baselines, because the external baseline incorporates complex numerical weather predictions and market commitments that autoregressive lag models lack.
4. **Deterministic Rule-Based Agents:** Agent capabilities are strictly rule-based templates over structured JSON evidence. No live Large Language Model (LLM) is used; the LLM interface is an abstract contract.
5. **Offline Evaluation Only:** The system is evaluated entirely offline on historical time series. There is no live SCADA integration, no streaming ingestion pipeline (Kafka/MQTT), and no real-time grid dispatch execution.
6. **Simulated Operator Workload:** The reduction in operator explanation burden is measured using a scenario-based analytical workload model rather than an empirical human-subject user study. No human operator study was performed; therefore the estimated workload reduction (~72%) should not be interpreted as an observed human-performance effect.
7. **Controlled Lifecycle Simulations (Not Empirical Utility Outages):** The MLOps comparison and MTTR metrics evaluate controlled scenario injections across 10 deterministic test cases (SC01-SC10) rather than empirical utility outage logs or live production telemetry.

---

## 3. Future Work

1. Integrating foundation time-series models (e.g., Chronos, TimesFM) into the challenger pool.
2. Formal human-in-the-loop user studies with grid operators and compliance officers.
3. Online streaming adapters for IEEE C37.118 synchrophasor / SCADA telemetry protocols.
4. Dynamic regulatory policy adaptation via formal domain-specific governance languages.

