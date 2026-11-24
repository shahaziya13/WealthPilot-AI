from pathlib import Path
import json
from wealthpilot.explainability import ExplanationEngine

snapshot = {
    "portfolio_id": "SYNTH-DEMO-001",
    "currency": "INR",
    "drift": {"max_drift_pct": 0.041, "threshold_pct": 0.03},
    "risk": {"tracking_error_pct": 0.016, "expected_volatility_pct": 0.105},
    "tax": {"estimated_tax": 820.0, "estimated_transaction_cost": 175.0},
    "trigger": {"type": "threshold", "reason": "Synthetic demo drift exceeds threshold"},
    "proposed_trades": [
        {"security": "SYNTH-EQ-01", "action": "SELL", "quantity": 5, "estimated_value": 2500.0},
        {"security": "SYNTH-DEBT-02", "action": "BUY", "quantity": 8, "estimated_value": 2500.0},
    ],
    "data_provenance": "synthetic_demo_data",
    "human_review_required": True,
}
out = Path("reports/day06")
out.mkdir(parents=True, exist_ok=True)
results = ExplanationEngine().explain_all(snapshot)
for audience, result in results.items():
    (out / f"{audience}_explanation.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out / f"{audience}_explanation.md").write_text(
        "# " + result["headline"] + "\n\n" +
        "\n\n".join("- " + item for item in result["explanation"]) +
        "\n\n## Evidence hash\n`" + result["evidence_sha256"] + "`\n",
        encoding="utf-8"
    )
print("Generated 3 audience explanations in reports/day06/")
print("Data provenance: synthetic_demo_data")
print("Trade execution: disabled; human review required.")
