# Day 5 changelog

- Corrected the holding-period test fixture expectation: long-term gain is INR 400.
- Corrected phased-execution day count to use mathematical ceiling, avoiding undercounting fractional sessions.
- Added finite-number and non-negative market-impact coefficient validation.
- Kept all trade plans in human-approval-required state; no execution integration is present.
- Tax rates remain illustrative, effective-dated project assumptions and are not legal/tax advice.
