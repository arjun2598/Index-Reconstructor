# Index Reconstructor

## Objective

This is a project aimed at consolidating historical stocks data and reconstructing indices that track
a combined basket of these stocks. Through processing massive financial datasets and validating results or explaining discrepancies, I aim to deepen my understanding of markets and financial data.

## Specification

This project will focus on the S&P 500 Index. I will focus on daily returns, attempting to match the constituent stocks to the Index's returns. To keep the first iteration simple, I will focus on the past 5 years of data from Yahoo Finance, and then increment the time horizon to introduce more complexities that could cause divergence in results.

## Initial Hypotheses

Reproducing the exact returns may be difficult to achieve, but any differences is what I want to explore, and be able to explain. The differences would likely come from the following sources: Inccurate re-balancing of constituent stocks, missing or inaccurate data, survivorship bias, failure to incorporate stock splits / dividends.
