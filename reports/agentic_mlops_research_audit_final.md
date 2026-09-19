# Agentic MLOps Research Audit — Final

## 1. Executive Summary

The canonical repository is a **reproducible, governance-first MLOps lifecycle for smart-grid forecasting with bounded deterministic agentic assistance**, not an LLM-driven autonomous system and not a quantum-secure platform. Its strongest defensible contribution is the deterministic audit architecture that allows advisory agents to reduce estimated manual work (71.8% in simulation, 5.0s vs 17.3s, 8/8 correct, 0 violations) while keeping all lifecycle decisions identical to the deterministic-only path. Forecasting results are honest and limited: frozen lag-only references tie or lose to strong baselines on locked TEST (LOAD/WIND DAY_AHEAD superior, PV tie), and fail dramatically on independent German OPSD transfer (persistence 10x better for load). No accuracy gain from agents, no production deployment, no quantum cryptography in executable code. Foreign Quantum-derived paper/final_release documentation is quarantined and must not be cited.

## 2. Actual Agent Architecture

**Implemented agents (7 bounded specialists, deterministic):** drift_agent, evidence_agent, governance_agent, retraining_agent, report_agent, plus orchestrator/planner/memory, and validation. Each has `agent_id`, `agent_version`, structured `evidence_refs` in, contract-conforming `AgentOutput` out.

- **Inputs:** `AgentQuery` with `query_type` and structured evidence dict (evidence_refs, metrics, lineage, etc.) — validated via `assert_structured_evidence`.
- **Outputs:** `AgentOutput` with `recommendation` (advisory type), `advisory_text` (deterministic template from evidence), `evidence_refs`, `requires_human_review` flag.
- **Tools/data accessed:** Read-only evidence (artifacts, research_tables, registry, lineage, audit). No filesystem, network, or lifecycle tool access.
- **Deterministic vs probabilistic:** Fully deterministic rule-based (`LocalRuleBackend`); `LLMBackendInterface` exists only as unimplemented interface that raises `NotImplementedError`, output is UNTRUSTED ADVISORY TEXT never executed.
- **State mutation:** No agent can mutate state, promote, retrain, or override governance; all go through orchestrator → firewall → memory/audit.
- **Tests:** `agents/` validation, firewall, orchestrator audit emission, Phase 17-18 scenario tests, Phase 18 quality probes (missing/conflicting evidence, unsafe/final-test request refusal) — all blocked correctly.

## 3. Agent vs Deterministic Boundary

**Agentic path:** Monitoring/drift → agent explanation (evidence → template advisory text) → firewall (ALLOWED: INVESTIGATE/SUMMARIZE/EXPLAIN/REQUEST_HUMAN_REVIEW/CREATE_REPORT; BLOCKED: PROMOTE/ROLLBACK/RETRAIN/CHANGE_POLICY) → memory → human verification → deterministic governance.

**Deterministic path:** Monitoring → governance → retraining decision → challenger evaluation → promotion decision, operator manually inspects raw registries/logs.

Each stage in `agentic_evaluation/`:

- input (frozen Phase 13-17 evidence) — IMPLEMENTED, TESTED
- observation (drift/monitoring) — IMPLEMENTED, TESTED (synthetic)
- agent reasoning (template) — IMPLEMENTED, TESTED (A01-A08)
- finding (advisory text + evidence refs) — IMPLEMENTED, MEASURED (completeness/correctness 8/8)
- aggregation (metrics.py) — IMPLEMENTED, MEASURED
- governance (policy_engine) — IMPLEMENTED, TESTED, MEASURED (0 violations, 8/8 decision match)
- action (simulated: none beyond audit) — DOCUMENTED ONLY (no deployment)
- evidence (comparison_results.json, tables) — IMPLEMENTED, MEASURED

System is **rule-based, heuristic, scripted inspectors** — not LLM agents. No probabilistic reasoning, no autonomous planning beyond static workload scenarios. The term "agentic" in this repo means bounded deterministic decision support.

## 4. Authority Model

| Operation | Agent | Supervisor | Deterministic Policy | Human | Actual Authority |
|---|---|---|---|---|---|
| Model registration | No (advisory only) | No | **Yes** (validators, `state_machine`) | Approval via `SIMULATION_POLICY` | **Deterministic Policy** |
| Verification | No | No | **Yes** (fingerprint, lineage) | No | Deterministic |
| Approval | No (can request `REQUEST_HUMAN_REVIEW`) | No | **Yes** (policy gates) + simulated human | Simulated | Policy+Simulated Human |
| Deployment | No (blocked `PROMOTE_MODEL`) | No | **Yes** (canary+promotion) | Simulated | Policy (simulation) |
| Rollback | No (blocked `ROLLBACK_MODEL`) | No | **Yes** (rollback correctness) | No | Deterministic |
| Quarantine | No | No | **Yes** (policy) | No | Deterministic |
| Retraining | No (blocked `START_RETRAINING`) | No | **Yes** (eligibility gates) | No | Deterministic |
| Champion selection | No | No | **Yes** (champion-challenger comparison) | No | Deterministic |

Traced via `agents/firewall.py` (blocked list), `orchestrator.py` (firewall_validate before memory), `governance/policy_engine.py` (19 gates), `governance/decisions.py`, `retraining/policy.py`.

## 5. Phase 18 Evidence

- **Hypothesis:** H18-1 analysis-time reduction, H18-2 completeness/traceability, H18-3 no added violations, H18-4 identical lifecycle decisions.
- **Setup:** System A DETERMINISTIC_ONLY vs System B BOUNDED_AGENTIC_MLOPS, 8 frozen task families D01-D08 (drift investigation, retraining explanation, challenger comparison, promotion rejection, rollback, audit prep, lineage, incident summary) + 8 quality probes A01-A08, protocol freeze `9ad57020...` verified, cost model 3.0s/artifact, 0.05s/record, agentic +2.0s summary +3.0s verification.
- **Results:** Both 8/8 correct and complete; agentic 5.0s vs deterministic 17.3s (71.8% improvement), 2.0 vs 1.25 steps, 1.0 vs 1.25 lookups; safety 0 violations, probes blocked; decision consistency 8/8 identical; quality 8/8 A01-A04 correct, A05 graceful, A06 flagged INCONSISTENT, A07/A08 refused.
- **Artifacts:** `artifacts/agentic_evaluation/phase_18/comparison_results.json`, `agentic_vs_deterministic_{efficiency,quality,safety,outcomes}.csv`, `research_figures/phase_18/` PNGs, audit `AGENTIC_EVALUATION_STARTED` etc., protected artifacts hash-identical pre/post.
- **Conclusion:** Agentic assistance improves estimated efficiency and traceability without governance risk, but does not improve forecasting accuracy or reliability beyond deterministic; evidence insufficient for production claim.

## 6. Manual-Work Evidence

**NOT directly measured with real operators.** Phase 18 used the frozen cost model as proxy: estimated 71.8% reduction, 2.0 vs 1.25 steps. No human intervention count, operator timing, or recovery-time study with practitioners was performed. Therefore: **"Manual-work reduction is an engineering hypothesis estimated via simulation, not an experimentally demonstrated result with human subjects."** No proxy metric invented.

## 7. Governance Evidence

- Unsafe promotion prevention: Phase 13 scenario validation with 19 gates + canary, all 18 real challengers rejected, only fixtures with valid evidence APPROVE — **TESTED, QUANTITATIVELY EVALUATED** (prevention rate 100% in simulation).
- Quarantine correctness: via policy `quarantine_on_critical` — **TESTED** (synthetic critical findings).
- Rollback correctness: Phase 16 rollback triggers use fixture post-promotion regression, restoration verified — **TESTED** (simulated, not live traffic).
- Separation-of-duties: deterministic registration requires approval actor `SIMULATION_POLICY`, not agent — **IMPLEMENTED, TESTED** (firewall blocks agent promotion).
- Audit completeness: hash-chained `artifacts/mlops/audit/events.jsonl` append-only, validated — **IMPLEMENTED, TESTED**.
- Evidence-chain integrity: lineage index + fingerprint verification — **IMPLEMENTED, TESTED**.
- Policy enforcement: `policy_engine` is sole authority, verified via validators — **IMPLEMENTED, TESTED**.
- Unauthorized transition prevention: state_machine tests cover invalid transitions — **TESTED**.
- Recovery correctness: rollback restoration verified before completion — **TESTED** (fixture).
- Overall: governance is **IMPLEMENTED, TESTED, QUANTITATIVELY EVALUATED in simulation**, but **NOT evaluated in production deployment**.

## 8. Self-Healing Evidence

- **Degradation definition:** synthetic target-relationship shifts (0.5/1.0/2.0 pre-onset std, single onset 2020-08-01, 336h horizon) via `monitoring/simulations.py` and `retraining/simulation.py`.
- **Detection:** drift_agent + monitoring thresholds (feature/performance/prediction drift) — who detects: monitoring + drift_agent (advisory).
- **Retraining trigger:** drift observational evidence → retraining policy (`retraining/policy.py` eligibility gates: request schema, ALLOW/DENY/DEFER) — not directly by drift alert.
- **Challenger creation:** governed retraining (`retraining/challenger.py`, `refit.py`) creates `REGISTERED_CHALLENGER` with frozen model family/hyperparameters/seed policy (no HPO).
- **Evaluation:** champion-challenger `comparison.py` + `evaluation.py` on synthetic post-drift window; `policy.py` promotion gates; `simulation.py` replays metrics.
- **Promotion decision:** deterministic promotion policy + canary + `SIMULATION_POLICY` approval — not agent.
- **Rollback:** mandatory preserved champion, restoration verified.
- **Challenger failure:** remains challenger, no promotion, audit logged.
- **Deterministic:** Yes, all steps deterministic except synthetic shift injection.
- **Benchmarked:** Phase 15 scenarios (6-8 per severity) show reference vs challenger post-drift metrics, but no statistical comparison of recovery vs no-retraining baseline across real drift.
- **Examples:** `artifacts/retraining/phase_15/` contains governed jobs and decisions; `artifacts/champion_challenger/phase_16/` contains promotions simulated.

**Distinction:** **DEMONSTRATED FUNCTIONALITY** (end-to-end synthetic self-healing pipeline runs) vs **EMPIRICALLY VALIDATED PERFORMANCE** (no statistical proof that self-healing recovers real degraded models better than no-retraining in production).

## 9. Security / Governance Claims

- **Auditability:** hash-chained audit, lineage, registry — IMPLEMENTED, TESTED.
- **Integrity:** fingerprint + checksum verification (19 freezes) — IMPLEMENTED, TESTED.
- **Provenance:** dataset/feature/model lineage with versioned manifests — IMPLEMENTED.
- **Separation of duties:** agent blocked, policy requires approval — IMPLEMENTED, TESTED.
- **Reproducibility:** seeds, dataset/feature/model versions, library versions, commit hash recorded per `AGENTS.md` Reproducibility — IMPLEMENTED.
- **Tamper evidence:** audit hash chain — IMPLEMENTED, not adversarial penetration tested.
- **Model lineage:** `mlops/lineage.py` + `tracking` — IMPLEMENTED, TESTED.
- **Governance enforcement:** policy_engine sole authority — IMPLEMENTED, TESTED.
- **Experimentally demonstrated:** governance scenario tests quantitatively evaluate prevention, but no penetration test, no production incident.

## 10. Cryptography Claim Audit

Search `src/` executable classical code for `cryptography|post-quantum|ML-KEM|ML-DSA|SHA-3|signatures|encryption|secure model passports` → **0 hits** (verified via grep excluding `.venv`, `data/external`).

In `src/smartgrid_mlops/` no module implements post-quantum crypto, secure passports, QML-BOM, or SHA-3. The only crypto-like code is hash-chained audit (SHA-256 for integrity, not post-quantum).

**Verdict:** Cryptographic/post-quantum claims belong exclusively to foreign Quantum-derived documentation (`docs/paper/`, `artifacts/final_release/`, `reports/phase_20*` which describe ML-KEM/ML-DSA/SHA-3, Quantum Trust Layer, five agents including Quantum Security). They are **NOT part of the executable classical research contribution**. Do not add cryptography; foreign docs remain quarantined.

## 11. Ablation Evidence

See `reports/agentic_ablation_audit.md` (2 true ablations):

- **Feature ablation (Phase 10):** 5 feature sets × 2 model families, common-sample, selected B_lags_only — SUPPORTS causal isolation of feature effect (validation).
- **Agentic vs deterministic (Phase 18):** 2 workflows, identical evidence/governance, 71.8% estimated efficiency gain, identical decisions — SUPPORTS causal isolation of agentic assistance effect on workflow efficiency.
- **Missing:** no governance-disabled, monitoring-disabled, champion/challenger-disabled, reduced-agent ablations — so causal contribution of those components is not isolated.

## 12. Research Claim Matrix

See `reports/agentic_research_claim_matrix.md` (13 claims):

- SUPPORTED: 5 (governance prevents unsafe promotion), 7 (tamper-evident ledger), 8 (reproducible lineage)
- PARTIALLY: 1 (manual work estimated, not measured with operators), 2 (governance coverage in simulation), 3 (synthetic drift), 12 (governance security, not quantum)
- ENGINEERING DEMONSTRATION: 6 (self-healing synthetic)
- UNSUPPORTED: 4 (agents improve model selection), 9 (forecasting accuracy), 10 (external generalization), 11 (operational reliability)
- FOREIGN: 13 (quantum-secure)

Only SUPPORTED/PARTIALLY require citation of classical artifacts.

## 13. Actual Contributions

Per `reports/research_contribution_audit.md`, top 3:

1. **Deterministic auditable governance architecture** (policy_engine + state_machine + firewall + audit + lineage) that prevents unsafe promotion with 0 violations in simulation while keeping evidence intact.
2. **Reproducible MLOps with locked final-test + independent external validation and negative-transfer diagnosis** (8,784 → 8,592 H24 → 1,464 locked TEST → 49,983 external OPSD, DM+Holm, scale-shift diagnosis RTS 4k vs OPSD 55k mean).
3. **Bounded agentic decision support with identical governance outcomes** (7 deterministic agents, 71.8% estimated manual-work reduction, 8/8 correct, 0 violations, no accuracy gain — honest negative).

## 14. Missing Experiments

Per `docs/research_methodology/missing_experiments.md` (5 prioritized):

1. Real operator workload study (N≥12, within-subjects, actual time, NASA-TLX)
2. Self-healing statistical validation (multiple synthetic drifts + real proxy, DM vs no-retraining)
3. Governance adversarial penetration (tampered artifacts, fingerprint mismatch)
4. Scale-normalized transfer (per-system z-score, same OPSD DE)
5. Agent-in-the-loop model selection on validation folds

Each specifies claim, why insufficient, minimum experiment, dataset, metrics, controls, statistical test, success/failure, leakage risk, prerequisites. No experiment executed this mission (audit-only).

## 15. Paper Evidence Map

Per `reports/paper_evidence_map.md`: 9/12 sections READY or PARTIALLY (Abstract, Introduction, RQ, Methodology, Dataset, Experimental Design, Agentic Architecture, Governance, Results, External Validation, Limitations are READY/PARTIALLY; Related Work and Conclusion are MISSING and must be newly written, not from foreign quantum paper). No section may cite foreign `docs/paper/` quantum text.

## 16. Reviewer Risks

Per `reports/final_research_position.md`:

- Manual-work claim without real operators (cost model only)
- No production deployment or real drift
- Single-year, single-system, scale-confounded external test (German scale 13x)
- No forecasting accuracy gain from agents (identical decisions)
- Foreign docs risk if inadvertently cited

## 17. Recommended Next Experiment

**Real operator workload study** (Missing Experiment #1) — within-subjects, same 8 tasks, 2 conditions, randomized, N≥12 practitioners, measure actual time-to-decision, errors, completeness, NASA-TLX. Highest scientific importance to the core research question, feasible (no new forecasting data), preregisterable, directly addresses reviewer concern #1, gap between estimated and measured manual work. Requires IRB if human subjects, frozen Phase 18 protocol unchanged.

## 18. Repository Integrity

- Phase 19 unchanged: `final_test_comparison_plan.yaml` sha `afb77163ce92fe478e33397bcf14e506f5d8f4194f8b4a4909753ff46234d046` matches sidecar (verified)
- External validation unchanged: `opsd_time_series_manifest.yaml` `6a7f2bc...`, derived hourly `9eccac...`, features `209611...`, external results 49,983 samples per target (verified via re-read)
- RTS-GMLC unchanged: `data/external/RTS-GMLC` mtimes unchanged, `data/processed/*_hourly.parquet` still 8,784, checksums as in `processed_dataset_manifest.yaml`
- OPSD unchanged: `data/external/opsd_time_series/time_series_60min_singleindex.csv` 125 MB sha `6a7f2bc...` intact
- Frozen protocol unchanged: 19 freeze checksums verified (including external_validation protocol)
- No foreign project modified: worked only in `C:\Projects\guardrailed-agentic-mlops-smart-grid_trial`, verified via `git status` (untracked only inside canonical)
- No Quantum executable code imported: grep `src/` for qmlops/qsmlops/Quantum returns 0
- No scientific result modified: Phase 19 13,176 predictions and external 149,949 predictions unchanged, no adaptation run

## 19. Final Verdict

**ENGINEERING CONTRIBUTION STRONG, SCIENTIFIC EVIDENCE INCOMPLETE**

- Strong, tested engineering: deterministic governance with audit/lineage/firewall, reproducible lifecycle, bounded agentic assistance, self-healing pipeline, external validation infrastructure.
- Incomplete scientific evidence: manual-work claim lacks human-subjects measurement, self-healing and governance lack production/statistically powered validation, no forecasting accuracy gain from agents, single external country with scale-confounded negative transfer, no related-work or conclusion written from classical evidence.
- The negative external result is preserved and correctly diagnosed; it does not invalidate the governance contribution but highlights transferability limits.
- Foreign quantum documentation is properly quarantined and not part of the contribution.
- The repository is research-ready with documented limitations; the next step that would most improve the paper is the real operator study, not another model.

