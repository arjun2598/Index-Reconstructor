"""Checks that make data holes obvious.

A missing cell silently drops a stock from that day's index and renormalises the
rest, so nothing downstream can detect it. These checks look at the inputs instead.
"""

from config import MIN_UNIVERSE, SHARE_JUMP_RATIO, TOP_N


# Cells usable for market cap: both price and share count present
def live_cells(closes, shares):
    return closes.notna() & shares.notna()


# How many names actually contribute on each day
def universe_size(closes, shares):
    return live_cells(closes, shares).sum(axis=1)


# Fewer names than the index really holds
def check_universe(universe, min_universe=MIN_UNIVERSE):
    short = universe[universe < min_universe]
    if not len(short):
        return None
    
    return (
        f"universe below {min_universe} on {len(short)} of {len(universe)} days "
        f"(min {universe.min()} on {universe.idxmin().date()})"
    )


# A dropped mega-cap costs far more than a dropped small-cap
def check_big_names(closes, shares, top_n=TOP_N):
    live = live_cells(closes, shares)
    biggest = (closes.iloc[-1] * shares.iloc[-1]).nlargest(top_n).index  # Last row has the best coverage
    absent = (~live[biggest]).sum()
    absent = absent[absent > 0].sort_values(ascending=False)
    if not len(absent):
        return None

    named = ", ".join(f"{t} {n}d" for t, n in absent.head(5).items())
    return f"{len(absent)} of the top {top_n} names are missing on some days: {named}"


# Complete prices paired with missing share counts, usually when tickers are renamed
def check_priced_without_shares(closes, shares):
    counts = (closes.notna() & shares.isna()).sum()
    counts = counts[counts > 0].sort_values(ascending=False)
    if not len(counts):
        return None

    named = ", ".join(f"{t} {n}d" for t, n in counts.head(5).items())
    return (
        f"{int(counts.sum())} ticker-days have a price but no share count "
        f"across {len(counts)} tickers: {named}"
    )


# Tickers that did not exist when the window opened
def check_late_entrants(closes):
    first = closes.apply(lambda c: c.first_valid_index())
    late = first[first > closes.index[0]].sort_values()
    if not len(late):
        return None

    named = ", ".join(f"{t} {d.date()}" for t, d in late.head(5).items())
    return f"{len(late)} tickers have no price at the window start: {named}"


# Share counts that jump implausibly far in one day, usually a filing landing on the
# wrong side of a split date rather than a real issuance
def check_share_jumps(shares, ratio=SHARE_JUMP_RATIO):
    step = shares / shares.shift(1)
    jumps = ((step > ratio) | (step < 1 / ratio)) & shares.notna() & shares.shift(1).notna()

    per_ticker = jumps.sum()
    per_ticker = per_ticker[per_ticker > 0].sort_values(ascending=False)
    if not len(per_ticker):
        return None

    named = ", ".join(f"{t} {n}d" for t, n in per_ticker.head(5).items())
    return (
        f"{int(jumps.sum().sum())} stock-days move share count more than {ratio}x "
        f"across {len(per_ticker)} tickers: {named}"
    )


# Run every check, returning the daily universe and whatever went wrong
def validate(closes, shares):
    universe = universe_size(closes, shares)
    warnings = [
        check_universe(universe),
        check_big_names(closes, shares),
        check_priced_without_shares(closes, shares),
        check_late_entrants(closes),
        check_share_jumps(shares),
    ]
    return universe, [w for w in warnings if w]     # Drop the checks that passed


# Print the checks as part of a pipeline run
def report(universe, warnings):
    print(
        f"checks: usable names per day min {universe.min()}, "
        f"median {int(universe.median())}, max {universe.max()}"
    )
    for warning in warnings:
        print(f"  WARN  {warning}")
    if not warnings:
        print("  all clear")
