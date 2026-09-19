# Phase 10 feature ablation results notes

Using fixed Phase 9 configurations, the classical development ranking selected lag-only features for load, wind, and PV. The wind selection used the preregistered 0.5% simplicity tie-break. The MLP anchor comparison selected the full feature set for all targets. All comparisons used identical timestamp membership within target/fold.

The post-ablation confirmation results indicate that the frozen selected classical sets achieved mean F05/F06 MAEs of 285.965 (load), 528.613 (wind), and 44.066 (PV). The frozen full-set MLP confirmation means were 482.597, 532.417, and 244.112 respectively. These are confirmation results, not final-test outcomes. Weather, wind-speed, irradiance, and cloud-cover variables remain absent, limiting interpretation for wind and PV.
