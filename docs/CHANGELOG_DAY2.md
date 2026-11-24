# Day 2 changelog
- Added vectorised portfolio drift calculations (absolute drift, SAD, RMSD, max drift).
- Added annualised ex-ante tracking error using six-asset-class covariance.
- Added category thresholds and valid per-portfolio drift-band overrides.
- Added severity-ranked monitoring queue and Parquet/CSV outputs.
- Added tests for zero/extreme drift, covariance, unknown assets, target validation and threshold overrides.
- All input data remains synthetic; no live orders are submitted.
