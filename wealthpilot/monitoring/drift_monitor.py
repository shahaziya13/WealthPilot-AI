import time
import pandas as pd
from .drift_calculator import DriftCalculator
from .threshold_manager import ThresholdManager

class DriftMonitor:
    """Run batch drift scans and return a severity-ranked breach queue."""
    def __init__(self, calculator=None, threshold_manager=None):
        self.calculator = calculator or DriftCalculator()
        self.threshold_manager = threshold_manager or ThresholdManager()

    def run(self, portfolios, holdings, target_allocations, covariance=None):
        started = time.perf_counter()
        result = self.calculator.calculate(portfolios, holdings, target_allocations, covariance=covariance)
        thresholds = self.threshold_manager.thresholds_for(portfolios).rename_axis("portfolio_id")
        summary = result.summary.set_index("portfolio_id").join(thresholds)
        summary["breach_ratio"] = summary.max_absolute_drift / summary.threshold
        summary["requires_attention"] = summary.breach_ratio > 1.0
        summary["severity"] = pd.cut(summary.breach_ratio,
            bins=[-float("inf"), .75, 1.0, 1.5, 2.0, float("inf")],
            labels=["LOW", "WATCH", "ELEVATED", "HIGH", "CRITICAL"], right=True).astype("object")
        summary["priority_score"] = summary.breach_ratio.clip(lower=0) + summary.sum_absolute_drift
        summary = summary.sort_values(["requires_attention", "priority_score", "sum_absolute_drift"],
            ascending=[False, False, False], kind="stable").reset_index()
        duration = time.perf_counter() - started
        summary["scan_duration_seconds"] = duration
        queue = summary.loc[summary.requires_attention].copy()
        return {"summary": summary, "breach_queue": queue, "asset_class_drift": result.by_asset_class,
                "scan_duration_seconds": float(duration), "portfolio_count": int(len(summary)),
                "breach_count": int(len(queue))}
