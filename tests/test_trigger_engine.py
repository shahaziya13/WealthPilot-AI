import pandas as pd
from wealthpilot.triggers import TriggerEngine, TriggerConfig


def test_threshold_trigger_detects_breach():
    drift = pd.DataFrame({
        "portfolio_id": ["P1", "P2"],
        "requires_attention": [True, False],
        "severity": ["HIGH", "LOW"],
        "priority_score": [80, 10],
        "largest_drift_asset_class": ["Equity", "Debt"],
    })
    result = TriggerEngine().threshold_triggers(drift, "2026-11-24T00:00:00Z")
    assert len(result) == 1
    assert result.iloc[0]["portfolio_id"] == "P1"


def test_calendar_trigger_uses_due_dates():
    portfolios = pd.DataFrame({
        "portfolio_id": ["P1", "P2"],
        "risk_category": ["Balanced", "Aggressive"],
        "next_review_date": ["2026-11-23", "2026-12-01"],
    })
    result = TriggerEngine().calendar_triggers(portfolios, "2026-11-24T00:00:00Z")
    assert result["portfolio_id"].tolist() == ["P1"]


def test_event_trigger_filters_severity():
    events = pd.DataFrame({
        "portfolio_id": ["P1", "P2"],
        "event_type": ["LIQUIDITY_SHOCK", "MARKET_VOLATILITY"],
        "severity": ["CRITICAL", "LOW"],
        "description": ["Liquidity event", "Minor volatility"],
        "is_synthetic": [True, True],
    })
    result = TriggerEngine().event_triggers(events)
    assert len(result) == 1
    assert result.iloc[0]["severity"] == "CRITICAL"


def test_combine_deduplicates_and_ranks():
    engine = TriggerEngine()
    frame = pd.DataFrame({
        "portfolio_id": ["P1", "P1", "P2"],
        "trigger_type": ["EVENT", "EVENT", "THRESHOLD"],
        "triggered_at": pd.to_datetime(["2026-11-24T00:00Z"] * 3),
        "severity": ["HIGH", "HIGH", "CRITICAL"],
        "priority_score": [70, 70, 100],
        "reason": ["Alert", "Alert", "Drift"],
        "source": ["event_feed", "event_feed", "day02"],
        "requires_human_review": [True] * 3,
        "is_synthetic": [True] * 3,
        "trigger_id": ["same", "same", "other"],
    })
    result = engine.combine(frame, as_of="2026-11-24T00:00:00Z")
    assert len(result) == 2
    assert result.iloc[0]["portfolio_id"] == "P2"
    assert result["queue_rank"].tolist() == [1, 2]


def test_cooldown_suppresses_recent_portfolio_trigger():
    engine = TriggerEngine(TriggerConfig(cooldown_hours=24))
    frame = pd.DataFrame({
        "portfolio_id": ["P1"], "trigger_type": ["EVENT"],
        "triggered_at": pd.to_datetime(["2026-11-24T00:00Z"]),
        "severity": ["HIGH"], "priority_score": [75], "reason": ["Alert"],
        "source": ["event_feed"], "requires_human_review": [True],
        "is_synthetic": [True], "trigger_id": ["new"],
    })
    existing = pd.DataFrame({
        "portfolio_id": ["P1"], "trigger_type": ["EVENT"],
        "triggered_at": pd.to_datetime(["2026-11-23T12:00Z"]),
        "trigger_id": ["old"],
    })
    result = engine.combine(frame, existing_log=existing, as_of="2026-11-24T00:00:00Z")
    assert result.empty


def test_empty_inputs_return_empty_queue():
    result = TriggerEngine().combine(pd.DataFrame())
    assert result.empty
