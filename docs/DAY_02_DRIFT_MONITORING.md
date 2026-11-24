# Day 02 — Portfolio Drift Monitoring Engine

## Implemented
- Absolute asset-class drift: `actual_weight - target_weight`.
- Sum of absolute drift (SAD): `sum(abs(drift))`.
- Root mean square drift (RMSD): `sqrt(mean(drift ** 2))`.
- Maximum absolute drift and largest-drift asset class.
- Annualised predicted tracking error: `sqrt(drift.T @ covariance @ drift) * sqrt(252)`.
- Risk-category thresholds and per-portfolio `drift_band` overrides.
- Severity classification and prioritised breach queue.
- Vectorised NumPy/Pandas calculations and edge-case tests.

## Threshold defaults from project brief
Ultra-Conservative 2.0%; Conservative 2.5%; Balanced 3.0%; Aggressive 4.0%; Ultra-Aggressive 5.0%. A valid `portfolios.drift_band` value takes precedence. Bands are decimal fractions.

## Run
```powershell
python scripts/run_drift_monitor.py
```

Outputs in `reports/day02/`: `portfolio_drift.parquet`, `priority_breach_queue.csv`, `asset_class_drift.parquet`, and `manifest.json`.

## Acceptance
The brief's target is a complete 50,000-portfolio scan in under 30 seconds. Measure on the target machine; do not claim it passed until the manifest reports the observed duration. The script's duration measures computation/queue work, excluding Parquet file reads and writes.

## Limitations
Day 1 market prices and returns are synthetic. Predicted tracking error is therefore a simulation estimate, not live risk or a forecast guarantee. This module monitors drift only; it does not execute trades or provide investment advice.
