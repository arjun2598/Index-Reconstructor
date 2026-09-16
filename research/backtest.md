# Backtest: net share issuance

## The idea

- Rank every index member by how much its share count changed over the past year, then long the biggest shrinkers and short the biggest growers
- Shrinking means buybacks, growing means issuance: stock sold to fund acquisitions, pay staff in equity, or raise capital
- Chosen because the signal IS the data engineering. The share panel is split-adjusted, rename-corrected and membership-scoped, and on raw filed counts a 10:1 split reads as +900% issuance, so every splitter would land in the short leg and the strategy would be a split detector
- It is not event driven. Every company has a score every day and positions come from ranking, not from a share count changing

## Why the literature expects this to work

- Net share issuance is a documented anomaly. Firms that issue equity subsequently underperform, firms that repurchase outperform
- Loughran and Ritter (1995) on the "new issues puzzle", Ikenberry, Lakonishok and Vermaelen (1995) on buyback announcements, Daniel and Titman (2006) on the intangible-return component, Pontiff and Woodgate (2008) showing share issuance predicts cross-sectional returns
- Fama and French (2015) folded it into the five-factor model as CMA, the investment factor. Share issuance is one of the cleanest observable proxies for corporate investment: firms that raise capital are expanding, and aggressive investors have historically earned lower returns than conservative ones
- So CMA is the closest published factor to this strategy. The expectation going in was a small positive return with low market beta, not a large one
- The usual explanations are that managers time issuance when their stock is expensive, and that investors underreact to the dilution

## Construction

- Signal: `shares(t) / shares(t - 252) - 1`, negative for buybacks
- Universe: index members on that day with both a price and a share count, about 400-490 names
- Legs: bottom decile long, top decile short, equal weight inside each leg, each leg summing to 1.0. Dollar neutral, gross exposure 2.0 per unit of capital
- Rebalance: month end. Positions are held between rebalances, and `hold()` shifts by a day so a position never earns the return that selected it
- Costs: 5bp one way on everything traded, plus 50bp a year borrow on short notional. See the cost assumptions section below
- No stop loss, no take profit. A position leaves only when it drops out of its decile at the next rebalance

## The suspect-data guard

- The signal is a ratio across 252 days, so one bad share print corrupts it for a full year, not just the day it lands
- Any name whose share count moves more than 1.5x in a single day is excluded for the whole lookback, using `jumps.rolling(252).max()`
- Without it PSKY would have read +21,537% issuance, sitting at the top of the short leg every day for a year and crowding out a real issuer
- Removes 41,079 ticker-days across 140 of 716 tickers, concentrated in renames and split-boundary artifacts
- Cost of the guard: a genuine large issuance, such as an all-stock merger, is excluded too. Deliberate, since ranks decide everything and one corrupted value takes a slot from a real name

## Cost assumptions

- Quoted in basis points because the differences matter at a scale where percentages become unreadable. 1bp = 0.01% = 0.0001. Tracking error of 0.000330 is hard to read, 3.30bp is not, and it is the unit the industry uses for spreads, fees and tracking error

- Trading cost, 5bp one way
  - Bid-ask spreads on US large caps run about 2-3bp of traded value ([Frec, direct indexing transaction costs](https://frec.com/resources/blog/direct-indexing-transaction-costs))
  - On top of that sit commissions, exchange fees and market impact, which for institutional orders is often the largest component ([Keim and Madhavan, "The Cost of Institutional Equity Trades", Financial Analysts Journal 1998](https://www.hillsdaleinv.com/uploads/The_Cost_of_Institutional_Equity_Trades,_Donald_B._Keim,_Ananth_Madhaven,_Financial_Analysts_Journal,_JulyAugust_1998,_Pages_50-69.pdf))
  - 5bp is roughly spread plus a modest allowance for the rest. Reasonable for S&P 500 names at modest size, optimistic for a large book

- Borrow cost, 50bp a year
  - S&P 500 constituents are almost always general collateral, meaning plentiful supply from index lenders. D'Avolio (2002) puts the value-weighted mean general collateral fee at 17bp ([The market for borrowing stock, Journal of Financial Economics](https://www.sciencedirect.com/science/article/abs/pii/S0304405X02002064))
  - Broker quotes for general collateral names typically run 25-100bp a year ([Interactive Brokers, short sale cost](https://www.interactivebrokers.com/en/pricing/short-sale-cost.php))
  - 50bp sits mid-range and about 3x D'Avolio's mean, so it is deliberately conservative

- Sensitivity, on the 2016 window
  - Zero costs: 2.23% CAGR, Sharpe 0.26
  - Optimistic 3bp / 17bp: 1.82% CAGR, Sharpe 0.23, costs 4.31pp
  - Baseline 5bp / 50bp: 1.35% CAGR, Sharpe 0.18, costs 9.25pp
  - Pessimistic 10bp / 100bp: 0.47% CAGR, Sharpe 0.10, costs 18.51pp
  - The conclusion does not depend on the assumption. Even at zero costs Sharpe is 0.26, so the strategy loses to buy and hold on every setting

## Results, 2017-02 to 2026-09, net of costs

- 9.6 years of live trading. The first year of data is consumed by the 252-day lookback

| | total % | CAGR % | vol % | Sharpe | max DD % | beta | alpha % |
|---|---|---|---|---|---|---|---|
| L/S gross | 26.51 | 2.48 | 10.91 | 0.28 | -24.11 | -0.01 | 3.22 |
| L/S net | 15.33 | 1.50 | 10.91 | 0.19 | -25.79 | -0.01 | 2.25 |
| Long only net | 202.87 | 12.24 | 21.09 | 0.65 | -43.15 | 1.00 | -0.41 |
| Buy and hold S&P 500 | 232.76 | 13.35 | 18.34 | 0.78 | -33.92 | 1.00 | 0.00 |

- Turnover 9.1x a year. Costs took 9.25pp of 29.22pp gross, about a third
- By year, net: 2017 +5.12, 2018 -11.43, 2019 +2.10, 2020 -5.91, 2021 +4.82, 2022 +10.97, 2023 +7.93, 2024 +7.00, 2025 +0.61, 2026 -4.61

## What the results say

- The strategy does not beat buy and hold. 1.50% a year against 13.35%, Sharpe 0.19 against 0.78. As a standalone strategy it is not worth running
- Beta is -0.01, so it is genuinely market neutral rather than approximately. Alpha 2.25% a year net
- The long leg has no edge at all: alpha -0.41%, more volatile than the index (21.09% vs 18.34%) with a much worse drawdown (-43% vs -34%)
- That follows from the distribution. On a typical day 69% of index members shrank their share count and the median was -1.2%, so buying back stock is the norm and carries almost no information. Issuance is the abnormal behaviour, and the deciles cut at -6.3% and +1.6%
- So whatever signal exists is in the short leg. That flips the usual "buyback anomaly" framing
- It behaves like a real factor even where it does not pay: the two worst years, 2018 and 2020, were sharp-reversal years, and 2022 returned +10.97% while the index fell 19.44%
- Sharpe 0.19 over 116 rebalances is not distinguishable from zero. The honest conclusion is that CMA-style issuance does not survive costs in this window, not that it has been disproved

## Survivorship bias, measured

- The same code run on the old survivorship-biased universe, before point-in-time membership, on the 2022 window:

| | biased universe | point-in-time |
|---|---|---|
| L/S net CAGR | 3.81% | 2.86% |
| L/S net Sharpe | 0.39 | 0.31 |
| Long only alpha | 3.44% | 1.86% |

- Survivorship inflated the long/short Sharpe by about 21% and nearly halved the long book's apparent alpha
- Only the universe changed. This is the clearest demonstration in the project of why point-in-time data matters

## Rebalance frequency

| | gross CAGR % | net CAGR % | Sharpe | turnover/yr | costs pp |
|---|---|---|---|---|---|
| Monthly | 2.48 | 1.50 | 0.19 | 9.1 | 9.25 |
| Weekly | 1.92 | 0.22 | 0.07 | 23.4 | 16.24 |
| Daily | 0.20 | -3.14 | -0.23 | 57.7 | 32.82 |

- Daily rebalancing turns +1.50% a year into -3.14%
- Gross return falls too, 2.48% to 0.20%, so this is not only a cost story. Re-ranking daily chases noise at the decile boundary and cuts short the slower drift the signal is meant to capture
- Only about 77 of 408 names have a signal value that changes at all on a given day, because share counts update on filings. Daily rebalancing re-cuts an unchanged ranking and pays spread for it
- Realistic means matched to how fast the information arrives. For a filing-based signal that is monthly, and quarterly would be defensible

## Positions

- Book is 48 long and 48 short at full size, 2.08% each, from a universe of about 484
- 79% of the book carries over each month, roughly 17 names swapped
- Median holding is 2 months, mean 5.3. Longest unbroken runs are O (96 months), ATO (68), ARE (63), WELL (59), EBAY (53), mostly REITs and utilities that issue equity persistently
- Example snapshot, 2026-08-31. Longs: ARES -30.97%, BDX -25.29%, FDX -19.17%. Shorts: HBAN +38.49%, LITE +28.33%, COHR +25.69%

## Known limitations

- Sharpe 0.19 over 9.6 years and 116 rebalances cannot be distinguished from zero. Everything above should be read as "no edge found", not "edge measured"
- Yahoo's dating convention for share counts is unknown. Observations are not quarterly filings, only 0.6% land on quarter ends, so we cannot tell whether a value dated day X was knowable on day X or backfilled. If backfilled there is lookahead the backtest cannot detect
- Costs are modelled, not measured. 5bp and 50bp are plausible for large caps but no market impact model, no borrow availability constraint, no short squeeze risk
- Roughly 3% of index members are unpriceable (acquired, failed, taken private), so they are absent from both the universe and the legs
- The 2016 floor is a data limit, not a choice: `get_shares_full` returns nothing before October 2015

## If this were taken further

- Sector-neutral ranking, so the short leg is not just an implicit bet against REITs and utilities
- Separate the signal into buybacks and issuance and test them independently, since the evidence says only one side carries information
- A holding period longer than a month, given the signal updates on filings
- Cross-check share counts against a second source before trusting a signal built on one vendor's dating convention
