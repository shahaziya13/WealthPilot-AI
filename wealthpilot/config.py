from pathlib import Path
from typing import Any
import yaml


def load_config(path: str | Path = "config/settings.yaml") -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    simulation = config["simulation"]
    if simulation["portfolio_count"] != sum(
        item["portfolio_count"] for item in config["risk_categories"].values()
    ):
        raise ValueError("Risk-category portfolio counts must sum to portfolio_count.")

    if len(config["risk_categories"]) != 5:
        raise ValueError("Exactly five risk categories are required.")

    for category, details in config["risk_categories"].items():
        weights = details["allocation"]
        if len(weights) != 6:
            raise ValueError(f"{category} must define six asset classes.")
        if abs(sum(weights.values()) - 1.0) > 1e-9:
            raise ValueError(f"{category} target allocation must sum to 1.0.")

    classes = list(config["market"]["annual_return"])
    corr = config["market"]["correlation"]
    if len(corr) != len(classes) or any(len(row) != len(classes) for row in corr):
        raise ValueError("Correlation matrix dimensions do not match asset classes.")
