# Contributing Guidelines

Thank you for your interest in contributing to the **Guardrailed Agentic MLOps for Smart Grid Forecasting** research platform.

## Research Integrity & Governance Principles

This repository follows strict scientific integrity and governance rules defined in `AGENTS.md`:

1. **Zero Data Leakage:** Time-series splitting must be strictly chronological. Future observations must never leak into past training sets. Feature scaling, imputation, and target transforms must be fitted exclusively on training-period data.
2. **Deterministic Governance Authority:** No autonomous agent or LLM may bypass or override deterministic model-governance policy gates. All agent recommendations are strictly advisory.
3. **Firewall Enforcement:** The governance firewall (`src/smartgrid_mlops/agents/firewall.py`) permits only 5 advisory recommendation types (`INVESTIGATE`, `SUMMARIZE`, `EXPLAIN`, `REQUEST_HUMAN_REVIEW`, `CREATE_REPORT`). All lifecycle action types (`PROMOTE_MODEL`, `ROLLBACK_MODEL`, `CHANGE_POLICY`, `START_RETRAINING`, `CHANGE_FEATURES`, `MODIFY_MODEL`, `DEPLOY`) are blocked and audited.
4. **Reproducibility:** Every experiment must record random seeds, dataset versions, model fingerprints, and protocol hashes. All results must be programmatically reproducible via `reproduce_paper.py`.
5. **No Fabricated Results:** Negative results (such as models underperforming published baselines) are scientifically valuable and must be honestly reported.

## Development Workflow

1. Clone the repository and activate the virtual environment:
   ```bash
   git clone <repo-url>
   cd guardrailed-agentic-mlops-smart-grid_trial
   .venv\Scripts\activate
   ```
2. Run the test suite:
   ```bash
   python -m pytest
   ```
3. Run the paper reproduction verification:
   ```bash
   python reproduce_paper.py --quick
   ```
4. For frontend development:
   ```bash
   cd product/frontend
   npm install
   npm test
   npm run dev
   ```
