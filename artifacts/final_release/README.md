# Final Research Release

This package contains the research materials for the paper:
"Guardrailed Agentic MLOps for Self-Adaptive Energy Forecasting in Renewable-Integrated Smart Grids"

## Contents

- `README.md`: This file.
- `architecture_diagram.svg`: System architecture diagram (see docs/paper/system_architecture.md for description).
- `final_results_tables/`: CSV files containing forecasting predictions and metrics.
- `methodology/`: Markdown files detailing the experimental setup and methods.
- `reproducibility/`: Materials for reproducibility, including environment, dataset, and protocol information.

## Description

The research package represents the culmination of Phase 20 of the MLOps pipeline project. It includes:
- Documentation for academic paper preparation (see docs/paper/).
- Final evaluation outputs from Phase 19.
- Reproducibility information to facilitate independent verification.

## Usage

To reproduce the evaluation results:
1. Ensure the Python environment is set up (Python 3.13, dependencies from requirements.txt).
2. Run the evaluation script: `python run_phase19_evaluation.py`
3. Check the output in the terminal and the generated artifacts.

Note: The current repository uses synthetic data and dummy models due to missing frozen artifacts. See the reproducibility documentation for details.

## License

This research package is released for academic and research purposes. Please refer to the main repository's license for details.