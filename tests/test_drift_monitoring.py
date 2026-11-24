import numpy as np
import pandas as pd
import pytest
from wealthpilot.monitoring import DriftCalculator, DriftMonitor, ThresholdManager

ASSETS = ["indian_equity", "international_equity", "indian_fixed_income", "international_fixed_income", "alternatives", "cash"]
TARGETS = {"Balanced": dict(zip(ASSETS, [.34,.16,.20,.10,.12,.08]))}

def fixture_data(weights=None):
    weights = weights or [.34,.16,.20,.10,.12,.08]
    p = pd.DataFrame([{"portfolio_id":"P1","risk_category":"Balanced","portfolio_value_inr":1000.,"drift_band":.03}])
    h = pd.DataFrame([{"portfolio_id":"P1","asset_class":a,"market_value_inr":w*1000} for a,w in zip(ASSETS,weights)])
    return p,h

def test_zero_drift_metrics():
    p,h=fixture_data(); row=DriftCalculator().calculate(p,h,TARGETS).summary.iloc[0]
    assert row.sum_absolute_drift == pytest.approx(0); assert row.rms_drift == pytest.approx(0); assert row.max_absolute_drift == pytest.approx(0)

def test_sad_rmsd_and_max():
    p,h=fixture_data([.39,.11,.20,.10,.12,.08]); row=DriftCalculator().calculate(p,h,TARGETS).summary.iloc[0]
    assert row.sum_absolute_drift == pytest.approx(.10); assert row.rms_drift == pytest.approx(np.sqrt((.05**2+.05**2)/6)); assert row.max_absolute_drift == pytest.approx(.05)

def test_predicted_te_positive():
    p,h=fixture_data([.39,.11,.20,.10,.12,.08]); row=DriftCalculator().calculate(p,h,TARGETS,np.eye(6)*.0001).summary.iloc[0]
    assert row.predicted_tracking_error > 0

def test_threshold_overlay_and_fallback():
    p=pd.DataFrame([{"portfolio_id":"P1","risk_category":"Balanced","drift_band":.025},{"portfolio_id":"P2","risk_category":"Balanced","drift_band":np.nan}])
    assert ThresholdManager().thresholds_for(p).tolist() == pytest.approx([.025,.03])

def test_monitor_flags_breach():
    p=pd.DataFrame([{"portfolio_id":"P1","risk_category":"Balanced","portfolio_value_inr":1000.,"drift_band":.03},{"portfolio_id":"P2","risk_category":"Balanced","portfolio_value_inr":1000.,"drift_band":.03}])
    rows=[]
    for pid, ws in [("P1",[.34,.16,.20,.10,.12,.08]),("P2",[.40,.10,.20,.10,.12,.08])]:
        rows += [{"portfolio_id":pid,"asset_class":a,"market_value_inr":w*1000} for a,w in zip(ASSETS,ws)]
    result=DriftMonitor().run(p,pd.DataFrame(rows),TARGETS)
    assert result["portfolio_count"] == 2 and result["breach_count"] == 1
    assert result["breach_queue"].iloc[0].portfolio_id == "P2"

def test_unknown_asset_rejected():
    p,h=fixture_data(); h.loc[0,"asset_class"]="crypto"
    with pytest.raises(ValueError,match="Unsupported asset classes"): DriftCalculator().calculate(p,h,TARGETS)

def test_invalid_targets_rejected():
    p,h=fixture_data(); invalid={"Balanced":dict(zip(ASSETS,[.5]*6))}
    with pytest.raises(ValueError,match="sum to 1"): DriftCalculator().calculate(p,h,invalid)

def test_non_psd_covariance_rejected():
    p,h=fixture_data(); cov=np.eye(6); cov[0,0]=-1
    with pytest.raises(ValueError,match="positive semidefinite"): DriftCalculator().calculate(p,h,TARGETS,cov)
