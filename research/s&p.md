# General Research on the S&P 500 Index

- Market cap: Market capitalization = Current market value of all outstanding stock shares of a company
  - Formula: Market Cap = Share Price x Total number of outstanding shares
  - Outstanding shares only change from corporate actions: Stock issuances, buybacks, stock splits

- Weighting method: Company weighting = Company market cap / Total of all market caps

- Index construction: 
  - Only free-floating shares are used: Shares that are publicly tradeable
  - S&P adjusts each company's market cap to compensate for new share issues or mergers
  - Index's value is calculated by adding each company's adjusted market cap and dividing by a divisor (Not released to public)
  - S&P is not a total return index, doesn't include cash dividend gains for companies

- Rebalancing: Every quarter in March, June, September, December
  - Company weights are adjusted and companies are removed / added
  - Additions and removals also happen off-cycle, whenever a constituent is acquired, merges, or goes private
  - Float is applied as an Investable Weight Factor (IWF), which is banded and rounded rather than raw float, and updated quarterly

- S&P 500 Selection: By a committee
  - Market cap above a certain size
  - At least 250,000 shares traded in past 6 months
  - At least 10% of shares available to public
  - Had IPO at least 1 year earlier
  - Have a positive sum of past 4 quarters of earnings + most recent quarter

- Share classes: A company can have more than one class in the index at the same time
  - Alphabet has both GOOGL (Class A) and GOOG (Class C), Fox has FOXA/FOX, News Corp has NWSA/NWS
  - Each class is weighted by its own float, so the company is counted once in total, split across its classes
  - Class B shares held by founders are typically not in the index, they are not publicly traded

- Index tickers:
  - `^GSPC` is the price-return index, no dividends. This is the headline S&P 500 number quoted in the news
  - `^SP500TR` is the total-return version, reinvests dividends, so it drifts above `^GSPC` by roughly the dividend yield
  - `SPY` and `VOO` are ETFs, not indices. They track the index but carry an expense ratio and their own tracking error

- ETF pricing and arbitrage:
  - An ETF's market price can differ from the value of the basket it holds, but only by a few basis points
  - Authorised Participants keep it tight: they can create and redeem ETF shares in kind, handing the fund a basket of stocks for ETF shares or the reverse
  - That creation/redemption right is what closes the gap, and it is not available to ordinary investors
  - So index-vs-ETF mispricing is not a tradeable edge without AP status

- The index is computed, not priced:
  - The index level is a weighted average of its constituents, defined by them rather than discovered by a market
  - So the index cannot be "mispriced" relative to its own components, there is no fair value to compare it against
  - Any disagreement between a reconstruction and the published level is reconstruction error, not a market signal

- Sources:
  - https://www.investopedia.com/terms/s/sp500.asp
  - https://www.investopedia.com/articles/investing/090414/sp-500-index-you-need-know.asp
