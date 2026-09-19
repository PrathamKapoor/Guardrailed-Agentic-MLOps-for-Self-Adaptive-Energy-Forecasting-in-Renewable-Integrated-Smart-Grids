# Phase 08 completion report

## Status and objective

**COMPLETE — UNTUNED VALIDATION.** Compact MLP, unidirectional LSTM, and GRU models were evaluated before HPO, ablation, agentic selection, MLOps, or final evaluation.

## Environment and frozen design

PyTorch 2.13.0+cpu ran on Python 3.13.2, CPU. The installer reported a Windows long-path metadata warning after the runtime-compatible package installed; `import torch` succeeded. Phase 5 and Phase 7 freeze checksums remained unchanged. Phase 8 freeze SHA-256 is `6b2668ea9be9f54f17e9ee9aaa317ab4aacfee0359ec7f8a9f9340993140c98e`.

The MLP uses Phase 7 `combined_v1`; recurrent models use 168-hour historical target/calendar sequences and legal target-time calendar covariates. Training uses training-fold-only input/target scaling, Adam 0.001, MSE, batch 64, 12 epochs maximum, chronological inner 10% early stopping with patience 4, restored best weights, and recurrent gradient clipping 1.0.

## Runs

324 planned runs completed successfully; 0 failed. H24 used all five seeds across six folds; H1 is formally reduced secondary seed-42 replication.

## H24 matched validation results

| Target | Best neural | MAE | vs best classical | vs naive | vs RTS DAY_AHEAD |
| --- | --- | ---: | --- | --- | --- |
| Load | MLP | 285.611 | worse than RF 179.458 | worse than 211.392 | worse than 126.613 |
| Wind | MLP | 516.763 | worse than HGB 513.907 | better than 586.542 | worse than 269.006 |
| PV | MLP | 45.257 | worse than RF 36.588 | worse than daily 33.765 | better than 48.795 |

Sequence-track LSTM/GRU results are retained separately; their representation differs from the tabular comparison.

## Integrity and final test

Final test accessed: **NO**. Protocol checks, RTS verification, and final repository tests passed.

## Tests

**48 passed, 0 failed, 0 skipped, 0 warnings.** Compilation passed.

## Phase 9 readiness

**READY** for explicit instructions only; HPO and final-test access remain prohibited.
