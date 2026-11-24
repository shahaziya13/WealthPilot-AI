from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
import pandas as pd

DEFAULT_CATEGORY_BANDS = {
    "Ultra-Conservative": 0.020, "Conservative": 0.025, "Balanced": 0.030,
    "Aggressive": 0.040, "Ultra-Aggressive": 0.050,
}

@dataclass(frozen=True)
class ThresholdManager:
    category_bands: Mapping[str, float] | None = None

    def __post_init__(self):
        if self.category_bands is None:
            object.__setattr__(self, "category_bands", DEFAULT_CATEGORY_BANDS.copy())
        for category, band in self.category_bands.items():
            if not 0 < float(band) <= 1:
                raise ValueError(f"Invalid drift band for {category}: {band}")

    def thresholds_for(self, portfolios: pd.DataFrame) -> pd.Series:
        required = {"portfolio_id", "risk_category"}
        missing = required.difference(portfolios.columns)
        if missing:
            raise ValueError(f"Missing portfolio columns: {sorted(missing)}")
        category = portfolios["risk_category"].map(self.category_bands)
        if category.isna().any():
            unknown = sorted(portfolios.loc[category.isna(), "risk_category"].dropna().unique())
            raise ValueError(f"Unknown risk categories: {unknown}")
        if "drift_band" in portfolios.columns:
            overlay = pd.to_numeric(portfolios["drift_band"], errors="coerce")
            valid = overlay.notna() & overlay.gt(0) & overlay.le(1)
            category = overlay.where(valid, category)
        return pd.Series(category.astype(float).to_numpy(), index=portfolios["portfolio_id"], name="threshold")
