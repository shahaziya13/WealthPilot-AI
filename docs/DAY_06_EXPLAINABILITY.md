# Day 06 — Explainability Engine

## Purpose
Provide deterministic, evidence-grounded explanations of supplied portfolio analytics for clients, advisors, and compliance reviewers.

## Capabilities
- Client, advisor, and compliance explanation styles.
- Uses supplied drift, threshold, risk, tax, transaction-cost, trigger, and proposed-trade fields.
- Preserves evidence in structured output and calculates a SHA-256 evidence fingerprint.
- Marks missing metrics as unavailable instead of fabricating values.
- Validates non-finite and invalid numeric inputs.
- Defaults to human review and explicitly disables execution.

## Input contract
`ExplanationEngine.explain(snapshot, audience="client")` accepts a mapping with optional:
`portfolio_id`, `currency`, `drift.max_drift_pct`, `drift.threshold_pct`,
`risk.tracking_error_pct`, `risk.expected_volatility_pct`,
`tax.estimated_tax`, `tax.estimated_transaction_cost`,
`trigger.type`, `trigger.reason`, `proposed_trades[]`,
`data_provenance`, and `human_review_required`.

Drift and threshold values are proportions: `0.03` means 3%.
Trade entries may contain `security` (or `asset`), `action`, `quantity`,
and `estimated_value`.

## Run
```powershell
python -m pytest tests\test_explainability.py -v
python -m pytest -v
python scripts\run_explainability_demo.py
```

Outputs are written to `reports/day06/` and should not normally be committed.

## Boundaries
This is a deterministic explanation layer, not a predictive model explainer.
SHAP and LIME are explicitly not implemented in Day 6. Tax and transaction-cost
figures are passed through as estimates; this module does not validate tax law.
No trades are executed and no investment advice is generated. All demo values
are synthetic.
