# Divergence: our reconstruction vs the published S&P 500

## Current state

- Window: 1179 trading days, 2022-01-03 to 2026-09-15
- Correlation of daily returns: 0.99978
- Daily tracking error: stdev 2.34bp, mean +0.03bp, worst day 14.1bp
- Cumulative: ours +58.51%, published +58.12%, gap +39.6bp

- Benchmark is `^GSPC`, the price-return index
  - Excludes dividends, matching our `auto_adjust=False` price pull
  - `^SP500TR` includes dividends and would drift above us by the dividend yield
  - `SPY` and `VOO` are funds with their own tracking error, so they measure someone else's error as well as ours

- By year, all of it now small and mixed in sign
  - 2022: TE 2.56bp, mean -0.17bp, gap -0.38pp
  - 2023: TE 1.97bp, mean +0.22bp, gap +0.67pp
  - 2024: TE 1.77bp, mean +0.22bp, gap +0.68pp
  - 2025: TE 2.26bp, mean +0.00bp, gap -0.00pp
  - 2026: TE 3.18bp, mean -0.20bp, gap -0.40pp
  - Mean daily difference across the whole window is +0.03bp, which is indistinguishable from zero. There is no systematic drift left

- Judge changes by TE stdev, not the cumulative gap
  - Yearly errors of opposite sign cancel, so the gap can look small while the underlying errors are large
  - This happened: fixing renames improved every daily metric while the cumulative gap got worse, because a compensating error had been removed

## Fixes, in order of impact

- Point-in-time membership, which removed the drift
  - Until this we held today's 503 members for the whole window. Additions were corrected from `Date added`, but companies removed from the index were missing entirely, and they typically underperform before being dropped, so excluding them flattered our return
  - Wikipedia's "Historical components of the S&P 500" page carries 407 additions and removals with effective dates back to 1976
  - `fetch_changes` scrapes it. `load_raw` expands the universe from 503 to 589 tickers, adding every name added or removed during the window, since without their prices the data simply is not there
  - `membership_timeline` walks backwards from today's list: a change on date d means that before d the index held the removed name and not the added one, so stepping back over it undoes both sides
  - Gap +228.3bp to +39.6bp, mean daily +0.13bp to +0.03bp, TE stdev 2.51 to 2.34bp, correlation 0.99974 to 0.99978
  - This confirmed what had been a hypothesis: the residual drift was the missing removed companies, not float or anything else
  - Bug worth remembering: the first version walked the timeline newest first, so the oldest membership set was applied last and overwrote everything. The index showed a constant 312 members. Iterate oldest first so each later entry overwrites only the tail it applies to

- Split adjustment, the largest error found
  - `auto_adjust=False` excludes dividends only. Yahoo's Close is split-adjusted either way, while `get_shares_full` reports as-filed counts, so market cap was wrong by the split ratio for every day before each split
  - NVDA read $0.122T in Dec 2023 against a true ~$1.22T, giving it 0.31% weight against a real ~3%. It was nearly absent from our index through the period it led the market
  - 58 tickers split inside the window, including CMG 50:1, BKNG 25:1, AMZN and GOOGL 20:1, NVDA and AVGO 10:1
  - Fix: `fetch_splits` in download.py, `split_factors` and `adjust_shares` in cleaning.py. Each day is scaled by the product of every split ratio dated after it, putting shares on the same basis as prices. Multiple splits compound, splits predating the window contribute nothing
  - TE stdev 7.75 to 4.06bp, worst day 54.2 to 16.0bp, correlation 0.99746 to 0.99950
  - 2024 went from the worst year (10.20bp) to near the best (3.47bp)

- Addition timing, since superseded by full membership
  - 77 of today's 503 members joined after 2022-01-03, roughly 15 a year, and all were held from day one. Companies are added because they grew enough to qualify, so holding them early captures the run-up that earned them a place
  - Fixed using `Date added`, which was already scraped and then discarded
  - Gap +588.4 to +228.3bp, TE stdev 4.06 to 2.51bp, mean +0.33 to +0.13bp
  - The change log now supplies both sides, so `Date added` is no longer the source. This step is kept here because it isolated how much of the drift was additions (roughly 60%) versus removals (the rest)

- Ticker renames
  - Yahoo carries price history back under a new symbol but files share counts only from the rename date, leaving prices with no share count for the earlier period
  - 15 renames mapped in `RENAMES` (config.py), fetched under the old symbol and merged with `combine_first` so current filings win
  - META was FB, ELV was ANTM, XYZ was SQ, MRSH was MMC, PSKY was PARA, EXE was CHK, and others
  - Coverage: 6816 ticker-days missing across 24 tickers, down to 96 across 10
  - TE stdev 8.60 to 7.75bp, worst day 79.5 to 54.2bp, correlation 0.99689 to 0.99746

- Dual-class double counting
  - yfinance reports the whole company's share count against every share class, so GOOGL and GOOG each carried Alphabet's full 12.230B shares. Alphabet entered twice at $4.2T, taking 11.45% weight instead of ~6%. Same for FOXA/FOX and NWSA/NWS
  - Found by scanning for tickers with identical share counts: `last[last.duplicated(keep=False)]`
  - Fix: keep one class per company (`SECOND_CLASS`). The retained class already carries total company shares, so its market cap is the full company
  - Measured on a 30-day window: gap -72.0 to -20.6bp, TE 9.71 to 5.68bp, correlation 0.98847 to 0.99647

- Validation, which found none of the above but stopped them hiding
  - A missing cell silently drops a stock and renormalises the rest, so `w.sum(axis=1) == 1` can never fail. Nothing downstream can detect a hole
  - `validation.py` checks the inputs instead, scoped to companies that were members that day
  - Before this we were reconstructing a 500-name index with as few as 474 names, with no error raised

## Remaining defects

- Companies Yahoo will not price, about 3% of the index
  - We now know who was a member and when, but 47 tickers have no price data at all: 17297 member-days, roughly 15 names at any time
  - EA 1148d, CTRA 1089d, HOLX 1069d, K 989d, IPG 980d are the largest
  - These are companies acquired (ATVI, CERN, XLNX, PXD), failed (SIVB, FRC, SBNY) or taken private. Yahoo drops the symbol once it stops trading
  - They are correctly marked as members and simply fall out of the weights, so the error is bounded and named rather than hidden
  - Ticker reuse is a live hazard here: SBNY returns 521 rows starting 2024, which is a different company using Signature Bank's old symbol after it failed in 2023. The membership mask handles it, since we only use data while a name was a member, but a naive universe expansion would inject the wrong prices
  - The unpriceable fraction will grow the further back the window goes

- Float adjustment
  - S&P weights by shares available to the public. We use full shares outstanding, so closely-held companies are overweighted: LVS 0.449, TMUS 0.453, WMT 0.547
  - Median float ratio is 0.994, so most names are almost fully floated and this only bites on a minority
  - Yahoo `floatShares` is usable for 485 of 503. 14 report a float above shares outstanding (dual-class names given a combined figure), BRK-B reports 0.001 which would delete Berkshire, 3 are missing
  - Measured TE 2.51 to 2.28bp, but that was before the membership fix and has not been re-run. Treat it as indicative only
  - It does not touch the drift, and there is now almost no drift left to touch, so the case for it is weaker than it was
  - Deferred: it is a current scalar with no history, so applying today's ratio assumes insider stakes never changed
  - S&P uses a banded and rounded Investable Weight Factor anyway, so even perfect float would not reproduce official weights

- No divisor
  - S&P adjusts its divisor on every buyback, issuance and membership change so the published level does not jump on non-price events. We have no divisor, so those events leak into our series
  - Detectable without external data: `(weights.shift(1) * closes.pct_change()).sum(axis=1)` against `caps.sum(axis=1).pct_change()`. Price cancels algebraically between the two, so any difference is a share-count change
  - 443 such days over the window, largest 2024-06-25 at -885.6bp and 2024-06-26 at +843.5bp

- Share filings near split boundaries
  - The split factor is correct, but Yahoo's filing dates do not always sit on the expected side of a split
  - TPL filed a post-split count one day early and a pre-split count on the split date, so our cap read $39.67B then $4.42B against a true ~$13B
  - 67 member-days across 40 tickers move the share count more than 1.5x in a day. Often self-cancelling, so invisible in the cumulative gap but real noise now that TE is 2.51bp
  - `check_share_jumps` reports these. It is a heuristic, not a missing-data check: a genuine large issuance can trip it
  - Fix would be to widen the split boundary a few days and take whichever filing agrees with its neighbours

- Spinoff listing lag
  - 45 member-days across 10 tickers where a company lists and trades before Yahoo files its first share count. PSKY 33d is most of it
  - No old symbol to fall back on, so a fix means carrying the first known value backwards, which asserts a share count for days before it was reported

- Share count timing
  - `get_shares_full` dates values by Yahoo's filing record date, not S&P's effective date
  - Small, and hard to quantify without a point-in-time source

## Other notes

- Methods that did not work
  - Leave-one-out (rebuild without a stock, see if the gap shrinks) is invalid here. The published index still holds that stock, so removing it creates a mismatch by construction, conflating a stock's genuine return contribution with mis-weighting
  - It produced two false leads: MSFT as the cause of 2024, NVDA as the cause of the drift
  - A flat year-by-year TE gradient was read as evidence against survivorship. Wrong test: survivorship shows up as drift in `mean_bp` and the cumulative gap, not as year-to-year noise. Survivorship was in fact the whole of the remaining drift, as the membership fix later showed

- Ruled out
  - MRNA +177% on 2026-08-19: no split, share count unchanged either side. A genuine news move, present in the published index too
  - Blending dual-class prices instead of dropping the second class: 0.1bp
  - Our market caps are not the problem. Cross-checked against Yahoo's own `marketCap` for the nine largest names, every one matches within 1%

- What is not diverging
  - Correlation 0.99978 over 1179 days means the construction is sound: elementwise market cap, row-normalised weights, one-day weight lag, compounding
  - The residual is data quality, not index logic

- Housekeeping
  - `SECOND_CLASS` and `RENAMES` are hardcoded lists found by hand. A new rename or share class will silently reopen the same hole
  - `--refresh` only reaches pipeline.py, so changing `START` and running analysis.py returns the old window from cache
