# Divergence: our reconstruction vs published S&P 500

- Benchmark: `^GSPC`, the price-return index
  - Excludes dividends, matching our `auto_adjust=False` price pull
  - `^SP500TR` includes dividends, would drift above us by the dividend yield
  - `SPY` is a fund, carries its own tracking error and expense ratio

- Current window: 1179 trading days, 2022-01-03 to 2026-09-15
  - ours +60.34%, published +58.06%, gap +228.3bp
  - daily TE stdev 2.51bp, worst day 14.1bp, correlation 0.99974
  - Gap = our cumulative return minus published. TE stdev = noise floor, judge future changes against it
  - Prefer TE stdev over cumulative gap: yearly errors of opposite sign can cancel and flatter the total

- Tracking by year, after split and membership fixes
  - 2022: ours -20.10%, published -19.95%, TE 2.78bp, mean -0.06bp, gap -0.14pp
  - 2023: ours +25.47%, published +24.23%, TE 2.33bp, mean +0.39bp, gap +1.23pp
  - 2024: ours +24.35%, published +23.31%, TE 1.98bp, mean +0.34bp, gap +1.04pp
  - 2025: ours +16.53%, published +16.39%, TE 2.34bp, mean +0.06bp, gap +0.14pp
  - 2026: ours +10.37%, published +10.75%, TE 3.17bp, mean -0.19bp, gap -0.37pp
  - Yearly gaps are now small and mixed in sign, where they were persistently positive before the membership fix
  - 2026 is the only year that did not improve, and its gap flipped negative. Recently removed companies bite hardest at the end of the window, and that half is not fixable from the current Wikipedia page

- Silent NaN exclusion, the most important finding
  - Nothing in the code handles NaN, the behaviour falls out of pandas defaults
  - `closes * shares` is NaN if either side is NaN, `caps.sum(axis=1)` skips NaN, so the denominator only ever includes available names
  - Net effect: a stock with any missing data is dropped from the universe that day and the rest are silently renormalised
  - Names contributing to weights: min 491, median 499, max 503 after the rename fix, was min 474. We still reconstruct a 500-name index with as few as 491 names
  - `validation.py` now reports this on every run, so it is no longer silent, but the underlying holes remain
  - `w.sum(axis=1) == 1` is a vacuous check, it can never fail because the denominator is built from whatever survived
  - Renormalising a dropped name assumes it returned the index average that day, which is wrong but doesn't have severe consequences, so errors show as noise rather than collapse

- Fixed: addition timing, the drift's main cause
  - 77 of today's 503 members joined after 2022-01-03, roughly 15 per year, and we were holding all of them from day one
  - Companies are added because they grew enough to qualify, so holding them early captures the run-up that earned them a place, which the real index never participated in
  - `Date added` was already being scraped and then discarded. `fetch_constituents` now keeps it, `build_membership` in cleaning.py turns it into a boolean frame, and `market_caps` applies it with `.where()` so a non-member goes NaN and drops out of the weights
  - A blank date means the company predates our window, so it stays a member throughout
  - Results: gap +588.4bp to +228.3bp, TE stdev 4.06bp to 2.51bp, mean +0.33bp to +0.13bp, correlation 0.99950 to 0.99974
  - Every year improved. Per-year TE: 2022 5.53 to 2.78, 2023 3.07 to 2.33, 2024 3.47 to 1.98, 2025 4.22 to 2.34
  - `MIN_UNIVERSE` warning is now partly expected rather than a defect: early in the window we should hold fewer than 500 names. The check still measures data availability, not membership, so the two now overlap

- Remaining: companies removed from the index
  - Roughly 77 companies left the index over the window and are absent from our panel entirely
  - They typically underperformed before being dropped, so excluding them exaggerates our return. This is the other half of survivorship and the likely source of the residual +228bp
  - Would need a historical membership source

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
  - 2026-07-23 -14.1bp: GOOGL -43.7bp, TSLA -30.0bp, AMZN -17.7bp
  - 2025-09-10 +12.4bp: ORCL +41.8bp, NVDA +27.4bp, AVGO +26.5bp
  - 2026-07-31 +8.4bp: AMZN +57.6bp, AAPL -53.4bp, GOOGL +40.8bp
  - 2026-07-30 -8.2bp: MSFT +67.7bp, MU +23.1bp, NVDA +18.3bp
  - Down from a 43-54bp band before the split fix, to 14-16bp after it, to 7-14bp now
  - Four of the five worst days are in 2026, matching the year-by-year table, so what is left concentrates at the end of the window

- Fixed: dual-class double counting
  - Measured on the earlier 30-day window: gap -72.0bp to -20.6bp, TE 9.71bp to 5.68bp, correlation 0.98847 to 0.99647
  - yfinance reports the whole company's share count against every share class
  - GOOGL and GOOG each carried Alphabet's full 12.230B shares, so Alphabet counted twice at $4.2T, 11.45% weight instead of ~6%
  - Same for FOXA/FOX and NWSA/NWS
  - Detected with `last = shares.iloc[-1]; last[last.duplicated(keep=False)]`
  - Fix: keep one class per company (`SECOND_CLASS` in analysis.py). Retained class already carries total company shares, so its market cap is the full company
  - `SECOND_CLASS` is hardcoded to today's three pairs, needs to become detection as the horizon widens

- Remaining 1: float adjustment
  - S&P weights by shares available to the public, excluding insider and strategic holdings. We use full shares outstanding, so closely-held companies are overweighted
  - Most closely held: BRK-B 0.001 (broken), LVS 0.449, TMUS 0.453, PSKY 0.492, HRL 0.528, DVA 0.532, WMT 0.547
  - Median float ratio is 0.994, so most names are almost fully floated and this only bites on a minority
  - Yahoo `floatShares` is usable for 485 of 503: 14 report a float above shares outstanding (dual-class names given a combined figure), BRK-B reports 0.001 which would delete Berkshire, 3 are missing. Those fall back to full shares
  - Measured on the current panel: TE stdev 2.51bp to 2.28bp, correlation 0.99974 to 0.99978, gap slightly worse at +167bp
  - It does NOT touch the drift. `mean_bp` stays at +0.13 to +0.14, so float is a noise reduction, not a bias correction. An earlier note here predicted the opposite and was wrong
  - Deferred: `floatShares` is a current scalar with no history, so applying today's ratio across 1179 days assumes insider stakes never changed. The ratio is dimensionless, so at least it is unaffected by the split adjustment
  - S&P does not use raw float anyway, it applies a banded and rounded Investable Weight Factor updated quarterly

- Remaining 2: no divisor
  - S&P adjusts its divisor on every buyback, issuance and membership change so the level does not jump on non-price events
  - We have no divisor, so those events leak into our series
  - Self-check needing no external data: `(weights.shift(1) * closes.pct_change()).sum(axis=1)` vs `caps.sum(axis=1).pct_change()`
  - They agree to a hundredth of a bp except on days a share count changed
  - 446 such days over the window, largest 2024-06-25 -890.4bp and 2024-06-26 +847.5bp, then 2025-04-11 +295.7bp
  - Before the split fix this check was mostly finding splits, not issuances. The largest entries are now paired opposite-sign days, the split-boundary filing noise above
  - The weighted figure is the correct one, issuance does not make a holder richer

- Remaining 3: membership timing, half fixed
  - Additions are fixed, see the addition timing section above
  - Removals are not: roughly 77 companies left the index over the window and are missing entirely
  - The current Wikipedia page no longer carries a changes table, so a different source is needed

- Remaining 4: share count timing
  - `get_shares_full` dates values by Yahoo's filing record date, not S&P's effective date
  - Small, hard to quantify without a point-in-time source

- Ruled out
  - MRNA +177% on 2026-08-19: checked for a split, none found, share count unchanged either side. Genuine news move, present in the published index too
  - Blending dual-class prices instead of dropping the second class: 0.1bp
  - Our market caps are not the problem. Cross-checked against Yahoo's own `marketCap` for the nine largest names, every one matches within 1%

- Methods that did not work
  - Leave-one-out (rebuild the index without a stock, see if the gap shrinks) is invalid here. The published index still holds that stock, so removing it creates a mismatch by construction. It conflates a stock's genuine return contribution with mis-weighting
  - It produced two false leads: MSFT as the cause of 2024, and NVDA as the cause of the drift. Both were artifacts of the method
  - A flat year-by-year TE gradient was read as evidence against survivorship. Wrong test: survivorship shows up as drift in `mean_bp` and the cumulative gap, not as year-to-year noise

- Not diverging
  - Correlation 0.99974 over 1179 days means the mechanics are sound: elementwise market cap, row-normalised weights, one-day weight lag, compounding
  - Residual is dominated by data quality (point-in-time membership, float), not construction logic

- Fix priority
  - Done: make the pipeline loud (`validation.py`), dual-class dedupe, ticker renames, split adjustment, addition timing
  - Next: removed companies, the other half of survivorship and the likely source of the residual +228bp. Needs a historical membership source since Wikipedia's changes table is gone
  - Then float adjustment, worth 2.51bp to 2.28bp but it is a current ratio projected backwards and does not touch the drift
  - Then split-boundary filing noise (76 stock-days) and spinoff listing lag (96 ticker-days)
  - Housekeeping: `SECOND_CLASS` and `RENAMES` are hardcoded lists that will silently go stale, `MIN_UNIVERSE` now overlaps with membership so its warning is partly expected, and `--refresh` only reaches pipeline.py so changing START and running analysis.py returns the old window from cache
