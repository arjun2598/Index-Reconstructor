"""Checks that make data holes obvious.

A missing cell silently drops a stock from that day's index and renormalises the
rest, so nothing downstream can detect it. These checks look at the inputs instead.

Every check is scoped to companies that were index members on the day in question.
"""

from config import INDEX_SIZE, SHARE_JUMP_RATIO, TOP_N


# Cells we can actually use: a member that day, with both a price and a share count
def usable_cells(closes, shares, membership):
    return membership & closes.notna() & shares.notna()


# Members we hold with complete data, each day
def universe_size(closes, shares, membership):
    return usable_cells(closes, shares, membership).sum(axis=1)


# Members whose data is missing, so they silently fall out of the weights
def check_member_coverage(closes, shares, membership):
    holes = membership & (closes.isna() | shares.isna())

    per_ticker = holes.sum()
    per_ticker = per_ticker[per_ticker > 0].sort_values(ascending=False)
    if not len(per_ticker):
        return None

    named = ", ".join(f"{t} {n}d" for t, n in per_ticker.head(5).items())
    return (
        f"{int(holes.sum().sum())} member-days have no market cap "
        f"across {len(per_ticker)} tickers: {named}"
    )


# How far our modelled membership falls short of the real index
def check_index_size(membership, size=INDEX_SIZE):
    members = membership.sum(axis=1)
    short = size - members
    if short.max() <= 0:
        return None

    return (
        f"we model {members.min()}-{members.max()} members against the index's {size}, "
        f"short by up to {short.max()} on {short.idxmax().date()}. "
        f"These are companies removed from the index, which we are yet to recover"
    )


# A dropped mega-cap costs far more than a dropped small-cap
def check_big_names(closes, shares, membership, top_n=TOP_N):
    usable = usable_cells(closes, shares, membership)
    biggest = (closes.iloc[-1] * shares.iloc[-1]).nlargest(top_n).index  # Last row has the best coverage
    absent = (membership[biggest] & ~usable[biggest]).sum()
    absent = absent[absent > 0].sort_values(ascending=False)
    if not len(absent):
        return None

    named = ", ".join(f"{t} {n}d" for t, n in absent.head(5).items())
    return f"{len(absent)} of the top {top_n} names are missing while members: {named}"


# Complete prices paired with missing share counts, usually when tickers are renamed
def check_priced_without_shares(closes, shares, membership):
    counts = (membership & closes.notna() & shares.isna()).sum()
    counts = counts[counts > 0].sort_values(ascending=False)
    if not len(counts):
        return None

    named = ", ".join(f"{t} {n}d" for t, n in counts.head(5).items())
    return (
        f"{int(counts.sum())} member-days have a price but no share count "
        f"across {len(counts)} tickers: {named}"
    )


# Share counts that jump implausibly far in one day, usually a filing landing on the
# wrong side of a split date rather than a real issuance
def check_share_jumps(shares, membership, ratio=SHARE_JUMP_RATIO):
    step = shares / shares.shift(1)
    jumps = ((step > ratio) | (step < 1 / ratio)) & shares.notna() & shares.shift(1).notna()
    jumps &= membership

    per_ticker = jumps.sum()
    per_ticker = per_ticker[per_ticker > 0].sort_values(ascending=False)
    if not len(per_ticker):
        return None

    named = ", ".join(f"{t} {n}d" for t, n in per_ticker.head(5).items())
    return (
        f"{int(jumps.sum().sum())} member-days move share count more than {ratio}x "
        f"across {len(per_ticker)} tickers: {named}"
    )


# Run every check, returning the daily universe and whatever went wrong
def validate(closes, shares, membership):
    warnings = [
        check_index_size(membership),
        check_member_coverage(closes, shares, membership),
        check_big_names(closes, shares, membership),
        check_priced_without_shares(closes, shares, membership),
        check_share_jumps(shares, membership),
    ]
    return universe_size(closes, shares, membership), [w for w in warnings if w]


# Print the checks as part of a pipeline run
def report(universe, warnings):
    print(
        f"checks: members with usable data per day, min {universe.min()}, "
        f"median {int(universe.median())}, max {universe.max()}"
    )
    for warning in warnings:
        print(f"  WARN  {warning}")
    if not warnings:
        print("  all clear")
