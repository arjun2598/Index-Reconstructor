# Divergence: our reconstruction vs published S&P 500

- Benchmark: `^GSPC`, the price-return index
  - Excludes dividends, matching our `auto_adjust=False` price pull
  - `^SP500TR` includes dividends, would drift above us by the dividend yield
  - `SPY` is a fund, carries its own tracking error and expense ratio

- Measurements: 30 trading days, 2026-08-03 to 2026-09-14. Will shift as horizon expands
  - Before dual-class fix: gap -72.0bp, daily TE stdev 9.71bp, correlation 0.98847
  - After dual-class fix: gap -20.6bp, daily TE stdev 5.68bp, correlation 0.99647
  - Gap = our cumulative return minus published. TE stdev = noise floor, judge future changes against it

- Fixed: dual-class double counting
  - yfinance reports the whole company's share count against every share class
  - GOOGL and GOOG each carried Alphabet's full 12.230B shares, so Alphabet counted twice at $4.2T, 11.45% weight instead of ~6%
  - Same for FOXA/FOX and NWSA/NWS
  - Detected with `last = shares.iloc[-1]; last[last.duplicated(keep=False)]`
  - Fix: keep one class per company (`SECOND_CLASS` in analysis.py). Retained class already carries total company shares, so its market cap is the full company
  - `SECOND_CLASS` is hardcoded to today's three pairs, needs to become detection when we extend to 2015

- Remaining 1: float adjustment, the largest residual
  - S&P weights by shares available to public, excluding insider and strategic holdings
  - We use full shares outstanding, so closely-held companies are overweighted
  - WMT is 54.7% float, so real index gives it roughly half our weight
  - Yahoo `floatShares` cannot be swapped in, it is broken for the names that matter most:
    - GOOGL: 5.867B shares but 10.879B float (exceeds shares, combined across classes)
    - GOOG: same 10.879B repeated
    - BRK-B: 1.408B shares but 0.001B float, would delete Berkshire
    - WMT: 4.350B of 7.958B, plausible
  - Needs per-class float from a source that models share classes correctly

- Remaining 2: no divisor
  - S&P adjusts its divisor on every buyback, issuance and membership change so the level does not jump on non-price events
  - We have no divisor, so those events leak into our series
  - Self-check needing no external data: `(weights.shift(1) * closes.pct_change()).sum(axis=1)` vs `caps.sum(axis=1).pct_change()`
  - They agree to a hundredth of a bp except on days a share count changed
  - 2026-09-03 diverged 13.7bp, traced to APH filing ~1.233B extra shares, adding $100.9B market cap with no price move
  - The weighted figure is the correct one, issuance does not make a holder richer
  - Days these two disagree are days a corporate action occurred

- Remaining 3: survivorship and membership timing
  - Membership is today's Wikipedia table applied backwards, so removals are missing and additions are held too early
  - FERG added 2026-08-05, RDDT added 2026-08-18, both inside the window
  - Correcting their entry dates changed daily TE by 0.01bp, immaterial at 30 days
  - Grows with horizon, so an earlier dataframe needs the historical changes table, not current membership

- Remaining 4: share count timing
  - `get_shares_full` dates values by Yahoo's filing record date, not S&P's effective date
  - Small, hard to quantify without a point-in-time source

- Ruled out
  - MRNA +177% on 2026-08-19: checked for a split, none found, share count unchanged either side. Genuine news move, present in the published index too

- Not diverging
  - Correlation 0.99647 means the mechanics are sound: elementwise market cap, row-normalised weights, one-day weight lag, compounding
  - Residual is dominated by data quality (float, point-in-time membership), not construction logic
