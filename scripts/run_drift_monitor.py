import argparse, json
from pathlib import Path
import pandas as pd
import yaml
from wealthpilot.monitoring import DriftMonitor, ThresholdManager
from wealthpilot.monitoring.drift_calculator import ASSET_CLASSES

# Six-class strategic allocations used by the Day 1 WealthPilot simulation.
TARGET_ALLOCATIONS = {
    "Ultra-Conservative": dict(zip(ASSET_CLASSES, [.10, .05, .45, .15, .10, .15])),
    "Conservative": dict(zip(ASSET_CLASSES, [.20, .10, .32, .13, .12, .13])),
    "Balanced": dict(zip(ASSET_CLASSES, [.34, .16, .20, .10, .12, .08])),
    "Aggressive": dict(zip(ASSET_CLASSES, [.48, .22, .10, .05, .10, .05])),
    "Ultra-Aggressive": dict(zip(ASSET_CLASSES, [.58, .27, .03, .02, .07, .03])),
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/generated")
    parser.add_argument("--output-dir", default="reports/day02")
    args = parser.parse_args()
    data, out = Path(args.data_dir), Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    portfolios = pd.read_parquet(data / "portfolios.parquet")
    holdings = pd.read_parquet(data / "holdings.parquet")
    returns = pd.read_parquet(data / "asset_class_returns.parquet")
    allocations = TARGET_ALLOCATIONS
    covariance = returns[list(ASSET_CLASSES)].cov().to_numpy()
    report = DriftMonitor(threshold_manager=ThresholdManager()).run(portfolios, holdings, allocations, covariance)
    report["summary"].to_parquet(out / "portfolio_drift.parquet", index=False)
    report["breach_queue"].to_csv(out / "priority_breach_queue.csv", index=False)
    report["asset_class_drift"].to_parquet(out / "asset_class_drift.parquet", index=False)
    manifest = {"portfolio_count": report["portfolio_count"], "breach_count": report["breach_count"],
        "scan_duration_seconds": report["scan_duration_seconds"], "data_is_synthetic": True,
        "target_allocations_source": "Day 1 six-asset-class strategic allocations",
        "covariance_source": "sample covariance of synthetic asset_class_returns.parquet",
        "outputs": ["portfolio_drift.parquet", "priority_breach_queue.csv", "asset_class_drift.parquet"]}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))

if __name__ == "__main__": main()
