from __future__ import annotations

from pathlib import Path
import json
import numpy as np
import pandas as pd

ASSET_CLASSES = [
    "indian_equity",
    "international_equity",
    "indian_fixed_income",
    "international_fixed_income",
    "alternatives",
    "cash",
]

COUNTRIES = {
    "indian_equity": "IN",
    "international_equity": "GLOBAL",
    "indian_fixed_income": "IN",
    "international_fixed_income": "GLOBAL",
    "alternatives": "IN",
    "cash": "IN",
}

SECTORS = [
    "Financials", "Information Technology", "Healthcare", "Consumer",
    "Industrials", "Energy", "Materials", "Utilities",
]


def _normalise_rows(values: np.ndarray) -> np.ndarray:
    totals = values.sum(axis=1, keepdims=True)
    return values / np.maximum(totals, 1e-12)


def generate_securities(count: int, seed: int) -> pd.DataFrame:
    if count < 60:
        raise ValueError("At least 60 securities are required for a diversified universe.")
    rng = np.random.default_rng(seed)
    classes = np.array(ASSET_CLASSES)
    # Ensure every asset class has meaningful representation.
    asset_class = np.resize(classes, count)
    rng.shuffle(asset_class)
    rows = []
    for i, asset in enumerate(asset_class):
        is_equity = "equity" in asset
        rows.append({
            "security_id": f"SEC{i + 1:04d}",
            "ticker": f"WP{i + 1:04d}",
            "security_name": f"WealthPilot Synthetic Security {i + 1:04d}",
            "asset_class": asset,
            "country": COUNTRIES[asset],
            "sector": rng.choice(SECTORS) if is_equity else (
                "Sovereign" if "fixed_income" in asset else "Diversified"
            ),
            "currency": "INR" if COUNTRIES[asset] == "IN" else "USD",
            "annual_volatility": float(rng.uniform(0.08, 0.28) if is_equity else
                                        rng.uniform(0.005, 0.14)),
            "average_daily_volume_inr": float(rng.uniform(2e6, 5e9)),
            "bid_ask_spread_bps": float(rng.uniform(2, 35)),
            "is_synthetic": True,
        })
    return pd.DataFrame(rows)


def generate_market_data(config: dict, securities: pd.DataFrame, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed + 1)
    n_days = int(config["simulation"]["trading_days"])
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n_days)
    means = np.array([config["market"]["annual_return"][a] for a in ASSET_CLASSES])
    vols = np.array([config["market"]["annual_volatility"][a] for a in ASSET_CLASSES])
    corr = np.asarray(config["market"]["correlation"], dtype=float)
    cov = np.outer(vols, vols) * corr / 252.0
    daily_mean = means / 252.0
    asset_returns = rng.multivariate_normal(daily_mean, cov, size=n_days)
    asset_return_df = pd.DataFrame(asset_returns, columns=ASSET_CLASSES)
    asset_return_df.insert(0, "date", dates)

    # Security-specific residual noise around the asset-class factor.
    class_index = {name: i for i, name in enumerate(ASSET_CLASSES)}
    security_rows = []
    for security in securities.itertuples(index=False):
        idx = class_index[security.asset_class]
        residual_vol = max(security.annual_volatility * 0.45, 0.015) / np.sqrt(252)
        residual = rng.normal(0, residual_vol, n_days)
        returns = asset_returns[:, idx] + residual
        prices = 100.0 * np.cumprod(1.0 + returns)
        for date, price, ret in zip(dates, prices, returns):
            security_rows.append((date, security.security_id, float(price), float(ret)))
    prices_df = pd.DataFrame(
        security_rows, columns=["date", "security_id", "adjusted_close_inr", "daily_return"]
    )
    return asset_return_df, prices_df


def generate_portfolios(config: dict, securities: pd.DataFrame, seed: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed + 2)
    category_defs = config["risk_categories"]
    n = int(config["simulation"]["portfolio_count"])
    total_aum = float(config["simulation"]["total_aum_inr"])
    categories = np.concatenate([
        np.repeat(name, details["portfolio_count"])
        for name, details in category_defs.items()
    ])
    rng.shuffle(categories)
    # Lognormal balances are rescaled to exactly match stated aggregate AUM.
    balances = rng.lognormal(mean=np.log(total_aum / n), sigma=0.65, size=n)
    balances *= total_aum / balances.sum()

    portfolios = pd.DataFrame({
        "portfolio_id": [f"WP-{i + 1:06d}" for i in range(n)],
        "client_id": [f"CL-{i + 1:06d}" for i in range(n)],
        "risk_category": categories,
        "portfolio_value_inr": balances,
        "drift_band": [category_defs[c]["drift_band"] for c in categories],
        "tax_profile": rng.choice(["low", "medium", "high"], size=n, p=[0.25, 0.50, 0.25]),
        "liquidity_need_90d_inr": balances * rng.uniform(0.0, 0.12, size=n),
        "esg_restricted": rng.random(n) < 0.12,
        "single_security_restricted": rng.random(n) < 0.05,
        "created_at": pd.Timestamp.utcnow().isoformat(),
        "is_synthetic": True,
    })

    # Allocate each portfolio across its six asset classes, then securities within class.
    sec_by_class = {
        asset: securities.loc[securities.asset_class == asset, "security_id"].to_numpy()
        for asset in ASSET_CLASSES
    }
    holdings_rows = []
    tax_lot_rows = []
    for p in portfolios.itertuples(index=False):
        targets = category_defs[p.risk_category]["allocation"]
        class_weights = rng.dirichlet(np.full(6, 45.0))
        target_vector = np.array([targets[a] for a in ASSET_CLASSES], dtype=float)
        # Small realistic deviations from strategic weights at inception.
        actual_weights = _normalise_rows((target_vector * rng.lognormal(0, 0.035, 6))[None, :])[0]
        for asset, weight in zip(ASSET_CLASSES, actual_weights):
            candidates = sec_by_class[asset]
            count = min(len(candidates), int(rng.integers(2, min(6, len(candidates)) + 1)))
            chosen = rng.choice(candidates, size=count, replace=False)
            splits = rng.dirichlet(np.full(count, 2.5))
            for sec_id, split in zip(chosen, splits):
                market_value = float(p.portfolio_value_inr * weight * split)
                quantity = market_value / 100.0
                acquired_days_ago = int(rng.integers(20, 1400))
                cost_basis = market_value * float(rng.uniform(0.72, 1.12))
                lot_id = f"LOT-{p.portfolio_id}-{sec_id}"
                holdings_rows.append((
                    p.portfolio_id, sec_id, asset, quantity, market_value,
                    market_value / p.portfolio_value_inr, True
                ))
                tax_lot_rows.append((
                    lot_id, p.portfolio_id, sec_id, quantity, cost_basis,
                    (pd.Timestamp.today().normalize() - pd.to_timedelta(acquired_days_ago, unit="D")).date(),
                    True
                ))

    holdings = pd.DataFrame(holdings_rows, columns=[
        "portfolio_id", "security_id", "asset_class", "quantity",
        "market_value_inr", "portfolio_weight", "is_synthetic"
    ])
    tax_lots = pd.DataFrame(tax_lot_rows, columns=[
        "tax_lot_id", "portfolio_id", "security_id", "quantity",
        "cost_basis_inr", "acquisition_date", "is_synthetic"
    ])
    return portfolios, holdings, tax_lots


def write_dataset(config: dict, output_dir: str | Path, seed: int | None = None) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    seed = int(seed if seed is not None else config["project"]["random_seed"])

    securities = generate_securities(
        int(config["simulation"]["securities_count"]), seed
    )
    asset_returns, prices = generate_market_data(config, securities, seed)
    portfolios, holdings, tax_lots = generate_portfolios(config, securities, seed)

    datasets = {
        "securities.parquet": securities,
        "asset_class_returns.parquet": asset_returns,
        "market_prices.parquet": prices,
        "portfolios.parquet": portfolios,
        "holdings.parquet": holdings,
        "tax_lots.parquet": tax_lots,
    }
    manifest = {
        "project": "WealthPilot AI",
        "synthetic_data": True,
        "seed": seed,
        "portfolio_count": len(portfolios),
        "securities_count": len(securities),
        "trading_days": int(config["simulation"]["trading_days"]),
        "total_aum_inr": float(portfolios.portfolio_value_inr.sum()),
        "files": {},
        "market_data_notice": (
            "Synthetic correlated returns using configurable assumptions; not actual NSE/BSE "
            "historical prices and not investment advice."
        ),
    }
    for filename, frame in datasets.items():
        path = output / filename
        frame.to_parquet(path, index=False)
        manifest["files"][filename] = {
            "rows": int(len(frame)),
            "columns": list(frame.columns),
            "size_bytes": int(path.stat().st_size),
        }

    with (output / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    return manifest
