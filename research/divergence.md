# Divergence: our reconstruction vs published S&P 500

- Benchmark: `^GSPC`, the price-return index
  - Excludes dividends, matching our `auto_adjust=False` price pull
  - `^SP500TR` includes dividends, would drift above us by the dividend yield
  - `SPY` is a fund, carries its own tracking error and expense ratio

- Current window: 1179 trading days, 2022-01-03 to 2026-09-15
  - ours +64.01%, published +58.13%, gap +588.4bp
  - daily TE stdev 4.06bp, worst day 16.0bp, correlation 0.99950
  - Gap = our cumulative return minus published. TE stdev = noise floor, judge future changes against it
  - Prefer TE stdev over cumulative gap: yearly errors of opposite sign can cancel and flatter the total
  - Gap flipped from -256bp to +588bp with the split fix. The old negative gap was largely splitters carried at a fraction of their weight during the biggest rally in the window

- Tracking by year, after the split fix
  - 2022: ours -20.68%, published -19.95%, TE 5.53bp, mean -0.31bp, gap -0.73pp
  - 2023: ours +26.75%, published +24.23%, TE 3.07bp, mean +0.81bp, gap +2.52pp
  - 2024: ours +25.57%, published +23.31%, TE 3.47bp, mean +0.74bp, gap +2.27pp
  - 2025: ours +17.13%, published +16.39%, TE 4.22bp, mean +0.28bp, gap +0.74pp
  - 2026: ours +10.92%, published +10.80%, TE 3.17bp, mean +0.07bp, gap +0.12pp
  - The year gradient is gone. TE was 13.42bp in 2022 and 3.38bp in 2026 before any fixes, now it is flat at 3-5bp throughout
  - So what looked like a survivorship signature was mostly splits. Survivorship is still present but much smaller than assumed
  - `mean_bp` is now consistently positive in 2023-2025, so we systematically overweight winners. That is the float-adjustment signature

- Silent NaN exclusion, the most important finding
  - Nothing in the code handles NaN, the behaviour falls out of pandas defaults
  - `closes * shares` is NaN if either side is NaN, `caps.sum(axis=1)` skips NaN, so the denominator only ever includes available names
  - Net effect: a stock with any missing data is dropped from the universe that day and the rest are silently renormalised
  - Names contributing to weights: min 491, median 499, max 503 after the rename fix, was min 474. We still reconstruct a 500-name index with as few as 491 names
  - `validation.py` now reports this on every run, so it is no longer silent, but the underlying holes remain
  - `w.sum(axis=1) == 1` is a vacuous check, it can never fail because the denominator is built from whatever survived
  - Renormalising a dropped name assumes it returned the index average that day, which is wrong but doesn't have severe consequences, so errors show as noise rather than collapse

- Fixed: split adjustment, the largest error found
  - `auto_adjust=False` does NOT give raw closes. It excludes dividends only, Yahoo's Close is split-adjusted either way
  - So prices were on a post-split basis all the way back, while `get_shares_full` files as-reported counts. Market cap was wrong by the split ratio for every day before each split
  - NVDA in Dec 2023: our cap read $0.122T against a true ~$1.22T, a 10x understatement. Weight 0.31% against a real ~3%
  - NVDA was therefore nearly absent from our index through 2023 and H1 2024, exactly when it was the market's largest contributor
  - 58 tickers split inside the window: CMG 50:1, BKNG 25:1, AMZN and GOOGL/GOOG 20:1, NVDA/AVGO/LRCX/SMCI/NFLX/KLAC 10:1, and others
  - The three largest `corporate_action_days` entries were all split dates, not issuances: 2024-06-10 NVDA, 2022-07-18 GOOGL, 2022-06-06 AMZN
  - Fix: `fetch_splits` in download.py, `split_factors` and `adjust_shares` in cleaning.py. Each day is scaled by the product of every split ratio dated after it, so shares land on the same basis as prices
  - Multiple splits compound automatically, and splits predating the window contribute nothing. TPL factor is 9.0 before 2024-03, 3.0 between its two splits, 1.0 after
  - Results: TE stdev 7.75bp to 4.06bp, worst day 54.2bp to 16.0bp, correlation 0.99746 to 0.99950
  - Per year TE: 2022 10.69 to 5.53, 2023 6.34 to 3.07, 2024 10.20 to 3.47. 2024 went from worst year to near best, confirming splits caused it

- Known defect: share filings near split boundaries
  - The split factor is correct, but Yahoo's filing dates do not always sit on the expected side of a split
  - TPL 2024-03-26 filed a post-split count one day early and 2024-03-27 filed a pre-split count on the split date, so our cap read $39.67B then $4.42B against a true ~$13B
  - 76 stock-days across 44 tickers move the adjusted share count more than 1.5x in a day: DXCM 4d, VMRK 4d, CVNA 4d, CPRT 4d, TPL 3d
  - Mostly one or two day spikes, often self-cancelling, so invisible in the cumulative gap but real noise in daily TE now that TE is down at 4bp
  - `check_share_jumps` in validation.py now reports these. It is a heuristic, not a missing-data check: a genuine large issuance can trip it too
  - Fix would be to widen the split boundary a few days and take whichever filing agrees with its neighbours

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
  - 2025-03-06 -16.0bp: NVDA -30.9bp, AMZN -15.3bp, META -13.6bp
  - 2025-02-20 -15.6bp: WMT -9.7bp, AMZN -7.1bp, JPM -6.2bp
  - 2025-03-10 -14.8bp: AAPL -33.3bp, NVDA -26.6bp, TSLA -24.9bp
  - 2022-05-09 -14.5bp: AAPL -22.8bp, TSLA -21.9bp, MSFT -20.5bp
  - 2026-07-23 -14.0bp: GOOGL -43.7bp, TSLA -29.9bp, AMZN -17.7bp
  - All now in the 14-16bp band rather than 43-54bp, with no single outlier and no ticker appearing in all five
  - MSFT dominated every worst day before the split fix, which pointed at its weight. That turned out to be the split mismatch distorting everything around it, not MSFT itself
  - The remaining pattern is residual weighting bias on the largest names, consistent with float rather than a data defect

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
  - 428 such days over the window, largest 2024-06-25 -870.7bp and 2024-06-26 +830.4bp, then 2025-04-11 +296.7bp
  - Before the split fix this check was mostly finding splits, not issuances. The largest entries are now paired opposite-sign days, the split-boundary filing noise above
  - The weighted figure is the correct one, issuance does not make a holder richer

- Remaining 3: survivorship and membership timing
  - Membership is today's Wikipedia table applied backwards, so removals are missing and additions are held too early
  - Correcting FERG and RDDT entry dates changed daily TE by 0.01bp on the 30-day window
  - Size is now unknown. The year-by-year TE gradient was the evidence for this being material, and the split fix flattened that gradient, so most of what was attributed here belonged to splits
  - Still real, since we hold 491-503 names and they are not the right ones, but it should be re-measured rather than assumed to be the structural limit
  - Needs the historical changes table, not current membership

- Remaining 4: share count timing
  - `get_shares_full` dates values by Yahoo's filing record date, not S&P's effective date
  - Small, hard to quantify without a point-in-time source

- Ruled out
  - MRNA +177% on 2026-08-19: checked for a split, none found, share count unchanged either side. Genuine news move, present in the published index too
  - Blending dual-class prices instead of dropping the second class: 0.1bp

- Not diverging
  - Correlation 0.99950 over 1179 days means the mechanics are sound: elementwise market cap, row-normalised weights, one-day weight lag, compounding
  - Residual is dominated by data quality (point-in-time membership, float), not construction logic

- Fix priority
  - Done: make the pipeline loud (`validation.py`), dual-class dedupe, ticker renames, split adjustment
  - Next: float adjustment, now the clearest remaining signal. `mean_bp` is positive across 2023-2025, meaning we overweight winners, which is what using full shares instead of float does
  - Then split-boundary filing noise, 76 stock-days, cheap to fix and now large relative to a 4bp TE
  - Then historical membership. Worth re-measuring first: the year gradient that motivated it has flattened, so survivorship may be smaller than assumed
  - Then spinoff listing lag, 96 ticker-days
  - Housekeeping: `SECOND_CLASS` and `RENAMES` are hardcoded lists that will silently go stale, and `--refresh` only reaches pipeline.py so changing START and running analysis.py returns the old window from cache
