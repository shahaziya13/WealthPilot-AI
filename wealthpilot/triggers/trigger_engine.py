from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json

import pandas as pd


@dataclass(frozen=True)
class TriggerConfig:
    cooldown_hours: int = 24
    calendar_review_day: int = 1
    event_severity_minimum: str = "HIGH"
    max_events_per_portfolio: int = 10


SEVERITY_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def _first_existing(df: pd.DataFrame, candidates: list[str]) -> str | None:
    return next((c for c in candidates if c in df.columns), None)


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


class TriggerEngine:
    """Creates deterministic, auditable rebalancing review triggers.

    This engine raises review recommendations; it never places trades.
    """

    def __init__(self, config: TriggerConfig | None = None):
        self.config = config or TriggerConfig()

    @staticmethod
    def _normalise_time(value: Any) -> pd.Timestamp:
        ts = pd.Timestamp(value)
        if ts.tzinfo is None:
            return ts.tz_localize("UTC")
        return ts.tz_convert("UTC")

    def _trigger_id(self, portfolio_id: Any, trigger_type: str,
                    trigger_date: Any, reason: str) -> str:
        raw = f"{portfolio_id}|{trigger_type}|{pd.Timestamp(trigger_date).date()}|{reason}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]

    def threshold_triggers(self, drift: pd.DataFrame,
                           as_of: Any | None = None) -> pd.DataFrame:
        if drift.empty:
            return pd.DataFrame()
        pid = _first_existing(drift, ["portfolio_id"])
        breach = _first_existing(drift, ["requires_attention", "is_breach", "breach"])
        ratio = _first_existing(drift, ["breach_ratio", "threshold_ratio"])
        max_drift = _first_existing(drift, ["max_abs_drift", "max_absolute_drift", "max_drift"])
        if pid is None:
            raise ValueError("Day 2 drift output must contain portfolio_id")
        if breach:
            mask = drift[breach].map(_to_bool)
        elif ratio:
            mask = pd.to_numeric(drift[ratio], errors="coerce") > 1.0
        elif max_drift:
            threshold = _first_existing(drift, ["threshold", "drift_threshold", "applicable_threshold"])
            if threshold is None:
                raise ValueError("Cannot determine threshold breaches: threshold column missing")
            mask = pd.to_numeric(drift[max_drift], errors="coerce") > pd.to_numeric(drift[threshold], errors="coerce")
        else:
            raise ValueError("Drift output needs requires_attention, breach_ratio, or max_abs_drift + threshold")

        rows = drift.loc[mask].copy()
        if rows.empty:
            return pd.DataFrame()
        now = self._normalise_time(as_of or datetime.now(timezone.utc))
        severity_col = _first_existing(rows, ["severity", "breach_severity"])
        priority_col = _first_existing(rows, ["priority_score", "priority"])
        reason_col = _first_existing(rows, ["largest_drift_asset_class", "largest_drift_class"])
        out = pd.DataFrame({
            "portfolio_id": rows[pid].astype(str),
            "trigger_type": "THRESHOLD",
            "triggered_at": now,
            "severity": rows[severity_col].astype(str).str.upper() if severity_col else "HIGH",
            "priority_score": pd.to_numeric(rows[priority_col], errors="coerce").fillna(0.0) if priority_col else 70.0,
            "reason": rows[reason_col].astype(str) if reason_col else "Drift threshold breached",
            "source": "day02_drift_monitor",
            "requires_human_review": True,
            "is_synthetic": True,
        })
        out["trigger_id"] = [
            self._trigger_id(p, "THRESHOLD", now, r)
            for p, r in zip(out["portfolio_id"], out["reason"])
        ]
        return out

    def calendar_triggers(self, portfolios: pd.DataFrame, as_of: Any | None = None,
                          review_day: int | None = None) -> pd.DataFrame:
        if portfolios.empty or "portfolio_id" not in portfolios:
            return pd.DataFrame()
        now = self._normalise_time(as_of or datetime.now(timezone.utc))
        day = review_day or self.config.calendar_review_day
        date_col = _first_existing(portfolios, ["next_review_date", "rebalance_date", "next_rebalance_date"])
        if date_col:
            due = pd.to_datetime(portfolios[date_col], errors="coerce", utc=True) <= now
        else:
            due = pd.Series(now.day == day, index=portfolios.index)
        rows = portfolios.loc[due].copy()
        if rows.empty:
            return pd.DataFrame()
        risk_col = _first_existing(rows, ["risk_category"])
        out = pd.DataFrame({
            "portfolio_id": rows["portfolio_id"].astype(str),
            "trigger_type": "CALENDAR",
            "triggered_at": now,
            "severity": "LOW",
            "priority_score": 25.0,
            "reason": (rows[risk_col].astype(str) + " scheduled portfolio review") if risk_col else "Scheduled portfolio review",
            "source": "calendar_schedule",
            "requires_human_review": True,
            "is_synthetic": True,
        })
        out["trigger_id"] = [
            self._trigger_id(p, "CALENDAR", now, r)
            for p, r in zip(out["portfolio_id"], out["reason"])
        ]
        return out

    def event_triggers(self, events: pd.DataFrame) -> pd.DataFrame:
        if events.empty:
            return pd.DataFrame()
        required = {"portfolio_id", "event_type"}
        missing = required - set(events.columns)
        if missing:
            raise ValueError(f"Event feed missing required columns: {sorted(missing)}")
        rows = events.copy()
        severity_col = _first_existing(rows, ["severity", "event_severity"])
        if severity_col is None:
            rows["severity"] = "HIGH"
            severity_col = "severity"
        rows[severity_col] = rows[severity_col].fillna("MEDIUM").astype(str).str.upper()
        minimum = SEVERITY_ORDER[self.config.event_severity_minimum.upper()]
        rows = rows[rows[severity_col].map(lambda x: SEVERITY_ORDER.get(x, 0)) >= minimum]
        if rows.empty:
            return pd.DataFrame()
        time_col = _first_existing(rows, ["event_time", "occurred_at", "timestamp"])
        times = pd.to_datetime(rows[time_col], errors="coerce", utc=True) if time_col else pd.Series(pd.Timestamp.now(tz="UTC"), index=rows.index)
        reason_col = _first_existing(rows, ["description", "reason"])
        descriptions = rows[reason_col].fillna(rows["event_type"]).astype(str) if reason_col else rows["event_type"].astype(str)
        out = pd.DataFrame({
            "portfolio_id": rows["portfolio_id"].astype(str),
            "trigger_type": "EVENT",
            "triggered_at": times,
            "severity": rows[severity_col],
            "priority_score": rows[severity_col].map({"LOW": 10, "MEDIUM": 40, "HIGH": 75, "CRITICAL": 100}).fillna(40),
            "reason": descriptions,
            "source": "event_feed",
            "requires_human_review": True,
            "is_synthetic": rows["is_synthetic"].map(_to_bool) if "is_synthetic" in rows else True,
        })
        out["trigger_id"] = [
            self._trigger_id(p, "EVENT", t, r)
            for p, t, r in zip(out["portfolio_id"], out["triggered_at"], out["reason"])
        ]
        return out

    def combine(self, *trigger_frames: pd.DataFrame,
                existing_log: pd.DataFrame | None = None,
                as_of: Any | None = None) -> pd.DataFrame:
        frames = [f for f in trigger_frames if f is not None and not f.empty]
        if not frames:
            return pd.DataFrame(columns=[
                "trigger_id", "portfolio_id", "trigger_type", "triggered_at",
                "severity", "priority_score", "reason", "source",
                "requires_human_review", "is_synthetic"
            ])
        combined = pd.concat(frames, ignore_index=True)
        combined["triggered_at"] = pd.to_datetime(combined["triggered_at"], utc=True)
        combined = combined.sort_values(
            ["priority_score", "triggered_at"], ascending=[False, False]
        )
        # Collapse same portfolio + trigger type + reason on the same date.
        combined = combined.drop_duplicates(subset=["trigger_id"], keep="first")
        now = self._normalise_time(as_of or datetime.now(timezone.utc))
        if existing_log is not None and not existing_log.empty:
            prior = existing_log.copy()
            if "triggered_at" in prior:
                prior["triggered_at"] = pd.to_datetime(prior["triggered_at"], utc=True, errors="coerce")
                cutoff = now - pd.Timedelta(self.config.cooldown_hours, unit="hours")
                prior = prior[prior["triggered_at"] >= cutoff]
            if "trigger_id" in prior:
                combined = combined[~combined["trigger_id"].isin(prior["trigger_id"].astype(str))]
            if "portfolio_id" in prior and "trigger_type" in prior:
                recent_keys = set(zip(prior["portfolio_id"].astype(str), prior["trigger_type"].astype(str)))
                combined = combined[
                    ~combined.apply(lambda r: (str(r["portfolio_id"]), str(r["trigger_type"])) in recent_keys, axis=1)
                ]
        combined = combined.sort_values(
            ["priority_score", "triggered_at"], ascending=[False, False]
        ).reset_index(drop=True)
        combined.insert(0, "queue_rank", range(1, len(combined) + 1))
        return combined
