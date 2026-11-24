import numpy as np
from wealthpilot.config import load_config
from wealthpilot.data_generation import generate_securities, generate_market_data, generate_portfolios


def test_security_universe_has_six_asset_classes():
    config = load_config()
    securities = generate_securities(600, 42)
    assert len(securities) == 600
    assert securities.asset_class.nunique() == 6


def test_market_data_dimensions():
    config = load_config()
    securities = generate_securities(120, 42)
    asset_returns, prices = generate_market_data(config, securities, 42)
    assert len(asset_returns) == 252
    assert len(prices) == 252 * 120
    assert (prices.adjusted_close_inr > 0).all()


def test_portfolio_generation_is_reproducible_and_balanced():
    config = load_config()
    securities = generate_securities(120, 42)
    p1, h1, l1 = generate_portfolios(config, securities, 42)
    p2, h2, l2 = generate_portfolios(config, securities, 42)
    assert len(p1) == 50_000
    assert np.isclose(p1.portfolio_value_inr.sum(), 25_000 * 10_000_000)
    assert p1.portfolio_id.equals(p2.portfolio_id)
    assert h1.equals(h2)
    assert l1.equals(l2)
