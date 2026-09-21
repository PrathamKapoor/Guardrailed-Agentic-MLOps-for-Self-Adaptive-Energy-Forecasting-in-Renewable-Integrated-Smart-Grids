The system architecture consists of five layers, as shown in Figure 1.

1. **Quantum Trust Layer** (Bottom): Implements post-quantum cryptography (ML-KEM for encryption, ML-DSA for signatures, SHA-3 for hashing) to secure all artifacts and communications. Includes cryptographic agility and versioned key management.

2. **Verification Engine**: Generates immutable verification packets for every operation (training, deployment, health checks) and maintains an append-only hash-chained evidence ledger for tamper-evident auditing.

3. **Model Trust System**: Binds model, dataset, code, environment, and metrics into a cryptographic model passport. Uses a QML-BOM for full supply-chain tracking. The secure registry enforces a state machine with cryptographic gates (REGISTERED → VERIFIED → APPROVED → DEPLOYED) and separation of duties.

4. **Agentic MLOps Layer**: Deploys five specialized agents (Data, Performance, Security, Quantum Security, Red Team) that produce evidence-based findings. An adaptive supervisor implements an Observe → Detect → Reason → Act → Verify → Learn control loop, making decisions (ACCEPT, RETRAIN, QUARANTINE, etc.) based on risk scores and learning state.

5. **Self-Healing Pipeline**: Orchestrates the lifecycle: provision data → train → build QML-BOM → sign passport → register → agent evaluation → supervisor decision → deploy gate → health monitoring → automatic recovery (retrain/verify/deploy or rollback).

**Agentic Layer Interaction**: Human operators interact with the system through the Adaptive Supervisor. The Bounded Agentic AI layer (the five agents) provides automated analysis and recommendations, but the supervisor retains final authority, ensuring deterministic governance.

Data flow for energy forecasting:
- Historical load, wind, and PV data (from RTS-GMLC or similar) are provisioned as datasets.
- Features are engineered (lagged values, calendar features, etc.) and validated by the Data Agent.
- Models (Random Forest, HistGradientBoosting) are trained and registered with full provenance.
- The Performance Agent monitors forecast accuracy (MAE, RMSE, etc.) and drift.
- Upon detecting degradation, the supervisor decides on retraining or rollback, but only if governance checks pass.
- The Red Team and Quantum Security agents adversarially test the system for tampering and cryptographic weakness.
- All actions are recorded in the evidence ledger for reproducibility.

Figure 1: Architecture diagram (see artifacts/final_release/architecture_diagram.svg for detailed visual).