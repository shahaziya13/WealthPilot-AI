# Day 1 Data Model

## Entities

- **Portfolio**: client and portfolio identifiers, risk category, current value, drift band, tax profile, liquidity needs and restriction flags.
- **Security**: synthetic instrument identifier, asset class, geography, sector, currency and liquidity proxies.
- **Holding**: portfolio-security position, quantity, market value and portfolio weight.
- **Tax lot**: acquisition date, quantity and cost basis for a holding.
- **Market price**: date, security, adjusted close and daily return.
- **Asset-class return**: daily correlated return series for the six strategic asset classes.

## Asset classes

1. Indian equities
2. International equities
3. Indian fixed income
4. International fixed income
5. Alternatives
6. Cash / liquid instruments

## Portfolio category counts

| Category | Portfolios | Drift band |
|---|---:|---:|
| Ultra-Conservative | 5,000 | 2.0% |
| Conservative | 12,000 | 2.5% |
| Balanced | 18,000 | 3.0% |
| Aggressive | 10,000 | 4.0% |
| Ultra-Aggressive | 5,000 | 5.0% |

## AUM

Portfolio balances are generated from a lognormal distribution and rescaled so the aggregate equals INR 25,000 crore exactly. Individual portfolio values therefore vary while the business-level total is controlled.

## Provenance and limitations

Every generated row is labelled synthetic. The configured return assumptions are illustrative, not empirical estimates. No personal data or real client identifiers are used.
