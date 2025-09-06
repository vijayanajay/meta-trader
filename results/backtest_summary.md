
## Backtest Report

### Run Configuration & Metadata
| Parameter | Value |
| --- | --- |
| Run Timestamp | 2025-09-06 09:21:07 UTC |
| Config File | `config.test.ini` |
| Git Commit Hash | `38a57ea` |

**Period:** 2018-01-01 to 2025-08-25
**Total Trades:** 25


### Filtering Funnel
| Stage | Count | % of Previous Stage |
| --- | --- | --- |
| Potential Signals | 26 | 100.00% |
| Survived Guardrails | 25 | 96.15% |
| Survived LLM Audit | 25 | 100.00% |
| Trades Executed | 25 | 100.00% |


### Guardrail Rejection Analysis
| Guardrail | Rejection Count | % of Total Guard Rejections |
| --- | --- | --- |
| StatGuard | 1 | 100.00% |


### Key Performance Indicators
| Metric | Value |
| --- | --- |
| Net Annualized Return | 12.57% |
| Sharpe Ratio | 0.67 |
| Profit Factor | 3.11 |
| Maximum Drawdown | -27.05% |
| Win Rate | 64.00% |

### Trade Distribution Analysis
| Metric | Value |
| --- | --- |
| Avg. Holding Period | 34.36 days |
| Avg. Win | 10.53% |
| Avg. Loss | -6.03% |
| Best Trade | 14.53% |
| Worst Trade | -12.89% |
| Skewness | -0.62 |
| Kurtosis | -1.20 |

### Net Return (%) Distribution
```
 -12.89 - -10.15  | ████ (1)
 -10.15 - -7.41   | ████ (1)
  -7.41 - -4.66   | █████████████████████████ (6)
  -4.66 - -1.92   |  (0)
  -1.92 - 0.82    | ████ (1)
   0.82 - 3.56    |  (0)
   3.56 - 6.30    | ████ (1)
   6.30 - 9.04    | ████████████ (3)
   9.04 - 11.78   | ██████████████████████████████ (7)
  11.78 - 14.53   | █████████████████████ (5)
```


### Per-Stock Performance Breakdown

| Stock | Compounded Return | Total Trades | Potential Signals | Rejections by Guard | Rejections by LLM |
|---|---|---|---|---|---|
| POWERGRID.NS | 181.12% | 25 | 26 | 1 | 0 |