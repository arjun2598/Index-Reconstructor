# Strategy and cost parameters

LOOKBACK_DAYS = 252         # One trading year of share-count change
DECILE = 0.10               # Fraction of the universe held in each leg

# A share count that moves this far in a single day inside the lookback is a filing
# landing on the wrong side of a split, not a corporate action. Exclude those names
# rather than let a data artifact decide a position.
MAX_DAILY_SHARE_JUMP = 1.5

# ----- rebalancing -----

REBALANCE = "ME"            # Month end. Share counts change on filings, so the signal moves slowly

# ----- costs -----

COST_BPS = 5.0              # One-way commission plus spread and impact, per dollar traded
BORROW_BPS_ANNUAL = 50.0    # Stock loan fee on short notional. S&P names are generally easy to borrow
TRADING_DAYS = 252
