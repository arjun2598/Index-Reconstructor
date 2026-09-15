"""Entry point: rebuild the dataframes, reconstruct the index, and report on it.

    python src/analysis.py
"""

from diagnostics import (
    corporate_action_days,
    coverage,
    late_entrants,
    tracking_by_year,
    worst_days,
)
from metrics import compare, reconstruct, tracking_summary
from pipeline import build


def report_index(caps, w, level):
    print(f"\nTotal market cap: ${caps.iloc[-1].sum() / 1e12:.2f}T")

    print("\nTop 10 weights:")
    print((w.iloc[-1].sort_values(ascending=False).head(10) * 100).round(2))

    print("\nIndex level:")
    print(level.round(2).tail())


def report_tracking(level, benchmark):
    print("\nVs published (^GSPC):")
    print(compare(level, benchmark).round(3).tail())

    s = tracking_summary(level, benchmark)
    print(f"\nOver {s['days']} days: ours {s['ours_%']:+.2f}%, "
          f"published {s['published_%']:+.2f}%, gap {s['gap_bp']:+.1f} bp")
    
    print(f"Daily tracking error: mean {s['te_mean_bp']:+.2f} bp, "
          f"stdev {s['te_stdev_bp']:.2f} bp, worst {s['te_worst_bp']:.1f} bp")
    
    print(f"Correlation of daily returns: {s['correlation']:.5f}")


def report_diagnostics(closes, shares, caps, w, returns, benchmark):
    theirs = benchmark.pct_change()

    print("\nTracking by year:")
    print(tracking_by_year(returns, theirs).round(2))

    print("\nWorst days:")
    print(worst_days(closes, w, returns, theirs).to_string(index=False))

    holes = coverage(closes, shares)
    print(f"\nCoverage holes in {len(holes)} tickers "
          f"({int(holes.priced_but_dropped.sum())} ticker-days priced but dropped for want of shares):")
    print(holes.head(8))

    print("\nTickers starting after the window opens:")
    print(late_entrants(closes).head(8).to_string())

    actions = corporate_action_days(caps, returns)
    print(f"\n{len(actions)} days where share counts moved (weighted vs aggregate return, bp):")
    print(actions.head(5).round(1).to_string())


if __name__ == "__main__":
    _, closes, shares, benchmark = build()
    caps, w, returns, level = reconstruct(closes, shares)

    report_index(caps, w, level)
    report_tracking(level, benchmark)
    report_diagnostics(closes, shares, caps, w, returns, benchmark)
