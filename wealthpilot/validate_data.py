from pathlib import Path
import json
import numpy as np
import pandas as pd


def validate_generated_data(data_dir: str | Path) -> dict:
    root = Path(data_dir)
    required = [
        "portfolios.parquet", "holdings.parquet", "tax_lots.parquet",
        "securities.parquet", "market_prices.parquet", "asset_class_returns.parquet",
        "manifest.json",
    ]
    missing = [name for name in required if not (root / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing generated datasets: {missing}")

    portfolios = pd.read_parquet(root / "portfolios.parquet")
    holdings = pd.read_parquet(root / "holdings.parquet")
    securities = pd.read_parquet(root / "securities.parquet")
    prices = pd.read_parquet(root / "market_prices.parquet")
    lots = pd.read_parquet(root / "tax_lots.parquet")

    checks = {
        "portfolio_count": len(portfolios) == 50_000,
        "security_count": len(securities) >= 500,
        "portfolio_ids_unique": portfolios.portfolio_id.is_unique,
        "portfolio_values_positive": bool((portfolios.portfolio_value_inr > 0).all()),
        "holdings_values_positive": bool((holdings.market_value_inr > 0).all()),
        "holdings_portfolios_known": bool(holdings.portfolio_id.isin(portfolios.portfolio_id).all()),
        "holdings_securities_known": bool(holdings.security_id.isin(securities.security_id).all()),
        "tax_lots_nonnegative_basis": bool((lots.cost_basis_inr >= 0).all()),
        "prices_positive": bool((prices.adjusted_close_inr > 0).all()),
        "five_risk_categories": portfolios.risk_category.nunique() == 5,
        "portfolio_aum_matches": np.isclose(
            portfolios.portfolio_value_inr.sum(), 25_000 * 10_000_000, rtol=1e-9
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    report = {
        "passed": not failed,
        "checks": checks,
        "failed_checks": failed,
        "rows": {
            "portfolios": len(portfolios),
            "holdings": len(holdings),
            "tax_lots": len(lots),
            "securities": len(securities),
            "market_prices": len(prices),
        },
        "aum_inr": float(portfolios.portfolio_value_inr.sum()),
    }
    if failed:
        raise AssertionError(f"Data validation failed: {failed}")
    return report
