from dataclasses import dataclass
from datetime import date
from math import isfinite
from .tax_lot_selector import TaxLot, select_tax_lots
from .capital_gains import TaxRule, estimate_capital_gains
from .liquidity import LiquiditySnapshot, assess_liquidity

@dataclass(frozen=True)
class TradeRequest:
    security_id: str
    quantity: float
    sale_price: float
    sale_date: date
    lot_strategy: str = "minimize_gain"
    prior_ltcg_used: float = 0.0

@dataclass(frozen=True)
class PlannedTrade:
    security_id: str
    selected_lots: tuple
    requested_quantity: float
    requested_notional: float
    executable_today_notional: float
    liquidity_days: int
    estimated_tax: object
    liquidity: object
    requires_human_approval: bool
    execution_status: str

def plan_tax_aware_sell(request: TradeRequest, lots: list[TaxLot], rule: TaxRule,
                        liquidity: LiquiditySnapshot) -> PlannedTrade:
    if (not isfinite(request.quantity) or not isfinite(request.sale_price)
            or not isfinite(request.prior_ltcg_used) or request.quantity <= 0
            or request.sale_price < 0 or request.prior_ltcg_used < 0):
        raise ValueError("sell quantity must be positive")
    if any(l.security_id != request.security_id for l in lots):
        raise ValueError("lot security_id does not match trade request")
    selections = select_tax_lots(lots, request.quantity, request.sale_price,
                                 request.sale_date, request.lot_strategy)
    tax = estimate_capital_gains(selections, request.sale_price, request.sale_date,
                                 rule, request.prior_ltcg_used)
    notional = request.quantity * request.sale_price
    liq = assess_liquidity(notional, liquidity)
    return PlannedTrade(
        request.security_id, tuple(selections), request.quantity, notional,
        liq.permitted_value, liq.days_required, tax, liq, True,
        "REQUIRES_HUMAN_APPROVAL"
    )
