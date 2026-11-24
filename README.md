# WealthPilot AI — Day 1 Foundation

> Synthetic research and simulation platform. Not connected to a broker, custody platform, exchange, or real client accounts.

## Day 1 scope

- Configuration-driven simulation for 50,000 portfolios and INR 25,000 crore aggregate AUM.
- Five risk categories and six strategic asset classes.
- 600 synthetic securities.
- 252 business-day synthetic market-price history.
- Portfolio, holdings, tax-lot, security-master and market-data datasets.
- Reproducible generation with a fixed random seed.
- Automated data-integrity validation and starter tests.

## Important data provenance

All generated clients, securities, tax lots, prices and returns are synthetic. Market return assumptions and correlations are configuration parameters, not claims of calibration to actual NSE/BSE historical observations. A later research milestone should ingest licensed or otherwise permitted historical data, document its source and date range, and calibrate assumptions transparently.

## Windows setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
```

If PowerShell blocks activation, run this once in the current terminal:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Generate Day 1 data

```powershell
python scripts/generate_data.py
```

Output files are written to `data/generated/` in Parquet format with a `manifest.json`.

## Run tests

```powershell
pytest
```

## Dataset inventory

| Dataset | Description |
|---|---|
| `portfolios.parquet` | Client-level portfolio profile and AUM |
| `holdings.parquet` | Security-level holdings and market values |
| `tax_lots.parquet` | Acquisition date and cost-basis records |
| `securities.parquet` | Synthetic security master |
| `market_prices.parquet` | Daily synthetic security prices and returns |
| `asset_class_returns.parquet` | Correlated asset-class return series |
| `manifest.json` | Dataset provenance, dimensions and file sizes |

## Day 1 acceptance criteria

- Exactly 50,000 portfolios across five risk categories.
- Aggregate portfolio value equals INR 25,000 crore.
- At least 500 securities.
- 252 business-day observations per security.
- Six asset classes represented.
- Positive portfolio values, holdings values and prices.
- Every holding maps to a known portfolio and security.
- Reproducible generation from the same seed.

## Next milestone

Day 2 implements vectorised drift calculations, category-specific thresholds, prioritised monitoring queues and a 50,000-portfolio scan benchmark.
