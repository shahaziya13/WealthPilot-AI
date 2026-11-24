from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import numpy as np
import pandas as pd

ASSET_CLASSES = ("indian_equity", "international_equity", "indian_fixed_income", "international_fixed_income", "alternatives", "cash")

@dataclass
class DriftResult:
    summary: pd.DataFrame
    by_asset_class: pd.DataFrame

class DriftCalculator:
    """Vectorised drift metrics. Drift is actual weight minus target weight."""
    def __init__(self, asset_classes: Iterable[str] = ASSET_CLASSES):
        self.asset_classes = tuple(asset_classes)
        if not self.asset_classes or len(set(self.asset_classes)) != len(self.asset_classes):
            raise ValueError("asset_classes must be non-empty and unique")

    def calculate(self, portfolios, holdings, target_allocations, covariance=None, periods_per_year=252):
        self._validate_inputs(portfolios, holdings, target_allocations, covariance)
        p = portfolios.set_index("portfolio_id")
        actual = (holdings.groupby(["portfolio_id", "asset_class"], observed=True)["market_value_inr"]
                  .sum().unstack(fill_value=0).reindex(columns=self.asset_classes, fill_value=0))
        actual = actual.div(p["portfolio_value_inr"].astype(float), axis=0).fillna(0.0)
        target_map = {cat: {a: float(vals.get(a, 0.0)) for a in self.asset_classes}
                      for cat, vals in target_allocations.items()}
        target = pd.DataFrame([target_map[cat] for cat in p.loc[actual.index, "risk_category"]],
                              index=actual.index, columns=self.asset_classes, dtype=float)
        drift = actual - target
        abs_drift = drift.abs()
        sad = abs_drift.sum(axis=1)
        rmsd = np.sqrt(drift.pow(2).mean(axis=1))
        max_abs = abs_drift.max(axis=1)
        max_asset = abs_drift.idxmax(axis=1)
        if covariance is None:
            predicted_te = pd.Series(np.nan, index=drift.index, dtype=float)
        else:
            cov = np.asarray(covariance, dtype=float)
            variance = np.einsum("ij,jk,ik->i", drift.to_numpy(), cov, drift.to_numpy())
            predicted_te = pd.Series(np.sqrt(np.maximum(variance, 0.0)) * np.sqrt(periods_per_year), index=drift.index)
        summary = pd.DataFrame({"portfolio_id": drift.index, "sum_absolute_drift": sad.values,
            "rms_drift": rmsd.values, "max_absolute_drift": max_abs.values,
            "largest_drift_asset_class": max_asset.values, "predicted_tracking_error": predicted_te.values})
        detail = drift.rename_axis("portfolio_id").reset_index().melt(id_vars="portfolio_id", var_name="asset_class", value_name="drift")
        detail["actual_weight"] = actual.rename_axis("portfolio_id").reset_index().melt(id_vars="portfolio_id", var_name="asset_class", value_name="actual_weight")["actual_weight"]
        detail["target_weight"] = target.rename_axis("portfolio_id").reset_index().melt(id_vars="portfolio_id", var_name="asset_class", value_name="target_weight")["target_weight"]
        detail["absolute_drift"] = detail["drift"].abs()
        return DriftResult(summary.reset_index(drop=True), detail)

    def _validate_inputs(self, portfolios, holdings, target_allocations, covariance):
        pr = {"portfolio_id", "risk_category", "portfolio_value_inr"}
        hr = {"portfolio_id", "asset_class", "market_value_inr"}
        if missing := pr.difference(portfolios.columns): raise ValueError(f"Missing portfolio columns: {sorted(missing)}")
        if missing := hr.difference(holdings.columns): raise ValueError(f"Missing holdings columns: {sorted(missing)}")
        if portfolios.portfolio_id.duplicated().any(): raise ValueError("portfolio_id must be unique")
        if (portfolios.portfolio_value_inr <= 0).any(): raise ValueError("portfolio values must be positive")
        unknown = set(holdings.asset_class.dropna().unique()) - set(self.asset_classes)
        if unknown: raise ValueError(f"Unsupported asset classes: {sorted(unknown)}")
        if not holdings.portfolio_id.isin(portfolios.portfolio_id).all(): raise ValueError("Holdings contain unknown portfolio IDs")
        if (holdings.market_value_inr < 0).any(): raise ValueError("Holdings market values cannot be negative")
        for category in portfolios.risk_category.unique():
            if category not in target_allocations: raise ValueError(f"Missing target allocation for {category}")
            weights = [float(target_allocations[category].get(a, 0.0)) for a in self.asset_classes]
            if any(w < 0 for w in weights) or not np.isclose(sum(weights), 1.0, atol=1e-6):
                raise ValueError(f"Target weights for {category} must be non-negative and sum to 1")
        if covariance is not None:
            cov = np.asarray(covariance, dtype=float); n = len(self.asset_classes)
            if cov.shape != (n, n) or not np.isfinite(cov).all(): raise ValueError(f"covariance must be a finite {n}x{n} matrix")
            if not np.allclose(cov, cov.T, atol=1e-10): raise ValueError("covariance matrix must be symmetric")
            if np.linalg.eigvalsh(cov).min() < -1e-10: raise ValueError("covariance matrix must be positive semidefinite")
