from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Iterable

@dataclass(frozen=True)
class TaxLot:
    lot_id: str
    security_id: str
    quantity: float
    acquisition_date: date
    cost_per_unit: float
    available_quantity: float | None = None

    def __post_init__(self):
        if not self.lot_id or not self.security_id:
            raise ValueError("lot_id and security_id are required")
        if (not isfinite(self.quantity) or not isfinite(self.cost_per_unit)
                or self.quantity <= 0 or self.cost_per_unit < 0):
            raise ValueError("quantity must be positive and cost_per_unit non-negative")
        if self.available_quantity is not None and (not isfinite(self.available_quantity) or not (0 <= self.available_quantity <= self.quantity)):
            raise ValueError("available_quantity must be between zero and quantity")

@dataclass(frozen=True)
class LotSelection:
    lot_id: str
    quantity: float
    cost_per_unit: float
    acquisition_date: date
    estimated_gain_per_unit: float

def select_tax_lots(
    lots: Iterable[TaxLot], quantity_to_sell: float, sale_price_per_unit: float,
    as_of: date, strategy: str = "minimize_gain"
) -> list[LotSelection]:
    """Select available units. Strategies: minimize_gain, maximize_loss, fifo, lifo."""
    if (not isfinite(quantity_to_sell) or not isfinite(sale_price_per_unit)
            or quantity_to_sell < 0 or sale_price_per_unit < 0):
        raise ValueError("sale quantity and price must be non-negative")
    if strategy not in {"minimize_gain", "maximize_loss", "fifo", "lifo"}:
        raise ValueError(f"unsupported lot-selection strategy: {strategy}")
    rows = list(lots)
    if any(l.acquisition_date > as_of for l in rows):
        raise ValueError("as_of cannot precede a lot acquisition date")
    if len({l.lot_id for l in rows}) != len(rows):
        raise ValueError("lot_id values must be unique")
    if rows and len({l.security_id for l in rows}) != 1:
        raise ValueError("all lots must belong to the same security")
    if strategy == "minimize_gain":
        rows.sort(key=lambda l: (sale_price_per_unit - l.cost_per_unit, l.acquisition_date))
    elif strategy == "maximize_loss":
        rows.sort(key=lambda l: (sale_price_per_unit - l.cost_per_unit, l.acquisition_date))
    elif strategy == "fifo":
        rows.sort(key=lambda l: l.acquisition_date)
    else:
        rows.sort(key=lambda l: l.acquisition_date, reverse=True)
    remaining = quantity_to_sell
    selected = []
    for lot in rows:
        available = lot.quantity if lot.available_quantity is None else lot.available_quantity
        take = min(remaining, available)
        if take > 0:
            selected.append(LotSelection(lot.lot_id, take, lot.cost_per_unit,
                                         lot.acquisition_date, sale_price_per_unit-lot.cost_per_unit))
            remaining -= take
        if remaining <= 1e-10:
            break
    if remaining > 1e-8:
        raise ValueError(f"insufficient available lot quantity; short by {remaining:.8f}")
    return selected
