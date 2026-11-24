from dataclasses import dataclass
from datetime import date
from math import isfinite

@dataclass(frozen=True)
class TaxRule:
    rule_id: str
    asset_class: str
    holding_period_days: int
    short_term_rate: float
    long_term_rate: float
    annual_ltcg_exemption: float = 0.0
    surcharge_rate: float = 0.0
    cess_rate: float = 0.0
    effective_from: date | None = None
    effective_to: date | None = None
    notes: str = "Configurable illustrative rule; verify against applicable law."

    def __post_init__(self):
        for name, value in (("short_term_rate", self.short_term_rate),
                            ("long_term_rate", self.long_term_rate),
                            ("surcharge_rate", self.surcharge_rate),
                            ("cess_rate", self.cess_rate)):
            if not isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if (self.holding_period_days < 0 or not isfinite(self.annual_ltcg_exemption)
                or self.annual_ltcg_exemption < 0):
            raise ValueError("holding period and exemption must be non-negative")

@dataclass(frozen=True)
class TaxEstimate:
    gross_gain: float
    short_term_gain: float
    long_term_gain: float
    taxable_short_term_gain: float
    taxable_long_term_gain: float
    estimated_base_tax: float
    estimated_surcharge: float
    estimated_cess: float
    estimated_total_tax: float
    rule_id: str
    assumptions: tuple[str, ...]

def estimate_capital_gains(selections, sale_price_per_unit: float, sale_date: date,
                           rule: TaxRule, prior_ltcg_used: float = 0.0) -> TaxEstimate:
    if (not isfinite(sale_price_per_unit) or not isfinite(prior_ltcg_used)
            or sale_price_per_unit < 0 or prior_ltcg_used < 0):
        raise ValueError("sale price and prior_ltcg_used must be non-negative")
    if rule.effective_from and sale_date < rule.effective_from:
        raise ValueError("tax rule is not yet effective on sale_date")
    if rule.effective_to and sale_date > rule.effective_to:
        raise ValueError("tax rule has expired for sale_date")
    st = lt = gross = 0.0
    for lot in selections:
        gain = (sale_price_per_unit - lot.cost_per_unit) * lot.quantity
        gross += gain
        days = (sale_date - lot.acquisition_date).days
        if days < 0:
            raise ValueError("sale_date cannot precede acquisition date")
        if days < rule.holding_period_days:
            st += gain
        else:
            lt += gain
    # Losses reduce the same bucket in this simplified estimator; cross-head set-off,
    # carry-forward, grandfathering, account-specific rules and slab tax are not modelled.
    taxable_st = max(0.0, st)
    exemption_left = max(0.0, rule.annual_ltcg_exemption - prior_ltcg_used)
    taxable_lt = max(0.0, lt - exemption_left)
    base = taxable_st * rule.short_term_rate + taxable_lt * rule.long_term_rate
    surcharge = base * rule.surcharge_rate
    cess = (base + surcharge) * rule.cess_rate
    assumptions = (
        "Simplified per-asset-class rates; not a complete Indian income-tax computation.",
        "No grandfathering, slab-rate calculation, cross-head set-off, carry-forward, treaty, surcharge-cap or account-specific treatment.",
        "Annual exemption usage is supplied by caller and is not automatically aggregated across securities.",
        "Verify current law, acquisition date, instrument classification and taxpayer facts before use."
    )
    return TaxEstimate(gross, st, lt, taxable_st, taxable_lt, base, surcharge, cess,
                       base+surcharge+cess, rule.rule_id, assumptions)
