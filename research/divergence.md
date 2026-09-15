# Divergence: our reconstruction vs published S&P 500

- Benchmark: `^GSPC`, the price-return index
  - Excludes dividends, matching our `auto_adjust=False` price pull
  - `^SP500TR` includes dividends, would drift above us by the dividend yield
  - `SPY` is a fund, carries its own tracking error and expense ratio

- Current window: 1178 trading days, 2022-01-03 to 2026-09-14
  - ours +57.98%, published +58.86%, gap -88.8bp
  - daily TE stdev 8.60bp, worst day 79.5bp, correlation 0.99689
  - Gap = our cumulative return minus published. TE stdev = noise floor, judge future changes against it

- Error scales with how far back we go, the survivorship signature
  - 2022: ours -18.30%, published -19.95%, TE 13.42bp, mean +0.74bp, gap +1.66pp
  - 2023: ours +23.54%, published +24.23%, TE 6.28bp, mean -0.23bp, gap -0.69pp
  - 2024: ours +20.45%, published +23.31%, TE 10.15bp, mean -0.94bp, gap -2.86pp
  - 2025: ours +16.90%, published +16.39%, TE 4.06bp, mean +0.20bp, gap +0.51pp
  - 2026: ours +11.16%, published +11.31%, TE 3.38bp, mean -0.08bp, gap -0.16pp
  - TE is 4x worse in 2022 than 2026
  - Drift does not accumulate: overall mean daily diff is -0.06bp and yearly gaps alternate sign, so this is noise not a consistent tilt
  - 2024 is the worst year at -2.86pp, unexplained, worth isolating

- Silent NaN exclusion, the most important finding
  - Nothing in the code handles NaN, the behaviour falls out of pandas defaults
  - `closes * shares` is NaN if either side is NaN, `caps.sum(axis=1)` skips NaN, so the denominator only ever includes available names
  - Net effect: a stock with any missing data is dropped from the universe that day and the rest are silently renormalised
  - Names contributing to weights: min 474, median 490, max 500. We reconstruct a 500-name index with as few as 474 names, no error raised
  - `w.sum(axis=1) == 1` is a vacuous check, it can never fail because the denominator is built from whatever survived
  - Renormalising a dropped name assumes it returned the index average that day, which is wrong but doesn't have severe consequences, so errors show as noise rather than collapse

- Ticker renames break share data, 29 tickers, 6816 ticker-days
  - All have complete prices and zero `nan_closes`, only share counts are missing
  - Yahoo carries price history back under the new symbol, but `get_shares_full` only records from the rename date forward
  - MRSH (Marsh McLennan) shares from 2025-06-30, prices from 2022-01-03, 874 of 1178 days dropped
  - VMRK (Vivmark Residential) shares from 2025-06-30, 874 days
  - PSKY (Paramount Skydance) shares from 2025-03-31, 812 days
  - XYZ (Block, formerly SQ) shares from 2025-01-22, 765 days
  - EXE (Expand Energy) 2024-10-03, SW (Smurfit Westrock) 2024-07-08
  - MRSH and VMRK sharing 2025-06-30 suggests Yahoo backfilled a batch of renames at once, so the cutoff is a record-keeping artifact
  - Most fixable problem found, the data exists under the old ticker, it is symbol mapping not missing data

- META missing for 109 trading days
  - Priced from day one but no share count until 2022-06-09, so a top-10 company is absent from the index for the first ~109 days of 2022
  - Main driver of 2022's 13.42bp TE, and META still appears in worst-day drivers for 2024
  - ELV 122 missing share-days, BALL 88, same shape
  - `implied_shares` cannot help: `get_valuation_measures` reaches back only 5 quarters from today, so it works at the window's end, not its start

- 11 tickers start after the window opens
  - CEG 2022-01-19, GEHC 2022-12-15, KVUE 2023-05-04, VLTO 2023-10-04, RDDT 2024-03-21, SOLV 2024-03-26, GEV 2024-03-27, SNDK 2025-02-13, Q 2025-10-27, FDXF 2026-05-27, HONA
  - Mostly spinoffs (GE HealthCare, GE Vernova, Kenvue, Veralto, Solventum) and IPOs
  - No fallback can help, these companies did not exist
  - `pct_change` gives NaN on a stock's first day, so new entrants correctly contribute nothing on day one

- Constituent count is inaccurate
  - Priced names per year, minimum: 2022 492, 2023 494, 2024 496, 2025 499, 2026 501
  - Reconstructing a 500-name index with 492 names, and they are the wrong 492 since names were added / removed

- Worst days are driven by mega-caps, not obscure names
  - 2022-02-03 +79.5bp: MSFT -27.0bp, AAPL -14.2bp, TMUS +4.1bp
  - 2024-02-22 -54.4bp: MSFT +17.1bp, AMZN +15.2bp, META +11.2bp
  - 2022-04-20 +53.0bp: TSLA -5.3bp, DIS -4.0bp, PYPL -3.1bp
  - 2024-05-23 -49.9bp: AAPL -14.1bp, GOOGL -8.0bp, MSFT -6.0bp
  - Our AAPL weight was 8.47% on 2022-02-03 against roughly 7% in the real index
  - Removed companies are missing from our denominator, so survivors absorb their weight and the distortion lands hardest on the largest names

- Fixed: dual-class double counting
  - Measured on the earlier 30-day window: gap -72.0bp to -20.6bp, TE 9.71bp to 5.68bp, correlation 0.98847 to 0.99647
  - yfinance reports the whole company's share count against every share class
  - GOOGL and GOOG each carried Alphabet's full 12.230B shares, so Alphabet counted twice at $4.2T, 11.45% weight instead of ~6%
  - Same for FOXA/FOX and NWSA/NWS
  - Detected with `last = shares.iloc[-1]; last[last.duplicated(keep=False)]`
  - Fix: keep one class per company (`SECOND_CLASS` in analysis.py). Retained class already carries total company shares, so its market cap is the full company
  - `SECOND_CLASS` is hardcoded to today's three pairs, needs to become detection as the horizon widens

- Remaining 1: float adjustment
  - We use full shares outstanding, so closely-held companies are overweighted
  - WMT is 54.7% float, so the real index gives it roughly half our weight. Most closely held: LVS 0.449, TMUS 0.453, PSKY 0.492, HRL 0.528, DVA 0.532, WMT 0.547
  - Median float ratio across the index is 0.994, so most names are almost fully floated and the adjustment only bites on a minority
  - Yahoo `floatShares` is usable for 485 of 503, broken for 18:
    - 14 impossible (ratio > 1): GOOGL, GOOG, FOX, NWS, KR, GIS, STT, BF-B and others, mostly dual-class where float is reported combined
    - BRK-B: 1.408B shares but 0.001B float, would delete Berkshire
    - 3 missing entirely
  - Measured on the 30-day window with a guarded fallback: TE 5.68bp to 4.91bp, correlation 0.99647 to 0.99705, cumulative gap slightly worse at -21.8bp
  - Deferred: `floatShares` is a current scalar with no history, so applying it backwards repeats the project-today-backwards problem, and the 18 broken names include a top-3 weight
  - S&P does not use raw float anyway, it applies a banded and rounded Investable Weight Factor updated quarterly, so even perfect float would not reproduce official weights

- Remaining 2: no divisor
  - S&P adjusts its divisor on every buyback, issuance and membership change so the level does not jump on non-price events
  - We have no divisor, so those events leak into our series
  - Self-check needing no external data: `(weights.shift(1) * closes.pct_change()).sum(axis=1)` vs `caps.sum(axis=1).pct_change()`
  - They agree to a hundredth of a bp except on days a share count changed
  - 433 such days over the 2022 window, largest 2024-06-10 at -595.7bp, 2022-07-18 -440.7bp, 2022-06-06 -371.6bp
  - Some are genuine corporate actions, some are share data appearing or vanishing mid-series, the same defect as META in another guise
  - The weighted figure is the correct one, issuance does not make a holder richer

- Remaining 3: survivorship and membership timing
  - Membership is today's Wikipedia table applied backwards, so removals are missing and additions are held too early
  - Correcting FERG and RDDT entry dates changed daily TE by 0.01bp on the 30-day window, immaterial there
  - Now material: this is the mechanism behind the year-by-year TE gradient above
  - Needs the historical changes table, not current membership

- Remaining 4: share count timing
  - `get_shares_full` dates values by Yahoo's filing record date, not S&P's effective date
  - Small, hard to quantify without a point-in-time source

- Ruled out
  - MRNA +177% on 2026-08-19: checked for a split, none found, share count unchanged either side. Genuine news move, present in the published index too
  - Blending dual-class prices instead of dropping the second class: 0.1bp

- Not diverging
  - Correlation 0.99689 over 1178 days means the mechanics are sound: elementwise market cap, row-normalised weights, one-day weight lag, compounding
  - Residual is dominated by data quality (renames, float, point-in-time membership), not construction logic

- Fix priority when we start
  - Make the pipeline loud first: assert constituent count, assert no top-50 name is missing, warn when the universe drops below a threshold.
  - Then ticker renames, the largest and most tractable data hole
  - Then historical membership, which the year-by-year gradient says is the structural limit
