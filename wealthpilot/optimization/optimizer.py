from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class OptimizationConfig:
    risk_aversion: float = 4.0
    min_weight: float = 0.0
    max_weight: float = 0.60
    max_turnover: float = 0.25
    max_asset_trade: float = 0.15
    transaction_cost_bps: float = 15.0
    solver: str | None = None
    tolerance: float = 1e-5

@dataclass
class OptimizationResult:
    status: str
    weights: pd.Series
    trades: pd.Series
    expected_return: float
    expected_volatility: float
    turnover: float
    estimated_transaction_cost: float
    objective_value: float
    validation: dict

class PortfolioOptimizer:
    """CVXPY mean-variance optimizer. Produces proposals, never executes orders."""
    def __init__(self, config=None):
        self.config = config or OptimizationConfig()

    def optimize(self, current_weights, expected_returns, covariance,
                 *, asset_max_weights=None, asset_min_weights=None,
                 liquidity_limits=None):
        try:
            import cvxpy as cp
        except ImportError as exc:
            raise ImportError("Install CVXPY with: pip install cvxpy") from exc
        names=list(current_weights.index)
        if len(names)<2 or len(set(names))!=len(names):
            raise ValueError("At least two uniquely named assets are required")
        w0=current_weights.astype(float).to_numpy()
        mu=expected_returns.reindex(names).astype(float).to_numpy()
        cov=covariance.reindex(index=names,columns=names).astype(float).to_numpy()
        if not (np.isfinite(w0).all() and np.isfinite(mu).all() and np.isfinite(cov).all()):
            raise ValueError("Weights, expected returns and covariance must be finite")
        if (w0 < -1e-8).any() or w0.sum()<=0:
            raise ValueError("Current weights must be non-negative and sum to a positive value")
        w0=w0/w0.sum()
        cov=(cov+cov.T)/2
        eigval,eigvec=np.linalg.eigh(cov)
        cov=eigvec@np.diag(np.maximum(eigval,1e-10))@eigvec.T
        cfg=self.config; n=len(names)
        lower=np.full(n,cfg.min_weight); upper=np.full(n,cfg.max_weight)
        if asset_min_weights is not None:
            lower=np.maximum(lower,asset_min_weights.reindex(names).fillna(cfg.min_weight).to_numpy(float))
        if asset_max_weights is not None:
            upper=np.minimum(upper,asset_max_weights.reindex(names).fillna(cfg.max_weight).to_numpy(float))
        if (lower>upper).any() or lower.sum()>1+1e-9 or upper.sum()<1-1e-9:
            raise ValueError("Allocation bounds are infeasible: check min/max weights")
        w=cp.Variable(n); delta=w-w0
        cons=[cp.sum(w)==1,w>=lower,w<=upper,
              cp.norm1(delta)<=2*cfg.max_turnover,
              cp.abs(delta)<=cfg.max_asset_trade]
        liq=None
        if liquidity_limits is not None:
            liq=liquidity_limits.reindex(names).fillna(cfg.max_asset_trade).to_numpy(float)
            if (liq<0).any(): raise ValueError("Liquidity limits must be non-negative")
            cons.append(cp.abs(delta)<=liq)
        cost_rate=cfg.transaction_cost_bps/10000
        objective=cp.Maximize(mu@w-cfg.risk_aversion*cp.quad_form(w,cp.psd_wrap(cov))-cost_rate*cp.norm1(delta))
        problem=cp.Problem(objective,cons)
        installed=set(cp.installed_solvers())
        order=[cfg.solver] if cfg.solver else ["CLARABEL","OSQP","SCS"]
        solver=next((s for s in order if s and s in installed),None)
        if solver is None: raise RuntimeError(f"No supported CVXPY solver installed: {sorted(installed)}")
        problem.solve(solver=solver,warm_start=True,verbose=False)
        if problem.status not in (cp.OPTIMAL,cp.OPTIMAL_INACCURATE) or w.value is None:
            raise RuntimeError(f"Optimization failed: {problem.status}")
        weights=np.maximum(np.asarray(w.value).reshape(-1),0); weights/=weights.sum()
        trades=weights-w0
        turnover=float(np.abs(trades).sum()/2)
        validation={
          "weights_sum_to_one":abs(weights.sum()-1)<=cfg.tolerance,
          "non_negative_weights":bool((weights>=-cfg.tolerance).all()),
          "allocation_bounds_respected":bool(((weights>=lower-cfg.tolerance)&(weights<=upper+cfg.tolerance)).all()),
          "turnover_limit_respected":turnover<=cfg.max_turnover+cfg.tolerance,
          "per_asset_trade_limit_respected":bool((np.abs(trades)<=cfg.max_asset_trade+cfg.tolerance).all()),
          "liquidity_limits_respected":True if liq is None else bool((np.abs(trades)<=liq+cfg.tolerance).all())
        }
        if not all(validation.values()): raise RuntimeError(f"Post-solve validation failed: {validation}")
        variance=max(float(weights@cov@weights),0)
        return OptimizationResult(str(problem.status),pd.Series(weights,index=names,name="proposed_weight"),
          pd.Series(trades,index=names,name="trade_weight_change"),float(mu@weights),
          float(np.sqrt(variance)),turnover,float(np.abs(trades).sum()*cost_rate),
          float(problem.value),validation)
