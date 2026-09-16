"""Charts for the net share issuance backtest. Writes PNGs to figures/.

    python backtest/plots.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from costs import turnover
from engine import rebalance_dates, run
from issuance import tradeable_signal
from pipeline import build
from portfolio import build_positions, hold, positions_from
from run import long_only
from settings import DECILE, REBALANCE
from stats import equity_curve

FIG_DIR = Path(__file__).resolve().parent.parent / "figures"

# Same validated palette as the reconstruction charts
STRAT = "#2a78d6"       # blue
MARKET = "#eb6834"      # orange
THIRD = "#1baf7a"       # aqua
INK = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e3e2de"
SURFACE = "#fcfcfb"


def style(ax, title, subtitle=None, ylabel=None):
    ax.set_facecolor(SURFACE)
    ax.figure.set_facecolor(SURFACE)
    ax.set_title(title, color=INK, fontsize=13, fontweight="600", loc="left", pad=18 if subtitle else 8)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=MUTED, fontsize=9.5)
    if ylabel:
        ax.set_ylabel(ylabel, color=MUTED, fontsize=9.5)

    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)


def save(fig, name):
    FIG_DIR.mkdir(exist_ok=True)
    fig.savefig(FIG_DIR / name, dpi=200, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    print(f"  wrote {name}")


# 5. What a pound in each strategy became
def plot_equity(result, longs, market, live):
    trim = lambda s: s.loc[live.min():]
    series = {
        "Buy and hold S&P 500": (trim(market), MARKET),
        "Issuance long only": (trim(longs), THIRD),
        "Issuance long/short": (trim(result["net"]), STRAT),
    }

    fig, ax = plt.subplots(figsize=(9, 4.8))
    for label, (returns, colour) in series.items():
        curve = equity_curve(returns)
        ax.plot(curve.index, curve, color=colour, linewidth=2, label=label)
        ax.text(curve.index[-1], curve.iloc[-1], f"  {curve.iloc[-1]:.0f}",
                color=colour, fontsize=10, fontweight="600", va="center")

    style(ax, "The long/short barely moves, and the index wins",
          "Growth of 100, net of costs. Long/short is dollar neutral so it earns no market return",
          "Value of 100")
    ax.legend(frameon=False, labelcolor=MUTED, fontsize=9.5, loc="upper left")
    save(fig, "5_backtest_equity.png")


# 6. Why the rebalance choice matters
def plot_rebalance(closes, shares, membership, market):
    rows = []
    for label, freq in [("Monthly", "ME"), ("Weekly", "W"), ("Daily", "D")]:
        result = run(closes, shares, membership, freq)
        live = result.index[result.long_names > 0]
        trim = lambda s: s.loc[live.min():]
        held = hold(build_positions(tradeable_signal(shares, closes, membership),
                                    rebalance_dates(closes.index, freq)), closes.index)
        years = len(trim(result)) / 252
        rows.append({
            "label": label,
            "gross": ((1 + trim(result["gross"])).prod() ** (1 / years) - 1) * 100,
            "net": ((1 + trim(result["net"])).prod() ** (1 / years) - 1) * 100,
            "turnover": turnover(trim(held)).mean() * 252,
        })
    table = pd.DataFrame(rows)

    fig, (left, right) = plt.subplots(1, 2, figsize=(10, 4.4), gridspec_kw={"wspace": 0.3})
    x = np.arange(len(table))
    left.bar(x - 0.19, table["gross"], width=0.36, color=THIRD, label="Gross")
    left.bar(x + 0.19, table["net"], width=0.36, color=STRAT, label="Net of costs")
    left.axhline(0, color=GRID, linewidth=1)
    left.set_xticks(x, table["label"])
    style(left, "Trading more often destroys it", "Annualised return", "% a year")
    left.legend(frameon=False, labelcolor=MUTED, fontsize=9)

    right.bar(x, table["turnover"], width=0.5, color=MUTED)
    for i, v in enumerate(table["turnover"]):
        right.text(i, v + 1, f"{v:.0f}x", ha="center", color=INK, fontsize=10, fontweight="600")
    right.set_xticks(x, table["label"])
    style(right, "Because turnover explodes", "Book turned over per year", "times")
    save(fig, "6_rebalance_frequency.png")


# 7. Where the deciles cut, and why shrinking alone means nothing
def plot_signal(signal, date):
    scores = signal.loc[date].dropna() * 100
    positions = positions_from(signal.loc[date])
    long_cut = scores[positions[positions > 0].index].max()
    short_cut = scores[positions[positions < 0].index].min()

    fig, ax = plt.subplots(figsize=(9, 4.6))
    clipped = scores.clip(-25, 25)
    ax.hist(clipped, bins=70, color=MUTED, alpha=0.35, linewidth=0)
    ax.hist(clipped[clipped <= long_cut], bins=70, range=(-25, 25), color=STRAT, linewidth=0, label="Long leg")
    ax.hist(clipped[clipped >= short_cut], bins=70, range=(-25, 25), color=MARKET, linewidth=0, label="Short leg")

    ax.axvline(0, color=INK, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(0, ax.get_ylim()[1] * 0.96, f"  {(scores < 0).mean() * 100:.0f}% of companies shrank",
            color=INK, fontsize=9.5, va="top")

    style(ax, "Buying back stock is normal, so only the extremes carry information",
          f"Net share issuance across {len(scores)} index members on {date.date()}, "
          f"clipped at +/-25%. Deciles cut at {long_cut:.1f}% and {short_cut:+.1f}%",
          "Companies")
    ax.set_xlabel("Net share issuance over the past year, %", color=MUTED, fontsize=9.5)
    ax.legend(frameon=False, labelcolor=MUTED, fontsize=9.5)
    save(fig, "7_signal_distribution.png")


# 8. How long a name stays in the book
def plot_holding(targets, stocks):
    inbook = targets != 0
    runs, longest = [], {}
    for ticker in inbook.columns:
        streak = 0
        for held_today in inbook[ticker].values:
            if held_today:
                streak += 1
            elif streak:
                runs.append(streak)
                longest[ticker] = max(longest.get(ticker, 0), streak)
                streak = 0
        if streak:
            runs.append(streak)
            longest[ticker] = max(longest.get(ticker, 0), streak)

    runs = pd.Series(runs)
    top = pd.Series(longest).sort_values().tail(10)
    names = dict(zip(stocks["Ticker"], stocks["Security"]))

    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"wspace": 0.45})
    left.hist(runs, bins=range(1, int(runs.max()) + 2), color=STRAT, linewidth=0)
    style(left, "Most positions are short-lived",
          f"Consecutive months in the book. Median {runs.median():.0f}, mean {runs.mean():.1f}", "Positions")
    left.set_xlabel("Months held", color=MUTED, fontsize=9.5)

    right.barh(range(len(top)), top.values, color=STRAT, height=0.65)
    right.set_yticks(range(len(top)), [f"{t}  {names.get(t, '')[:16]}" for t in top.index])
    for i, v in enumerate(top.values):
        right.text(v + 0.7, i, f"{v}", va="center", color=INK, fontsize=9.5, fontweight="600")
    style(right, "The longest holds", "Longest unbroken run in the book", None)
    right.set_xlabel("Months", color=MUTED, fontsize=9.5)
    right.grid(axis="y", linewidth=0)
    save(fig, "8_holding_periods.png")


if __name__ == "__main__":
    stocks, closes, shares, benchmark, membership = build()
    market = benchmark.pct_change()

    signal = tradeable_signal(shares, closes, membership)
    targets = build_positions(signal, rebalance_dates(closes.index, REBALANCE))
    result = run(closes, shares, membership, REBALANCE)
    longs = long_only(closes, targets)
    live = result.index[result.long_names > 0]

    print("figures:")
    plot_equity(result, longs, market, live)
    plot_rebalance(closes, shares, membership, market)
    plot_signal(signal, pd.Timestamp("2026-08-31"))
    plot_holding(targets.loc[(targets != 0).any(axis=1)], stocks)
