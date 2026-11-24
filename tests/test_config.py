from wealthpilot.config import load_config, validate_config


def test_default_config_is_valid():
    config = load_config()
    validate_config(config)


def test_portfolio_counts_sum_to_50000():
    config = load_config()
    assert sum(x["portfolio_count"] for x in config["risk_categories"].values()) == 50_000


def test_all_target_allocations_sum_to_one():
    config = load_config()
    for details in config["risk_categories"].values():
        assert abs(sum(details["allocation"].values()) - 1.0) < 1e-9
