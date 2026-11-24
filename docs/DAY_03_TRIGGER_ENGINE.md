# Day 03 — Event-Driven Rebalancing Trigger Engine

## Scope
Creates human-review recommendations from threshold, calendar, and event signals.
It does not calculate trades, execute orders, or provide investment advice.

## Trigger types
- `THRESHOLD`: imports Day 2 portfolio drift breaches.
- `CALENDAR`: uses `next_review_date`, `rebalance_date`, or `next_rebalance_date` when present; otherwise runs the monthly review on the configured day.
- `EVENT`: reads `data/events/market_events.csv` and filters by minimum severity.

## Controls
- Stable SHA-256-derived trigger IDs.
- Duplicate suppression.
- Configurable cooldown (default 24 hours) against recent trigger-log entries for the same portfolio and trigger type.
- Priority-ranked queue.
- Human review flag on every trigger.
- Synthetic-data provenance flag.

## Input
- `reports/day02/portfolio_drift.parquet`
- Day 1 portfolios Parquet containing `portfolio_id` and `risk_category`
- Optional `data/events/market_events.csv`

If no event file exists, the runner creates five clearly labelled synthetic validation events.

## Outputs
- `reports/day03/trigger_queue.csv`
- `reports/day03/trigger_log.csv`
- `reports/day03/manifest.json`

## Run
```powershell
python scripts/run_trigger_engine.py
```
