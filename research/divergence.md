# Divergence: our reconstruction vs published S&P 500

- Benchmark: `^GSPC`, the price-return index
  - Excludes dividends, matching our `auto_adjust=False` price pull
  - `^SP500TR` includes dividends, would drift above us by the dividend yield
  - `SPY` is a fund, carries its own tracking error and expense ratio

- Current window: 1179 trading days, 2022-01-03 to 2026-09-15
  - ours +55.94%, published +58.51%, gap -256.3bp
  - daily TE stdev 7.75bp, worst day 54.2bp, correlation 0.99746
  - Gap = our cumulative return minus published. TE stdev = noise floor, judge future changes against it
  - Prefer TE stdev over cumulative gap: yearly errors of opposite sign can cancel and inaccurately report the total

- Error scales with how far back we go, likely survivorship
  - 2022: ours -19.09%, published -19.95%, TE 10.69bp, mean +0.37bp, gap +0.86pp
  - 2023: ours +23.48%, published +24.23%, TE 6.34bp, mean -0.25bp, gap -0.75pp
  - 2024: ours +20.40%, published +23.31%, TE 10.20bp, mean -0.95bp, gap -2.91pp
  - 2025: ours +16.90%, published +16.39%, TE 3.95bp, mean +0.20bp, gap +0.51pp
  - 2026: ours +10.90%, published +11.06%, TE 3.37bp, mean -0.08bp, gap -0.16pp
  - 2024 is now the dominant problem at -2.91pp, three of the five worst days fall in it
  - 2022 and 2024 are both high TE but for different reasons, so the gradient is not purely survivorship

- Silent NaN exclusion, the most important finding
  - Nothing in the code handles NaN, the behaviour falls out of pandas defaults
  - `closes * shares` is NaN if either side is NaN, `caps.sum(axis=1)` skips NaN, so the denominator only ever includes available names
  - Net effect: a stock with any missing data is dropped from the universe that day and the rest are silently renormalised
  - Names contributing to weights: min 491, median 499, max 503 after the rename fix, was min 474. We still reconstruct a 500-name index with as few as 491 names
  - `validation.py` now reports this on every run, so it is no longer silent, but the underlying holes remain
  - `w.sum(axis=1) == 1` is a vacuous check, it can never fail because the denominator is built from whatever survived
  - Renormalising a dropped name assumes it returned the index average that day, which is wrong but doesn't have severe consequences, so errors show as noise rather than collapse

- Fixed: ticker renames
  - Yahoo carries price history back under a new symbol, but `get_shares_full` only files from the rename date forward, so the early period had prices with no share count
  - 15 renames mapped in `RENAMES` (config.py), fetched under the old symbol and merged with `combine_first` so current filings win
  - META was FB, ELV was ANTM, BALL was BLL, WBD was DISCA, WTW was WLTW, RVTY was PKI, EG was RE, CPAY was FLT, XYZ was SQ, PSKY was PARA, EXE was CHK, MRSH was MMC, VMRK was AVB, TKO was WWE, SW was WRK
  - Every old symbol still returns share data from yfinance, each series ending at its rename date
  - Coverage: 6816 ticker-days missing across 24 tickers to 96 across 10. Universe min 477 to 491, median 493 to 499
  - Daily tracking: TE stdev 8.60bp to 7.75bp, worst day 79.5bp to 54.2bp, correlation 0.99689 to 0.99746, 2022 TE 13.42bp to 10.69bp
  - Cumulative gap went the other way, -88.8bp to -256.3bp, because 2022's +1.66pp error was partly cancelling 2024's -2.86pp. Removing it exposed the real size of what remains, it is not a regression
  - `RENAMES` is hardcoded and found by hand. Any new rename will silently reopen the same hole

- Remaining coverage holes: spinoff listing lag, 96 ticker-days across 10 tickers
  - A company lists and trades for a few days before Yahoo files its first share count
  - PSKY 33d, GEHC 13d, CEG 12d, HONA 10d, Q 7d, SNDK 7d, FDXF 4d, GEV 4d, SOLV 4d, KVUE 2d
  - Different fix from renames: there is no old symbol, so the first known value would have to be carried backwards
  - Small, and backfilling means asserting a share count for days before it was reported

- 11 tickers start after the window opens
  - CEG 2022-01-19, GEHC 2022-12-15, KVUE 2023-05-04, VLTO 2023-10-04, RDDT 2024-03-21, SOLV 2024-03-26, GEV 2024-03-27, SNDK 2025-02-13, Q 2025-10-27, FDXF 2026-05-27, HONA 2026-06-15
  - Mostly spinoffs (GE HealthCare, GE Vernova, Kenvue, Veralto, Solventum, FedEx Freight, Honeywell Aerospace, Qnity) and IPOs (Reddit)
  - No fallback can help, these companies did not exist
  - `pct_change` gives NaN on a stock's first day, so new entrants correctly contribute nothing on day one

- Constituent count is inaccurate
  - Usable names per day: min 491, median 499, max 503
  - Still short of 500 on 788 of 1179 days, and they are not the right names since names were added / removed

- Worst days are driven by mega-caps, not obscure names
  - 2024-02-22 -54.2bp: MSFT +17.1bp, AMZN +15.1bp, META +11.2bp
  - 2024-05-23 -49.8bp: AAPL -14.0bp, GOOGL -8.0bp, MSFT -6.0bp
  - 2024-04-19 +49.4bp: META -12.7bp, AMZN -11.5bp, MSFT -9.3bp
  - 2023-05-25 -49.2bp: MSFT +25.9bp, GOOGL +9.5bp, AMD +5.6bp
  - 2022-02-04 -43.0bp: MSFT +10.2bp, BAC +4.4bp, JPM +3.3bp
  - MSFT appears in all five, so its weight is the most likely single culprit
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
  - 437 such days over the window, largest 2024-06-10 at -593.2bp, 2022-07-18 -437.8bp, 2022-06-06 -361.5bp
  - The rename fix barely moved this count, so most of these are genuine share changes rather than data arriving
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
  - Correlation 0.99746 over 1179 days means the mechanics are sound: elementwise market cap, row-normalised weights, one-day weight lag, compounding
  - Residual is dominated by data quality (point-in-time membership, float), not construction logic

- Fix priority
  - Next: 2024, now the largest single item at -2.91pp and untouched by anything so far. MSFT appears in all five worst days
  - Then historical membership, which the year gradient says is the structural limit
  - Then spinoff listing lag (96 ticker-days) and float adjustment, both small and both requiring a judgement call rather than better data
  - Housekeeping: `SECOND_CLASS` and `RENAMES` are both hardcoded lists that will silently go stale, and `--refresh` only reaches pipeline.py so changing START and running analysis.py returns the old window from cache
