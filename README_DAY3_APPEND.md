## Day 3 — Event-Driven Trigger Engine

Run `python scripts/run_trigger_engine.py` after completing Day 2. The engine creates
threshold, calendar, and event-driven review triggers, suppresses duplicate/recent
triggers, and writes a ranked queue plus append-only-style CSV audit log under
`reports/day03/`. It recommends human review only and never executes trades.
