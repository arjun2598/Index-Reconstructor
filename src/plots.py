"""Charts for the reconstruction. Writes PNGs to figures/.

    python src/plots.py

Reads the cached data through pipeline.build(), so it needs data/ populated.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

from cleaning import clean_closes, clean_shares
from download import load_raw
from metrics import compare, reconstruct, weights
from pipeline import build

FIG_DIR = Path(__file__).resolve().parent.parent / "figures"

# Colour palettes
OURS = "#2a78d6"
THEIRS = "#eb6834"
INK = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e3e2de"
SURFACE = "#fcfcfb"

# Tracking error after each fix, in the order they were made
FIX_LADDER = [
    ("Naive\nreconstruction", 9.71),
    ("Dual-class\ndedupe", 8.60),
    ("Ticker\nrenames", 7.75),
    ("Split\nadjustment", 4.06),
    ("Addition\ntiming", 2.51),
]

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


# 1. Every fix and its impact
def plot_fix_ladder():
    labels = [l for l, _ in FIX_LADDER]
    values = [v for _, v in FIX_LADDER]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(labels, values, color=OURS, width=0.62)
    bars[0].set_color(MUTED)                    # The starting point is not a fix

    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.15, f"{value:.2f}",
                ha="center", color=INK, fontsize=10, fontweight="600")

    style(ax, "Each fix cut the tracking error",
          "Daily tracking error vs ^GSPC, standard deviation in basis points", "bp")
    ax.set_ylim(0, max(values) * 1.18)
    save(fig, "1_fix_ladder.png")


# 2. The reconstruction against the published index, with the residual below
def plot_tracking(level, benchmark):
    cmp = compare(level, benchmark)
    gap = (cmp["reconstructed"] / cmp["published"] - 1) * 100

    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(9, 5.8), sharex=True, height_ratios=[3, 1], gridspec_kw={"hspace": 0.28}
    )

    top.plot(cmp.index, cmp["published"], color=THEIRS, linewidth=2, label="Published (^GSPC)")
    top.plot(cmp.index, cmp["reconstructed"], color=OURS, linewidth=2, label="Reconstruction")
    style(top, "The reconstruction tracks the index",
          "Both rebased to 100 at 2022-01-03. Correlation of daily returns 0.99974", "Index level")
    top.legend(frameon=False, labelcolor=MUTED, fontsize=9.5, loc="upper left")

    bottom.axhline(0, color=GRID, linewidth=1)
    bottom.fill_between(gap.index, gap, color=OURS, alpha=0.22, linewidth=0)
    bottom.plot(gap.index, gap, color=OURS, linewidth=1.4)
    style(bottom, "", "Cumulative difference, percentage points", "pp")
    bottom.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:+.0f}"))
    save(fig, "2_tracking.png")


# 3. What the split mismatch did to a single weight
def plot_nvda_split(closes, shares, membership):
    raw = load_raw()[2]                         # Filed share counts, before split adjustment
    unadjusted = clean_shares(raw, closes.index)

    def weight_of(share_panel, ticker="NVDA"):
        caps = (closes * share_panel).where(membership)
        return weights(caps)[ticker] * 100

    before, after = weight_of(unadjusted), weight_of(shares)

    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.plot(before.index, before, color=THEIRS, linewidth=2, label="As filed (wrong)")
    ax.plot(after.index, after, color=OURS, linewidth=2, label="Split-adjusted")

    split = pd.Timestamp("2024-06-10")
    ax.axvline(split, color=MUTED, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(split, ax.get_ylim()[1] * 0.97, "  10:1 split", color=MUTED, fontsize=9, va="top")

    style(ax, "Unadjusted share counts hid NVDA's weight",
          "NVDA weight in the reconstruction. Prices are split-adjusted, filed share counts are not",
          "Weight %")
    ax.legend(frameon=False, labelcolor=MUTED, fontsize=9.5, loc="upper left")
    save(fig, "3_nvda_split.png")


# 4. How concentrated the index has become
def plot_concentration(w):
    top10 = w.apply(lambda row: row.nlargest(10).sum(), axis=1) * 100

    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.plot(top10.index, top10, color=OURS, linewidth=2)

    start, end = top10.iloc[0], top10.iloc[-1]
    ax.text(top10.index[-1], end, f"  {end:.0f}%", color=INK, fontsize=10,
            fontweight="600", va="center")

    style(ax, "The index keeps concentrating",
          f"Combined weight of the ten largest companies, {start:.0f}% to {end:.0f}% over the window",
          "Weight %")
    # Zoomed to the data, so no fill: shading to a truncated baseline would overstate the change
    ax.set_ylim(top10.min() - 2, top10.max() + 3)
    save(fig, "4_concentration.png")


if __name__ == "__main__":
    _, closes, shares, benchmark, membership = build()
    caps, w, returns, level = reconstruct(closes, shares, membership)

    print("figures:")
    plot_fix_ladder()
    plot_tracking(level, benchmark)
    plot_nvda_split(closes, shares, membership)
    plot_concentration(w)
