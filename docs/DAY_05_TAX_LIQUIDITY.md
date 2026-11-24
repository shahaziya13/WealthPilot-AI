# Day 05 — Tax and Liquidity Intelligence

## Scope implemented
- Deterministic tax-lot selection: minimum realised gain, maximum loss opportunity (ordering by lowest gain), FIFO and LIFO.
- Holding-period classification and configurable rate/exemption estimates.
- Liquidity capacity from ADV participation and optional notional cap.
- Spread and square-root market-impact cost estimates.
- Tax-aware sell planning with a mandatory human-approval status; no broker integration or order execution.

## Source alignment
The supplied Project 1D brief (section A1.3, printed page 5) requires lot-level tax analysis, loss harvesting, gain deferral, explicit/implicit transaction costs and hard liquidity constraints, including phased execution. Section B2.2 (printed page 25) assigns lot-level tax analysis to the Tax Optimisation Agent.

## Important limitations
The YAML tax rates are labelled project-brief reference assumptions, not a complete or authoritative Indian tax engine. Actual tax depends on instrument classification, acquisition/transfer dates, taxpayer status, grandfathering, exemptions, set-off/carry-forward, surcharge caps, cess and amendments. The debt STCG rate in YAML is deliberately a placeholder because slab rates are taxpayer-specific. A production release must use a legally reviewed, effective-dated rule registry and tax-professional sign-off.

The estimator does not yet implement:
- Section 112A grandfathering / FMV as at 31-Jan-2018
- STT and instrument eligibility validation
- Section 50AA and other debt-fund acquisition-date branches
- taxpayer slab calculation, surcharge caps, loss set-off and carry-forward
- security substitution / wash-trade controls / tracking-error optimisation
- multi-day child-order generation or live market-depth feeds

Liquidity calculations are estimates. ADV participation and impact coefficients must be calibrated by instrument and market. They are not execution guarantees.

## Validation
Run `pytest tests/test_tax_engine.py -v` and then `pytest -v`.
