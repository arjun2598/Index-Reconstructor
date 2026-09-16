"""Running the book day by day

Positions are set on rebalance dates from the signal as it stood that day, then held.
`hold()` shifts by one day so a position never earns the return that selected it.
"""

import pandas as pd

from costs import borrow_cost, trading_cost
from portfolio import build_positions, hold
from issuance import tradeable_signal


# Every rebalance date that falls inside the trading calendar
def rebalance_dates(index, freq):
    marks = pd.Series(index, index=index).resample(freq).last().dropna()
    return pd.DatetimeIndex(marks.values)


def run(closes, shares, membership, freq):
    signal = tradeable_signal(shares, closes, membership)
    targets = build_positions(signal, rebalance_dates(closes.index, freq))
    held = hold(targets, closes.index)

    stock_returns = closes.pct_change().reindex(columns=held.columns)
    gross = (held * stock_returns).sum(axis=1, min_count=1)

    costs = trading_cost(held) + borrow_cost(held)
    return pd.DataFrame({
        "gross": gross,
        "cost": costs,
        "net": gross - costs,
        "long_names": (held > 0).sum(axis=1),
        "short_names": (held < 0).sum(axis=1),
    })
