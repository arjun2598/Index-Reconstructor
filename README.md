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

## Result Visualisations

Each iteration removed a defect and tightened the tracking error. The basic reconstruction was at 9.71bp of daily tracking error against the published index while the latest one sits at 2.51bp.

![Daily tracking error after each fix](figures/1_fix_ladder.png)

Plotted against the published index, the two series are hard to tell apart. The panel underneath shows the cumulative difference, which is where the remaining bias is visible: it opens through 2023 and settles near +2 percentage points, most likely the companies removed from the index that are missing from my data.

![Reconstruction against the published index](figures/2_tracking.png)

The largest single error was stock splits. Yahoo returns prices that are split-adjusted all the way back, but share counts as they were filed at the time, so market cap was wrong by the split ratio for every day before a split. NVDA was carried at roughly a tenth of its true weight through the period it led the market.

![NVDA weight before and after the split adjustment](figures/3_nvda_split.png)

With the reconstruction working, the weights themselves become worth looking at. The ten largest companies have gone from a third of the index to two fifths over the window.

![Combined weight of the ten largest companies](figures/4_concentration.png)
