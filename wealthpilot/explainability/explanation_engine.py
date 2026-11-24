"""Deterministic, evidence-grounded explanations for portfolio decisions.

This module explains supplied analytics. It does not calculate portfolio returns,
recommend securities, provide legal/tax advice, or execute orders.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from typing import Any, Mapping, Sequence
import hashlib
import json


class ExplanationError(ValueError):
    """Raised when an explanation request contains invalid input."""


def _number(value: Any, field: str, *, optional: bool = False) -> float | None:
    if value is None and optional:
        return None
    if isinstance(value, bool):
        raise ExplanationError(f"{field} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ExplanationError(f"{field} must be a finite number") from None
    if not isfinite(result):
        raise ExplanationError(f"{field} must be a finite number")
    return result


def _fmt_pct(value: float | None) -> str:
    return "not supplied" if value is None else f"{value * 100:.2f}%"


def _fmt_money(value: float | None, currency: str = "INR") -> str:
    if value is None:
        return "not supplied"
    return f"{currency} {value:,.2f}"


class ExplanationEngine:
    """Build client, advisor, and compliance explanations from structured evidence."""

    AUDIENCES = ("client", "advisor", "compliance")

    def explain(self, snapshot: Mapping[str, Any], audience: str = "client") -> dict[str, Any]:
        if audience not in self.AUDIENCES:
            raise ExplanationError(f"audience must be one of {', '.join(self.AUDIENCES)}")
        if not isinstance(snapshot, Mapping):
            raise ExplanationError("snapshot must be a mapping")

        portfolio_id = str(snapshot.get("portfolio_id", "UNSPECIFIED"))
        if not portfolio_id.strip():
            raise ExplanationError("portfolio_id cannot be blank")

        drift = snapshot.get("drift") or {}
        risk = snapshot.get("risk") or {}
        tax = snapshot.get("tax") or {}
        trigger = snapshot.get("trigger") or {}
        trades = snapshot.get("proposed_trades") or []
        if not isinstance(trades, Sequence) or isinstance(trades, (str, bytes)):
            raise ExplanationError("proposed_trades must be a list of trade mappings")

        drift_pct = _number(drift.get("max_drift_pct"), "drift.max_drift_pct", optional=True)
        threshold_pct = _number(drift.get("threshold_pct"), "drift.threshold_pct", optional=True)
        tracking_error = _number(risk.get("tracking_error_pct"), "risk.tracking_error_pct", optional=True)
        volatility = _number(risk.get("expected_volatility_pct"), "risk.expected_volatility_pct", optional=True)
        tax_cost = _number(tax.get("estimated_tax"), "tax.estimated_tax", optional=True)
        transaction_cost = _number(tax.get("estimated_transaction_cost"), "tax.estimated_transaction_cost", optional=True)
        currency = str(snapshot.get("currency", "INR"))

        if drift_pct is not None and drift_pct < 0:
            raise ExplanationError("drift.max_drift_pct cannot be negative")
        if threshold_pct is not None and threshold_pct < 0:
            raise ExplanationError("drift.threshold_pct cannot be negative")
        if tax_cost is not None and tax_cost < 0:
            raise ExplanationError("tax.estimated_tax cannot be negative")
        if transaction_cost is not None and transaction_cost < 0:
            raise ExplanationError("tax.estimated_transaction_cost cannot be negative")

        breach = (
            drift_pct is not None and threshold_pct is not None
            and drift_pct > threshold_pct
        )
        trigger_type = str(trigger.get("type", "not supplied"))
        trigger_reason = str(trigger.get("reason", "No trigger reason was supplied."))
        trade_lines = []
        evidence_trades = []
        for index, trade in enumerate(trades):
            if not isinstance(trade, Mapping):
                raise ExplanationError(f"proposed_trades[{index}] must be a mapping")
            symbol = str(trade.get("security", trade.get("asset", "Unspecified asset")))
            action = str(trade.get("action", "unspecified action")).upper()
            quantity = _number(trade.get("quantity"), f"proposed_trades[{index}].quantity", optional=True)
            value = _number(trade.get("estimated_value"), f"proposed_trades[{index}].estimated_value", optional=True)
            if quantity is not None and quantity < 0:
                raise ExplanationError(f"proposed_trades[{index}].quantity cannot be negative")
            trade_lines.append({
                "security": symbol, "action": action, "quantity": quantity,
                "estimated_value": value,
            })
            evidence_trades.append(
                f"{action} {quantity:g} units of {symbol}" if quantity is not None
                else f"{action} {symbol}"
            )

        drivers = []
        if drift_pct is not None:
            drivers.append(f"Maximum allocation drift is {_fmt_pct(drift_pct)}.")
        if threshold_pct is not None:
            drivers.append(f"The configured drift threshold is {_fmt_pct(threshold_pct)}.")
        if tracking_error is not None:
            drivers.append(f"Tracking error supplied by the risk model is {_fmt_pct(tracking_error)}.")
        if volatility is not None:
            drivers.append(f"Expected volatility supplied by the optimizer is {_fmt_pct(volatility)}.")
        if not drivers:
            drivers.append("No drift or risk measurements were supplied; quantitative conclusions are limited.")

        if audience == "client":
            headline = (
                "Your portfolio has moved beyond its supplied drift threshold."
                if breach else
                "Your portfolio review is based on the information currently available."
            )
            paragraphs = [
                headline,
                "The portfolio's allocation may differ from its intended mix. "
                + ("The supplied drift measurement is above the configured threshold."
                   if breach else "The supplied information does not establish a threshold breach."),
                ("Measured maximum drift: " + _fmt_pct(drift_pct) +
                 "; configured threshold: " + _fmt_pct(threshold_pct) + ".")
                if drift_pct is not None or threshold_pct is not None
                else "No drift or risk measurements were supplied; quantitative conclusions are limited.",
                "Any trades shown are proposals for review, not completed transactions."
                if trade_lines else "No proposed trades were included in this review.",
            ]
            if tax_cost is not None or transaction_cost is not None:
                paragraphs.append(
                    f"Estimated tax: {_fmt_money(tax_cost, currency)}; "
                    f"estimated transaction cost: {_fmt_money(transaction_cost, currency)}. "
                    "These are estimates based on supplied inputs."
                )
        elif audience == "advisor":
            headline = "Portfolio decision rationale and proposed actions"
            paragraphs = [
                f"Portfolio {portfolio_id}: trigger={trigger_type}; reason={trigger_reason}",
                *drivers,
                "Proposed actions: " + ("; ".join(evidence_trades) if evidence_trades else "none supplied"),
                f"Estimated tax={_fmt_money(tax_cost, currency)}; "
                f"estimated transaction cost={_fmt_money(transaction_cost, currency)}.",
            ]
        else:
            headline = "Compliance explanation and evidence record"
            paragraphs = [
                f"Portfolio identifier: {portfolio_id}.",
                f"Trigger type: {trigger_type}. Trigger reason: {trigger_reason}",
                *drivers,
                "Threshold breach evaluated only when both drift and threshold values are present: "
                + ("YES" if breach else "NO / NOT ESTABLISHED"),
                "Proposed trades are unexecuted recommendations supplied to this explanation layer: "
                + (json.dumps(trade_lines, sort_keys=True) if trade_lines else "none supplied"),
                f"Tax estimate={_fmt_money(tax_cost, currency)}; "
                f"transaction-cost estimate={_fmt_money(transaction_cost, currency)}.",
                "No independent tax-law validation, suitability determination, or order execution is performed here.",
            ]

        evidence = {
            "portfolio_id": portfolio_id,
            "drift": {"max_drift_pct": drift_pct, "threshold_pct": threshold_pct, "threshold_breach": breach},
            "risk": {"tracking_error_pct": tracking_error, "expected_volatility_pct": volatility},
            "tax": {"estimated_tax": tax_cost, "estimated_transaction_cost": transaction_cost, "currency": currency},
            "trigger": {"type": trigger_type, "reason": trigger_reason},
            "proposed_trades": trade_lines,
            "data_provenance": snapshot.get("data_provenance", "not supplied"),
            "human_review_required": bool(snapshot.get("human_review_required", True)),
        }
        canonical = json.dumps(evidence, sort_keys=True, separators=(",", ":"), default=str)
        evidence_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return {
            "schema_version": "1.0",
            "portfolio_id": portfolio_id,
            "audience": audience,
            "headline": headline,
            "explanation": paragraphs,
            "evidence": evidence,
            "evidence_sha256": evidence_hash,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "safety": {
                "trade_execution": False,
                "financial_advice": False,
                "human_review_required": evidence["human_review_required"],
                "limitations": [
                    "Explanations are limited to supplied inputs.",
                    "Tax and transaction-cost values are estimates, not legal or execution quotes.",
                    "This module does not run SHAP or LIME.",
                ],
            },
        }

    def explain_all(self, snapshot: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        """Return the same evidence explained for all supported audiences."""
        return {audience: self.explain(snapshot, audience) for audience in self.AUDIENCES}
