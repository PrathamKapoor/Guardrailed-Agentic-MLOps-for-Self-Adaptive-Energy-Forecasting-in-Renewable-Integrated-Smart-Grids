# Drift detection and monitoring

## Research Objective
Phase 14 evaluates deterministic multi-signal monitoring using development data only.

## Monitoring Architecture
Feature, prediction, performance, and data-quality detectors emit auditable events.

## Calibration and Thresholds
F01-F03 calibrate 99th-percentile thresholds before F04-F06 or synthetic evaluation. Windows are 168 hours with 24-hour stride.

## Governance Isolation
Alerts are observational evidence only and cannot retrain, promote, rollback, or change lifecycle state.

## Final-Test Isolation
No final-test data or November–December targets were read; the historical P9-DEV-002 exception remains historical only.

## Limitations
Synthetic shifts do not cover all real grid changes; natural F05-F06 alerts lack ground truth; engineered predictors omit weather variables.
