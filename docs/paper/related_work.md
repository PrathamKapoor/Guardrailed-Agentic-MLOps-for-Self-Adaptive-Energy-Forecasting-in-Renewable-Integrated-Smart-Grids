Related work spans three areas: (1) MLOps for reliable ML deployment, (2) agentic AI for automation, and (3) energy forecasting in smart grids.

MLOps practices focus on automating the ML lifecycle, including data validation, model training, deployment, and monitoring [1]. However, traditional MLOps often lacks formal governance for safety-critical systems. Recent work introduces MLOps for healthcare [2] and autonomous vehicles [3], emphasizing model cards, provenance, and human-in-the-loop checks. Our work extends these principles to energy forecasting, adding a deterministic governance engine with ordered evaluation gates and a tamper-evident, append-only audit ledger.

Agentic AI systems frequently use LLM-based agents to automate complex tasks [4,5]. In ML, agents have been proposed for hyperparameter tuning [6] and pipeline orchestration [7]. However, unbounded agents risk unsafe actions in critical domains, and LLM-driven behavior is inherently non-deterministic. We therefore adopt a deliberately deterministic, rule-based agent implementation that realizes the bounded-agency paradigm [8]: the agent layer produces structured, evidence-referenced advisory outputs within strict policy constraints, and its memory holds structured summaries only - never reasoning traces. This is a design choice, not a limitation of integration: non-deterministic model backends are excluded so that every agent action remains reproducible and auditable.

Energy forecasting has evolved from statistical methods to ML and deep learning [9,10]. Renewable variability necessitates probabilistic and adaptive forecasts [11]. MLOps for energy forecasting remains underexplored; existing works focus on accuracy improvements rather than deployment safety [12]. Our system fills this gap by providing a governance-driven MLOps framework tailored to grid-integrated forecasting, where model integrity and action safety are paramount, and where published day-ahead forecasts serve as strong external benchmarks that internal candidates must honestly beat.

[1] Sculley et al., "Hidden technical debt in machine learning systems," NeurIPS, 2015.
[2] Rajkomar et al., "Scalable and accurate deep learning with electronic health records," PLOS Medicine, 2018.
[3] Bojarski et al., "End to end learning for self-driving cars," arXiv, 2016.
[4] Wang et al., "HuggingGPT: Solving AI tasks with chatGPT and its friends in huggingface," arXiv, 2023.
[5] Yao et al., "Tree of thoughts: Deliberate problem solving with large language models," NeurIPS, 2023.
[6] Feurer et al., "Efficient and robust automated machine learning," NeurIPS, 2019.
[7] Zeng et al., "AgentTuning: Enabling generalized agent abilities for LLMs," arXiv, 2023.
[8] Hadfield-Menell et al., "The off-switch game," arXiv, 2016.
[9] Hong and Fan, "Probabilistic electric load forecasting: A tutorial review," International Journal of Forecasting, 2016.
[10] Liu et al., "A review of deep learning applications in renewable energy forecasting," Renewable Energy, 2019.
[11] Noorollahi et al., "A review on wind power forecasting models," Renewable and Sustainable Energy Reviews, 2019.
[12] Zhang et al., "Optimizing short-term wind power forecasting using deep learning," Energy, 2020.
