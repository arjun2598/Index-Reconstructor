# Index Reconstructor

## Objective

This is a project aimed at consolidating historical stocks data and reconstructing indices that track
a combined basket of these stocks. Through processing massive financial datasets and validating results or explaining discrepancies, I aim to deepen my understanding of markets and financial data.

## Specification

This project will focus on the S&P 500 Index. I will focus on daily returns, attempting to match the constituent stocks to the Index's returns. To keep the first iteration simple, I will focus on the past 5 years of data from Yahoo Finance, and then increment the time horizon to introduce more complexities that could cause divergence in results.

## Initial Hypotheses

Reproducing the exact returns may be difficult to achieve, but any differences is what I want to explore, and be able to explain. The differences would likely come from the following sources: Inaccurate re-balancing of constituent stocks, missing or inaccurate data, survivorship bias, failure to incorporate stock splits / dividends.

## Actual Observations

I was able to achieve a 0.99974 correlation of daily returns between my reconstruction of the index and the actual data after several iterations. A few key contributing factors to initial divergence were stock splits, addition timings of stocks to the index, and renaming of tickers. While other defects still exist, such as failing to incorporate the companies that previously existed in the index but have since been removed, I believe I have achieved the key objective of this study. Those interested in reading the findings in full can find them in [divergence.md](research/divergence.md). Some background research is also included in [s&p.md](research/s&p.md).