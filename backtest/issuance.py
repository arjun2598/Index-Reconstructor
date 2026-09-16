"""Net share issuance: the change in a company's share count over the past year

Shrinking share counts mean buybacks, expanding ones mean issuance. Companies that
retire equity have historically outperformed those that print it.

The share panel is split-adjusted, which this depends on. On as-filed counts a 10:1
split would read as 900% issuance and swamp every real signal.
"""

from settings import LOOKBACK_DAYS, MAX_DAILY_SHARE_JUMP


# Names whose share count takes an implausible one-day step, which is a filing landing
# on the wrong side of a split rather than anything the company did
def suspect_data(shares, ratio=MAX_DAILY_SHARE_JUMP):
    step = shares / shares.shift(1)
    jumps = ((step > ratio) | (step < 1 / ratio)) & shares.notna() & shares.shift(1).notna()
    return jumps.rolling(LOOKBACK_DAYS, min_periods=1).max().astype(bool)  # Sticky for the lookback


# Fractional change in share count over the lookback. Negative means a buyback
def net_issuance(shares, lookback=LOOKBACK_DAYS):
    issuance = shares / shares.shift(lookback) - 1
    return issuance.where(~suspect_data(shares))


# The signal we actually rank on, restricted to names we can hold that day
def tradeable_signal(shares, closes, membership):
    signal = net_issuance(shares)
    usable = membership & closes.notna() & shares.notna()
    return signal.where(usable)
