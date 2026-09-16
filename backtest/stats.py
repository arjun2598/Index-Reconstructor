"""Performance measurement."""

import numpy as np
import pandas as pd

from settings import TRADING_DAYS


def equity_curve(returns, base=100.0):
    return base * (1 + returns.fillna(0)).cumprod()


def max_drawdown(returns):
    curve = equity_curve(returns)
    return (curve / curve.cummax() - 1).min()


# Slope against the index, so we can see how much of a return is just market exposure
def beta(returns, market):
    paired = pd.concat([returns, market], axis=1).dropna()
    if len(paired) < 2:
        return np.nan
    
    ours, theirs = paired.iloc[:, 0], paired.iloc[:, 1]
    return ours.cov(theirs) / theirs.var()


def summarise(returns, market, name):
    returns = returns.dropna()
    years = len(returns) / TRADING_DAYS
    total = (1 + returns).prod() - 1
    vol = returns.std() * np.sqrt(TRADING_DAYS)
    b = beta(returns, market)

    return {
        "strategy": name,
        "total_%": total * 100,
        "cagr_%": ((1 + total) ** (1 / years) - 1) * 100,
        "vol_%": vol * 100,
        "sharpe": (returns.mean() * TRADING_DAYS) / vol if vol else np.nan,
        "max_dd_%": max_drawdown(returns) * 100,
        "hit_%": (returns > 0).mean() * 100,
        "beta": b,
        # What is left after stripping the market exposure, annualised
        "alpha_%": (returns.mean() - b * market.reindex(returns.index).mean()) * TRADING_DAYS * 100,
    }


def table(rows):
    return pd.DataFrame(rows).set_index("strategy").round(2)
