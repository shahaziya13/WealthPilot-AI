## Day 5 — Tax and Liquidity Intelligence

Extract this ZIP into the existing WealthPilot-AI repository root, allowing the files to merge.
It adds the `wealthpilot/tax`, `config`, `tests`, and `docs` files. Do not replace the existing
top-level `wealthpilot` package initializer.

Run in PowerShell from the repository root:

```powershell
python -m pytest tests\test_tax_engine.py -v
python -m pytest -v
```

Tax rules are simplified, illustrative project assumptions only. Confirm current Indian tax
treatment with qualified professionals before any real-money or client-facing use. Liquidity
costs are estimates, not execution guarantees. The planner does not submit orders and always
requires human approval.

After both test commands pass, review `git status`, stage the Day 5 files, commit, and push.
Keep generated reports and local data out of Git.
