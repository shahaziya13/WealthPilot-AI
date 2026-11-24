from datetime import date
import pytest
from wealthpilot.tax import (
    TaxLot, TaxRule, LiquiditySnapshot, TradeRequest,
    select_tax_lots, estimate_capital_gains, assess_liquidity, plan_tax_aware_sell
)

def lots():
    return [
        TaxLot("L1", "EQ1", 10, date(2024, 1, 1), 80),
        TaxLot("L2", "EQ1", 10, date(2025, 6, 1), 110),
    ]

def rule():
    return TaxRule("test-equity", "equity", 365, .20, .125, 1000, cess_rate=.04)

def test_minimize_gain_selects_highest_cost_basis_first():
    selected = select_tax_lots(lots(), 5, 100, date(2026, 1, 1))
    assert selected[0].lot_id == "L2"
    assert selected[0].quantity == 5

def test_fifo_and_lifo():
    assert select_tax_lots(lots(), 2, 100, date(2026, 1, 1), "fifo")[0].lot_id == "L1"
    assert select_tax_lots(lots(), 2, 100, date(2026, 1, 1), "lifo")[0].lot_id == "L2"

def test_reject_insufficient_lots():
    with pytest.raises(ValueError, match="insufficient"):
        select_tax_lots(lots(), 25, 100, date(2026, 1, 1))

def test_tax_estimate_separates_holding_periods():
    selected = select_tax_lots(lots(), 20, 120, date(2026, 1, 1))
    result = estimate_capital_gains(selected, 120, date(2026, 1, 1), rule())
    assert result.short_term_gain == 100
    assert result.long_term_gain == 400
    assert result.estimated_total_tax >= 0
    assert result.taxable_long_term_gain == 0  # test rule exemption is 1,000

def test_liquidity_caps_daily_trade_and_estimates_cost():
    snap = LiquiditySnapshot(1_000_000, 10, .02, .10)
    result = assess_liquidity(250_000, snap)
    assert result.permitted_value == 100_000
    assert result.days_required == 3
    assert not result.is_fully_executable_today
    assert result.estimated_total_cost > 0

def test_trade_plan_never_executes_and_requires_approval():
    req = TradeRequest("EQ1", 5, 100, date(2026, 1, 1))
    plan = plan_tax_aware_sell(req, lots(), rule(), LiquiditySnapshot(100_000, 5, .01))
    assert plan.execution_status == "REQUIRES_HUMAN_APPROVAL"
    assert plan.requires_human_approval
    assert plan.requested_notional == 500

def test_liquidity_days_uses_ceiling_for_fractional_sessions():
    snap = LiquiditySnapshot(1_000_000, 10, .02, .10)
    assert assess_liquidity(200_001, snap).days_required == 3

def test_invalid_market_impact_coefficient_rejected():
    with pytest.raises(ValueError):
        LiquiditySnapshot(1_000_000, 10, .02, .10, market_impact_coefficient=-0.1)

def test_invalid_rule_rate_rejected():
    with pytest.raises(ValueError):
        TaxRule("bad", "equity", 365, 1.2, .1)

def test_future_rule_rejected():
    future = TaxRule("future", "equity", 365, .2, .1, effective_from=date(2027,1,1))
    selected = select_tax_lots(lots(), 1, 100, date(2026,1,1))
    with pytest.raises(ValueError, match="not yet effective"):
        estimate_capital_gains(selected, 100, date(2026,1,1), future)
