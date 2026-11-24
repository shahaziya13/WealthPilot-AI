from dataclasses import dataclass
from math import ceil, isfinite

@dataclass(frozen=True)
class LiquiditySnapshot:
    adv_value: float
    bid_ask_spread_bps: float
    daily_volatility: float
    participation_rate: float = 0.10
    max_trade_value: float | None = None
    market_impact_coefficient: float = 1.0

    def __post_init__(self):
        numeric = (self.adv_value, self.bid_ask_spread_bps, self.daily_volatility,
                   self.participation_rate, self.market_impact_coefficient)
        if not all(isfinite(x) for x in numeric):
            raise ValueError("liquidity inputs must be finite numbers")
        if self.adv_value <= 0 or self.daily_volatility < 0:
            raise ValueError("adv_value must be positive and volatility non-negative")
        if self.bid_ask_spread_bps < 0 or not 0 < self.participation_rate <= 1:
            raise ValueError("invalid spread or participation_rate")
        if self.market_impact_coefficient < 0:
            raise ValueError("market_impact_coefficient must be non-negative")
        if self.max_trade_value is not None and (not isfinite(self.max_trade_value) or self.max_trade_value < 0):
            raise ValueError("max_trade_value must be non-negative")

@dataclass(frozen=True)
class LiquidityAssessment:
    requested_value: float
    permitted_value: float
    daily_capacity: float
    estimated_spread_cost: float
    estimated_market_impact_cost: float
    estimated_total_cost: float
    days_required: int
    is_fully_executable_today: bool
    reason: str

def assess_liquidity(requested_value: float, snapshot: LiquiditySnapshot) -> LiquidityAssessment:
    if not isfinite(requested_value) or requested_value < 0:
        raise ValueError("requested_value must be non-negative")
    cap = snapshot.adv_value * snapshot.participation_rate
    if snapshot.max_trade_value is not None:
        cap = min(cap, snapshot.max_trade_value)
    permitted = min(requested_value, cap)
    spread_cost = permitted * snapshot.bid_ask_spread_bps / 10000.0
    # Square-root market-impact approximation; coefficient is calibrated externally.
    participation = permitted / snapshot.adv_value
    impact_bps = snapshot.market_impact_coefficient * snapshot.daily_volatility * 10000 * (participation ** 0.5)
    impact_cost = permitted * impact_bps / 10000.0
    days = 0 if requested_value == 0 else ceil(requested_value / cap)
    return LiquidityAssessment(
        requested_value, permitted, cap, spread_cost, impact_cost,
        spread_cost + impact_cost, days, requested_value <= cap + 1e-9,
        "Within daily participation limit" if requested_value <= cap + 1e-9
        else "Phase execution across multiple sessions; human approval required"
    )
