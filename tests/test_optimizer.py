import numpy as np
import pandas as pd
import pytest
pytest.importorskip("cvxpy")
from wealthpilot.optimization import PortfolioOptimizer, OptimizationConfig

@pytest.fixture
def data():
    names=["Equity","Debt","Gold"]
    current=pd.Series([.5,.3,.2],index=names)
    expected=pd.Series([.08,.04,.03],index=names)
    cov=pd.DataFrame([[.04,.002,.001],[.002,.01,.001],[.001,.001,.006]],index=names,columns=names)
    return current,expected,cov

def test_valid_solution(data):
    r=PortfolioOptimizer().optimize(*data)
    assert all(r.validation.values())
    assert r.weights.sum()==pytest.approx(1,abs=1e-5)

def test_turnover_constraint(data):
    r=PortfolioOptimizer(OptimizationConfig(max_turnover=.05)).optimize(*data)
    assert r.turnover<=.05001

def test_asset_upper_bound(data):
    c,e,v=data
    upper=pd.Series({"Equity":.45,"Debt":.6,"Gold":.4})
    r=PortfolioOptimizer().optimize(c,e,v,asset_max_weights=upper)
    assert r.weights["Equity"]<=.45001

def test_infeasible_bounds(data):
    c,e,v=data
    lower=pd.Series({"Equity":.6,"Debt":.6,"Gold":.1})
    with pytest.raises(ValueError,match="infeasible"):
        PortfolioOptimizer().optimize(c,e,v,asset_min_weights=lower)

def test_nonfinite_input_rejected(data):
    c,e,v=data
    e.loc["Gold"]=np.nan
    with pytest.raises(ValueError,match="finite"):
        PortfolioOptimizer().optimize(c,e,v)

def test_liquidity_constraint(data):
    c,e,v=data
    limits=pd.Series({"Equity":.03,"Debt":.03,"Gold":.03})
    r=PortfolioOptimizer().optimize(c,e,v,liquidity_limits=limits)
    assert (r.trades.abs()<=.03001).all()
