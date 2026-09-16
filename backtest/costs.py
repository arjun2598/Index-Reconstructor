"""What trading the book costs

Two charges: a one-way cost on everything traded, and a borrow fee on short notional
held overnight.
"""

from settings import BORROW_BPS_ANNUAL, COST_BPS, TRADING_DAYS


# Fraction of capital traded each day, summed across names
def turnover(held):
    return held.diff().abs().sum(axis=1).fillna(0.0)


# Commission, spread and impact on whatever we traded
def trading_cost(held, bps=COST_BPS):
    return turnover(held) * bps / 10_000


# Stock loan fee, charged daily on the short side only
def borrow_cost(held, annual_bps=BORROW_BPS_ANNUAL):
    short_notional = held.clip(upper=0).abs().sum(axis=1)
    return short_notional * (annual_bps / 10_000) / TRADING_DAYS
