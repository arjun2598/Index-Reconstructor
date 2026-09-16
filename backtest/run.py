"""Net share issuance, backtested against buy-and-hold S&P 500

    python backtest/run.py

Loads the cached data from the reconstruction pipeline in src/.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src")) # Include src directory to build dataframes

import pandas as pd

from costs import trading_cost, turnover
from engine import rebalance_dates, run
from issuance import tradeable_signal
from pipeline import build
from portfolio import build_positions, hold
from settings import BORROW_BPS_ANNUAL, COST_BPS, DECILE, LOOKBACK_DAYS, REBALANCE
from stats import summarise, table


# The buyback leg on its own, fully invested and unlevered, to see whether the
# short side earns its keep
def long_only(closes, targets):
    longs = targets.clip(lower=0)
    longs = longs.div(longs.sum(axis=1), axis=0).fillna(0.0)    # Rescale to 1.0 gross
    held = hold(longs, closes.index)

    gross = (held * closes.pct_change().reindex(columns=held.columns)).sum(axis=1, min_count=1)
    return gross - trading_cost(held)


if __name__ == "__main__":
    _, closes, shares, benchmark, membership = build()
    market = benchmark.pct_change()

    signal = tradeable_signal(shares, closes, membership)
    targets = build_positions(signal, rebalance_dates(closes.index, REBALANCE))
    held = hold(targets, closes.index)

    result = run(closes, shares, membership, REBALANCE)
    longs = long_only(closes, targets)

    print(f"\nnet share issuance | {LOOKBACK_DAYS}d lookback | {DECILE:.0%} legs "
          f"| {REBALANCE} rebalance | {COST_BPS}bp trade, {BORROW_BPS_ANNUAL}bp/yr borrow")

    # Nothing trades until the lookback fills, so measure every series over the live
    # window only. Leaving the flat year in would understate vol and beta alike
    live = result.index[result.long_names > 0]
    trim = lambda series: series.loc[live.min():]

    print(f"book: {int(result.long_names.max())} long, {int(result.short_names.max())} short")
    print(f"data from {closes.index.min().date()}, trading {live.min().date()} to "
          f"{live.max().date()} once the {LOOKBACK_DAYS}d lookback fills")

    market = trim(market)
    rows = [
        summarise(trim(result["gross"]), market, "issuance L/S (gross)"),
        summarise(trim(result["net"]), market, "issuance L/S (net)"),
        summarise(trim(longs), market, "issuance long only (net)"),
        summarise(market, market, "buy and hold S&P 500"),
    ]
    print("\n" + table(rows).to_string())

    print(f"\nturnover {turnover(trim(held)).mean() * 252:.1f}x a year, "
          f"costs {trim(result['cost']).sum() * 100:.2f}pp against "
          f"{trim(result['gross']).sum() * 100:.2f}pp gross")

    compound = lambda s: ((1 + s.fillna(0)).prod() - 1) * 100
    print("\nby year, net of costs (%):")
    print(pd.DataFrame({
        "L/S": trim(result["net"]).groupby(trim(result["net"]).index.year).apply(compound),
        "long only": trim(longs).groupby(trim(longs).index.year).apply(compound),
        "S&P 500": market.groupby(market.index.year).apply(compound),
    }).round(2).to_string())
