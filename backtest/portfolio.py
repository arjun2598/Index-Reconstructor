"""Turning a signal into positions

Long the biggest buybacks, short the biggest issuers, equal weight inside each leg
and equal dollars across them.
"""

import pandas as pd

from settings import DECILE


# Equal-weight long/short positions from one row of the signal
def positions_from(scores, decile=DECILE):
    scores = scores.dropna()
    n = int(len(scores) * decile)
    if n < 2:
        return pd.Series(dtype="float64")   # Too few names to form two legs

    ranked = scores.sort_values()
    longs = ranked.index[:n]                # Most negative issuance, the buybacks
    shorts = ranked.index[-n:]              # Most positive, the issuers

    weights = pd.Series(0.0, index=scores.index)
    weights[longs] = 1.0 / n                # Each leg sums to 1, so the book is dollar neutral
    weights[shorts] = -1.0 / n
    return weights[weights != 0]


# Target positions on every rebalance date, as a dates x tickers frame
def build_positions(signal, rebalance_dates):
    rows = {d: positions_from(signal.loc[d]) for d in rebalance_dates}
    return pd.DataFrame(rows).T.reindex(columns=signal.columns).fillna(0.0)


# Positions held on each trading day, carried forward between rebalances
def hold(targets, index):
    return targets.reindex(index).ffill().fillna(0.0).shift(1)  # Yesterday's book earns today
