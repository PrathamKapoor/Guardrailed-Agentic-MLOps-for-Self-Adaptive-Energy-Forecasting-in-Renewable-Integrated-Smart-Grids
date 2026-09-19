# Missing Experiments — Minimum Designs to Support Major Claims

## Priority Order

1. **Scientific importance** 2. **Feasibility** 3. **Relevance to research question** 4. **Information gain**

---

### 1. Real Operator Workload Measurement (for Claim: agentic reduces manual work)

- **Claim:** Agentic automation reduces manual MLOps work (currently PARTIALLY SUPPORTED via simulated cost model)
- **Current evidence:** Phase 18 estimated 71.8% improvement via frozen cost model (3.0s/artifact, 0.05s/record), no real operators
- **Why insufficient:** Simulated tasks, approximated times, deterministic rule backend, no user study
- **Minimum experiment:** Within-subjects operator study: same 8 task families, 2 conditions (deterministic-only vs bounded-agentic), N≥12 MLOps practitioners, randomized order, measure actual time-to-decision, time-to-recovery, intervention count, approvals, investigations, NASA-TLX, governance errors
- **Dataset:** Same frozen Phase 13-17 evidence; no new forecasting data needed
- **Metrics:** Mean time per task, total time, error rate, completeness, SUS for interpretability
- **Controls:** Identical evidence, governance, and lifecycle outcomes; counterbalanced order
- **Statistical test:** Paired t-test or Wilcoxon on time, with Holm across task families; report effect size and 95% CI via block bootstrap
- **Success:** Agentic significantly faster with non-inferior correctness/completeness and 0 governance violations
- **Failure:** No significant difference or agentic slower/more errors
- **Leakage risk:** None (no forecasting data)
- **Prerequisites:** IRB if involving human subjects, frozen Phase 18 protocol unchanged

### 2. Self-Healing Statistical Validation (for Claim: self-healing recovers degraded models)

- **Claim:** Self-healing can recover degraded models (currently ENGINEERING DEMONSTRATION on synthetic concept drift)
- **Current evidence:** Phase 15 synthetic adaptation scenarios (severity 0.5/1.0/2.0 pre-onset std, single onset 2020-08-01, expanding-window refit, 336h horizon), no ground-truth real drift, no operational stream
- **Why insufficient:** Controlled perturbations, single strategy, untuned post-drift hyperparams, no statistical comparison of recovery vs no-retraining
- **Minimum experiment:** Preregistered drift scenarios on held-out validation folds (F05-F06) with multiple synthetic shift types (mean, variance, seasonality) and magnitudes, plus real drift proxies (e.g., OPSD second period with known regime change if documented), compare no-retraining vs governed retraining (same frozen HGB/RF) on post-drift MAE, with 5-seed repetition
- **Dataset:** RTS-GMLC validation folds and OPSD temporal splits; no TEST or external evaluation data for tuning
- **Metrics:** Post-drift MAE, relative improvement, recovery time, policy eligibility rate
- **Controls:** Identical shift injection, same challenger generation, same promotion gates; compare to deterministic no-retraining baseline
- **Statistical test:** DM on post-drift absolute errors (lag 23) per scenario + Holm across scenarios
- **Success:** Retraining shows significant MAE reduction in at least one shift type with governed promotion and preserved rollback
- **Failure:** No significant improvement or retraining triggers but fails promotion gates
- **Leakage risk:** Shift magnitude must not be tuned on evaluation window; evaluation window must not overlap training

### 3. Governance Quantitative Evaluation (for Claim: governance prevents unsafe promotion under attack)

- **Claim:** Deterministic governance prevents unsafe promotion, quarantine correctness (PARTIALLY SUPPORTED via scenario tests)
- **Current evidence:** Phase 13 synthetic approval `SIMULATION_POLICY`, scenario tests with fixture challengers, no adversarial penetration
- **Why insufficient:** Synthetic candidates, not real adversarial model submissions; no tamper attempt on ledger/fingerprint
- **Minimum experiment:** Adversarial suite: submit tampered artifacts (bit-flipped model, mismatched fingerprint, invalid lineage, expired policy, missing canary) as challengers to the real governance engine; measure prevention rate, false accept/reject, audit completeness
- **Dataset:** Existing registry and policy artifacts; no new forecasting data
- **Metrics:** Prevention rate, false positive/negative, audit log completeness, lineage verification failure rate
- **Controls:** Legitimate challengers with valid evidence vs tampered ones
- **Statistical test:** Exact binomial test on prevention rate vs 100% expected
- **Success:** 100% tampered rejected, 0% legitimate rejected due to governance (allow legitimate via fixtures with valid evidence)
- **Failure:** Any tampered accepted
- **Leakage risk:** None

### 4. External Generalization with Scale Normalization (for Claim: transferable)

- **Claim:** System is transferable/robust (currently UNSUPPORTED, external shows poor transfer)
- **Current evidence:** OPSD DE negative transfer (persistence beats all, LOAD 10x worse)
- **Why insufficient:** Single external country, no scale adaptation
- **Minimum experiment:** As designed in `future_experiments.md` Experiment A: per-system z-score normalization, same frozen models, same OPSD DE evaluation (49,983 samples), compare normalized vs unnormalized nMAE and DM vs persistence
- **Required dataset:** Already has OPSD DE (no new acquisition)
- **Metrics:** nMAE, DM vs persistence (lag 23), Holm
- **Controls:** Same models, same external data, only scaling policy differs, preregistered
- **Statistical test:** DM between normalized and unnormalized absolute errors
- **Success:** Significant nMAE reduction and at least one target no longer significantly worse than persistence
- **Failure:** No improvement
- **Risk:** Must not fit scaling on evaluation period (fit on training only)

### 5. Forecasting Accuracy Improvement via Agents (for Claim: agents improve model selection/accuracy)

- **Claim:** Agents improve model selection/accuracy (currently UNSUPPORTED)
- **Current evidence:** Phase 18 shows identical lifecycle decisions (8/8) and no accuracy delta
- **Why insufficient:** Agents are advisory and deterministic; no experiment where agent recommendation changes model choice and improves MAE
- **Minimum experiment:** Preregistered agent-in-the-loop model selection: agent proposes feature set or hyperparameter adjustment based on validation evidence, constrained to frozen search spaces, vs deterministic baseline (e.g., B_lags_only) on held-out validation folds F05-F06; measure MAE difference
- **Dataset:** Validation folds, not TEST
- **Metrics:** MAE, DM
- **Controls:** Same search budget, same data, deterministic vs agentic proposal
- **Statistical test:** DM per target + Holm
- **Success:** Agentic proposal significantly better on at least one target without extra governance violations
- **Failure:** No difference (current evidence suggests this)
- **Leakage risk:** Must not use TEST or external data for selection

Prioritization: 1 and 2 highest feasibility and relevance to research question; 3 is governance-critical; 4-5 test core forecasting claims.

