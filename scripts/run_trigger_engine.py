from __future__ import annotations
import json
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wealthpilot.triggers import TriggerEngine, TriggerConfig


def read_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required input not found: {path}")
    return pd.read_parquet(path)


def locate_portfolios() -> Path:
    candidates = [
        ROOT / "data" / "processed" / "portfolios.parquet",
        ROOT / "data" / "portfolios.parquet",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    for candidate in (ROOT / "data").rglob("*.parquet"):
        try:
            sample = pd.read_parquet(candidate)
            if {"portfolio_id", "risk_category"}.issubset(sample.columns):
                return candidate
        except Exception:
            continue
    raise FileNotFoundError("Could not locate Day 1 portfolios Parquet (portfolio_id + risk_category).")


def main():
    import time
    start_time = time.perf_counter()
    drift_path = ROOT / "reports" / "day02" / "portfolio_drift.parquet"
    portfolio_path = locate_portfolios()
    drift = read_parquet(drift_path)
    portfolios = read_parquet(portfolio_path)
    event_path = ROOT / "data" / "events" / "market_events.csv"
    event_path.parent.mkdir(parents=True, exist_ok=True)
    if event_path.exists():
        events = pd.read_csv(event_path)
    else:
        # Clearly labelled synthetic event examples for pipeline validation.
        sample_ids = portfolios["portfolio_id"].astype(str).head(5).tolist()
        events = pd.DataFrame([
            {"portfolio_id": pid, "event_type": "MARKET_VOLATILITY",
             "severity": "HIGH", "description": "Synthetic volatility alert for pipeline validation",
             "event_time": pd.Timestamp.now(tz="UTC").isoformat(), "is_synthetic": True}
            for pid in sample_ids
        ])
        events.to_csv(event_path, index=False)

    engine = TriggerEngine(TriggerConfig())
    threshold = engine.threshold_triggers(drift)
    calendar = engine.calendar_triggers(portfolios)
    event = engine.event_triggers(events)
    out_dir = ROOT / "reports" / "day03"
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "trigger_log.csv"
    existing = pd.read_csv(log_path) if log_path.exists() else None
    queue = engine.combine(threshold, calendar, event, existing_log=existing)
    # Append newly emitted triggers to the durable audit log.
    if not queue.empty:
        if log_path.exists():
            old = pd.read_csv(log_path)
            log = pd.concat([old, queue], ignore_index=True).drop_duplicates("trigger_id", keep="first")
        else:
            log = queue.copy()
        log.to_csv(log_path, index=False)
    queue_path = out_dir / "trigger_queue.csv"
    queue.to_csv(queue_path, index=False)
    summary = {
        "portfolio_count": int(portfolios["portfolio_id"].nunique()),
        "threshold_trigger_count": int(len(threshold)),
        "calendar_trigger_count": int(len(calendar)),
        "event_trigger_count": int(len(event)),
        "new_trigger_count": int(len(queue)),
        "scan_duration_seconds": round(time.perf_counter() - start_time, 4),
        "event_input_is_synthetic": bool(events["is_synthetic"].map(_to_bool).all()) if "is_synthetic" in events else True,
        "outputs": ["trigger_queue.csv", "trigger_log.csv"],
        "safety": "Review recommendations only; no trades are executed."
    }
    import time
    # duration includes pipeline; measured by wall clock around this run below in later version
    (out_dir / "manifest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


def _to_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


if __name__ == "__main__":
    main()
