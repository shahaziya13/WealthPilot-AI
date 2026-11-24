import pytest
from wealthpilot.explainability import ExplanationEngine, ExplanationError

@pytest.fixture
def snapshot():
    return {
        "portfolio_id": "SYNTH-1001",
        "currency": "INR",
        "drift": {"max_drift_pct": 0.042, "threshold_pct": 0.03},
        "risk": {"tracking_error_pct": 0.018, "expected_volatility_pct": 0.112},
        "tax": {"estimated_tax": 1250.0, "estimated_transaction_cost": 250.0},
        "trigger": {"type": "threshold", "reason": "Maximum drift exceeded configured band"},
        "proposed_trades": [
            {"security": "SYNTH-EQ-01", "action": "sell", "quantity": 10, "estimated_value": 5000}
        ],
        "data_provenance": "synthetic_test_fixture",
        "human_review_required": True,
    }

def test_client_explanation_uses_supplied_values(snapshot):
    result = ExplanationEngine().explain(snapshot, "client")
    assert result["audience"] == "client"
    assert result["evidence"]["drift"]["threshold_breach"] is True
    assert "4.20%" in " ".join(result["explanation"])
    assert result["safety"]["trade_execution"] is False

def test_advisor_contains_trade_and_risk_detail(snapshot):
    result = ExplanationEngine().explain(snapshot, "advisor")
    text = " ".join(result["explanation"])
    assert "SYNTH-EQ-01" in text
    assert "1.80%" in text

def test_compliance_has_provenance_and_limitations(snapshot):
    result = ExplanationEngine().explain(snapshot, "compliance")
    assert result["evidence"]["data_provenance"] == "synthetic_test_fixture"
    assert any("SHAP" in item for item in result["safety"]["limitations"])

def test_explain_all_returns_three_audiences(snapshot):
    result = ExplanationEngine().explain_all(snapshot)
    assert set(result) == {"client", "advisor", "compliance"}

def test_evidence_hash_is_stable_for_same_inputs(snapshot):
    engine = ExplanationEngine()
    assert engine.explain(snapshot)["evidence_sha256"] == engine.explain(snapshot)["evidence_sha256"]

def test_missing_metrics_are_not_invented():
    result = ExplanationEngine().explain({"portfolio_id": "P-1"})
    assert result["evidence"]["drift"]["max_drift_pct"] is None
    assert "No drift or risk measurements" in " ".join(result["explanation"])

@pytest.mark.parametrize("value", [-0.1, float("nan"), float("inf"), "bad"])
def test_invalid_drift_rejected(value):
    with pytest.raises(ExplanationError):
        ExplanationEngine().explain({"portfolio_id": "P-1", "drift": {"max_drift_pct": value}})

def test_negative_tax_rejected():
    with pytest.raises(ExplanationError):
        ExplanationEngine().explain({"portfolio_id": "P-1", "tax": {"estimated_tax": -1}})

def test_invalid_audience_rejected(snapshot):
    with pytest.raises(ExplanationError):
        ExplanationEngine().explain(snapshot, "trader")

def test_invalid_trade_shape_rejected():
    with pytest.raises(ExplanationError):
        ExplanationEngine().explain({"portfolio_id": "P-1", "proposed_trades": ["BUY"]})

def test_human_review_defaults_to_true():
    result = ExplanationEngine().explain({"portfolio_id": "P-1"})
    assert result["safety"]["human_review_required"] is True
