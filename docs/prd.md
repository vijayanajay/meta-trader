# **Project Name:** "Praxis" - An Indian Market Mean-Reversion Engine

## Intro

This document outlines the requirements for "Praxis," a quantitative trading system designed to identify and capitalize on high-probability mean-reversion opportunities within the Indian stock market (NSE). The system's core philosophy is not to predict prices, but to apply a cascade of statistical and market-regime filters to isolate asymmetric risk-reward scenarios. It explicitly rejects the notion of "guaranteed returns," focusing instead on a disciplined, evidence-based approach to trading that accounts for the unique structural realities of Indian markets, such as high transaction costs, liquidity traps, and sector-driven volatility.

Praxis is built for the discerning quantitative analyst who understands that in trading, the most profitable decision is often not to trade. It leverages a minimal, cloud-hosted LLM via OpenRouter (specifically, `moonshotai/kimi-k2`) not as a predictive oracle, but as a final statistical auditor. This ensures computational resources are only spent on signals that have already passed a rigorous gauntlet of traditional quantitative checks. This MVP aims to build, backtest, and deploy a robust engine capable of generating a small, highly-vetted list of weekly opportunities.

## Goals and Context

-   **Project Objectives:**
    -   To develop a systematic, automated engine that identifies statistically significant mean-reversion signals in Nifty 500 stocks.
    -   To prioritize capital preservation and long-term survival by integrating non-negotiable filters for liquidity, market regime, and transaction costs.
    -   To create a system where the primary edge is derived from *filtering out* over 95% of apparent trading signals, acting only when multiple statistical guards align.
    -   To validate the system's efficacy through a rigorous, cost-inclusive, walk-forward backtesting framework that accounts for Indian market specifics (STT, brokerage, slippage).

-   **Measurable Outcomes:**
    -   The final backtest report (2010-2023) must demonstrate a positive net annualized return after all simulated costs.
    -   The system must successfully filter and reduce the number of potential trades to fewer than 20 high-confidence signals per month across the Nifty 500 universe.

-   **Success Criteria:**
    -   **Profit Factor (Net):** The backtested profit factor (Gross Profits / Gross Losses) must be greater than 1.5 after factoring in all costs.
    -   **Win Rate (Net):** The percentage of trades achieving a net return greater than the target 1.77% must exceed 25%.
    -   **Maximum Drawdown:** The system's maximum peak-to-trough drawdown must remain below 15% over the entire backtest period.
    -   **Survivability:** The system must remain profitable when tested specifically on volatile periods, such as 2015 (China crisis), 2018 (NBFC crisis), and 2020 (COVID-19 crash).

-   **Key Performance Indicators (KPIs):**
    -   Net Annualized Return (%)
    -   Cost-Adjusted Sharpe Ratio (> 0.8)
    -   Profit Factor
    -   Maximum Drawdown (%)
    -   Average Signals Generated per Year
    -   Average Net Profit per Trade

## Scope and Requirements (MVP / Current Version)

### Functional Requirements (High-Level)

-   **FR1: Indian Market Data Pipeline:** The system must fetch and process daily OHLCV data for NSE stocks using `yfinance` as the primary source. It must also fetch corresponding Nifty sectoral index data to calculate sector volatility. The pipeline must handle data errors, adjust for Indian market holidays, and persist the data for analysis.
-   **FR2: Multi-Frame Signal Generation:** The system must calculate technical indicators (Bollinger Bands, RSI) on three distinct time frames (Daily, Weekly, Monthly) from the daily data. It must generate a preliminary signal only when a specific alignment of these indicators occurs across frames, as defined in the `project_brief.md`.
-   **FR3: Statistical Guardrail Validation:** Every preliminary signal must be subjected to a battery of statistical tests:
    -   **Mean-Reversion Test:** Augmented Dickey-Fuller (ADF) test to confirm the statistical property of mean-reversion in the stock's recent price action.
    -   **Pattern Persistence Test:** Hurst Exponent calculation to ensure the observed mean-reverting behavior is not random noise (H < 0.5).
    -   **Historical Efficacy Test:** Calculation of the historical alignment rate between BB touches and RSI oversold conditions.
-   **FR4: Market Regime & Contextual Filtering:** The system must analyze the broader market context before proceeding:
    -   **Sector Volatility Filter:** Calculate the 20-day annualized volatility of the stock's corresponding Nifty sector index and reject signals if it exceeds a defined threshold (e.g., 22%).
    -   **Liquidity Filter:** Calculate the 5-day average daily turnover (Volume * Close) and reject signals for stocks with less than ₹5 Crore turnover to avoid slippage.
-   **FR5: LLM-Powered Statistical Audit:** For signals that pass all prior filters, the system must query the Kimi 2 model (`moonshotai/kimi-k2`) via the OpenRouter API. The API key must be loaded from a `.env` file. The query will contain only aggregated statistical data from the strategy's historical performance on that stock, not price data. The LLM's role is to provide a final confidence score (0-1) based on this statistical summary.
-   **FR6: Cost-Aware Execution & Sizing Logic:** The system must calculate trade parameters (entry, stop-loss, position size) based on the signal and a strict risk management model (e.g., risk 0.5% of capital per trade). All calculations must bake in estimated costs.
-   **FR7: Rigorous Backtesting Framework:** A walk-forward backtesting engine must be built. This engine must simulate trade execution using the full logic chain (FR1-FR6) and apply a realistic cost model including brokerage (e.g., Zerodha's ₹20/trade model), Securities Transaction Tax (STT), and volume-based slippage.
-   **FR8: Weekly Opportunity Report Generation:** The system must produce a clear, tabular report of all valid, high-confidence trading opportunities for the upcoming week, including all relevant parameters and statistical justifications.

### Non-Functional Requirements (NFRs)

-   **Performance:** A full backtest on a single Nifty 500 stock over a 13-year period must complete in under 15 seconds. The entire Nifty 500 backtest should be parallelizable and complete within 8 hours on a standard quad-core machine.
-   **Reliability/Availability:** The data pipeline must be resilient to intermittent API failures from `nsepy`, implementing retry logic. Error logging must be comprehensive for failed data fetches or calculations.
-   **Security:** The OpenRouter API key must be loaded from a `.env` file and must not be committed to the repository. This is the primary security concern.
-   **Maintainability:** The Python codebase must be modular, with distinct modules for data fetching, indicator calculation, statistical tests, LLM interaction, and backtesting. All key parameters (lookback periods, thresholds, etc.) must be stored in a central configuration file.
-   **Usability/Accessibility:** The primary interface is the weekly generated report. It must be human-readable, clear, and concise, enabling a user to understand the rationale behind each signal at a glance.

### The Philosophy of LLM Usage: The Statistical Auditor

This system's use of an LLM is deliberately constrained and philosophically aligned with using it as a sophisticated meta-learning tool, not a predictive one.

**What the LLM DOES:**
The LLM acts as a non-linear function approximator on the *outputs* of our classical statistical models. It is tasked with answering one question: "Given the historical performance characteristics of this *exact statistical setup* on this *specific stock*, what is the confidence that the current signal is not a statistical anomaly?"

-   **Input:** A structured prompt containing only statistical aggregates.
    -   *Example Input:* `Win rate (>1.77% net): 28.1%, Profit factor: 1.62, Sample size: 21 historical signals, Current sector volatility: 14.5%`
-   **Process:** The LLM leverages its pattern-recognition capabilities to weigh these factors. It might learn, for instance, that a high win rate is less meaningful with a small sample size, or that a good profit factor is unreliable when current sector volatility is much higher than the historical average during past signals.
-   **Output:** A single floating-point number between 0.0 and 1.0.

**What the LLM MUST NEVER DO (The Anti-Patterns):**
1.  **NEVER See Price Data:** The LLM will never be given OHLCV data, charts, or any raw time-series information. This is the single most important rule to prevent it from overfitting to noise and hallucinating price predictions.
2.  **NEVER Read News or Sentiment:** The system is purely quantitative. Feeding the LLM news headlines or social media sentiment would introduce untestable, non-stationary variables.
3.  **NEVER Generate the Signal:** The LLM's role is to *audit*, not to create. It is the final quality check, not the first step.
4.  **NEVER Be Asked Open-Ended Questions:** Prompts must be structured to force a numeric, constrained output. Avoid questions like "Do you think HDFCBANK will go up?" and instead use "Based on these statistics, output a confidence score between 0.0 and 1.0."

### The Science of Market Regime Detection

The system's edge is critically dependent on correctly identifying the prevailing market regime, as mean-reversion strategies fail catastrophically in strong trending markets. Regime is not a single metric but a confluence of factors:

1.  **Primary Filter: Sector Volatility (The Litmus Test):**
    -   **Calculation:** 20-day rolling standard deviation of daily percentage changes of the relevant Nifty sector index (e.g., `^NIFTYFINANCE`), annualized (`* sqrt(252)`).
    -   **Interpretation:**
        -   **< 15% (Mean-Reverting / "Calm"):** Ideal regime. Mean-reversion is expected to work. Signals are considered high-quality.
        -   **15% - 22% (Transitional / "Choppy"):** Caution zone. The market is uncertain. Signals require stronger confirmation from other statistical guards.
        -   **> 22% (Trending / "Storm"):** Avoid. The sector is in a high-volatility, trending mode (either up or down). Mean-reversion bets are statistically poor. **All signals are rejected regardless of other factors.** This filter is the primary defense against events like election results or budget announcements.

2.  **Secondary Confirmation: Hurst Exponent (The Memory Test):**
    -   **Calculation:** Applied to the stock's closing prices over the last 100 days.
    -   **Interpretation:**
        -   **H < 0.45:** Strong evidence of mean-reverting (anti-persistent) behavior. The price has a statistical tendency to return to its mean. This validates the regime for the specific stock.
        -   **0.45 < H < 0.55:** Random walk behavior. No predictable pattern. Low-confidence environment.
        -   **H > 0.55:** Trending (persistent) behavior. The price has a tendency to continue in its current direction. Mean-reversion is contraindicated.

3.  **Tertiary Confirmation: ADF Test (The Stationarity Test):**
    -   **Calculation:** Applied to the stock's daily returns.
    -   **Interpretation:** A p-value < 0.05 suggests the time series of returns is stationary, a key property for mean-reversion to be effective. It confirms that price shocks are temporary.

A signal is only considered to be in a valid "mean-reverting regime" if **Sector Volatility is < 22% AND the stock's Hurst Exponent is < 0.45 AND the ADF test p-value is < 0.05.**

## Epic Overview (MVP / Current Version)

-   **Epic 1: Bedrock - Data Pipeline & Environment:**
    -   Goal: To establish a reliable and automated data foundation for the entire system.
    -   *Stories: Setup Python environment with all dependencies, Implement `nsepy` data fetcher for equities, Implement `yfinance` fetcher for sector indices, Create data cleaning and holiday adjustment module, Implement data storage/caching mechanism.*
-   **Epic 2: The Core - Multi-Frame Signal & Statistical Engine:**
    -   Goal: To codify the signal generation logic and the crucial statistical validation guards.
    -   *Stories: Implement BB and RSI indicator calculations, Develop multi-frame (D/W/M) alignment logic, Implement ADF test function, Implement Hurst Exponent calculator, Implement historical alignment rate function.*
-   **Epic 3: The Grinder - Cost-Aware Backtesting Framework:**
    -   Goal: To build a brutally realistic backtester that can rigorously validate the strategy's historical performance.
    -   *Stories: Design the walk-forward testing loop, Implement the detailed Indian market cost model (brokerage, STT, slippage), Integrate the signal and stats engine into the backtester, Develop performance reporting module (metrics, charts).*
-   **Epic 4: The Auditor - OpenRouter LLM Integration:**
    -   Goal: To integrate the OpenRouter API as the final statistical audit layer.
    -   *Stories: Implement a service to query the OpenRouter API using the specified Kimi 2 model, Ensure the API key is securely loaded from the environment, Develop the prompt engineering function to format statistical data, Create the LLM query and response parsing module, Integrate the LLM confidence score into the main execution logic.*
-   **Epic 5: The Output - Execution Logic & Reporting:**
    -   Goal: To synthesize all components into a final trade execution logic and produce the user-facing weekly report.
    -   *Stories: Implement the final `execute_trade` function combining all filters, Develop the risk management and position sizing calculator, Create the formatted weekly opportunity report generator, Add market-specific enhancements (liquidity/monsoon rules).*

## Key Reference Documents

-   `docs/project-brief.md`
-   `docs/architecture.md`
-   `docs/epic1.md`, `docs/epic2.md`, ...
-   `docs/tech-stack.md`
-   `docs/testing-strategy.md`

## Post-MVP / Future Enhancements

-   **Regime-Adaptive Parameters:** Automatically adjust indicator lookback periods (e.g., shorter BB periods in higher volatility regimes) based on the measured market regime.
-   **Expanded Factor Model:** Incorporate additional statistical factors like volatility skew or correlation with broader market indices as additional filters.
-   **Short-Side Signals:** Develop a parallel logic for identifying overbought, mean-reversion shorting opportunities with its own set of statistical guards.
-   **Dynamic Stop-Loss:** Implement an Average True Range (ATR)-based trailing stop-loss instead of a static mid-band stop to adapt to changing volatility post-entry.

## Change Log

| Change      | Date       | Version | Description      | Author        |
|-------------|------------|---------|------------------|---------------|
| Initial PRD | 2023-10-27 | 1.0     | First Draft      | System Prompt |

## Initial Architect Prompt

### Technical Infrastructure

-   **Starter Project/Template:** None. Build from scratch using standard Python project structure.
-   **Hosting/Cloud Provider:** Not required for MVP. The system is designed to run locally for backtesting and weekly signal generation.
-   **Frontend Platform:** N/A. The output is a Markdown report.
-   **Backend Platform:** Python 3.10+. Key libraries: `pandas`, `numpy`, `statsmodels`, `yfinance`, `openrouter-api`, `python-dotenv`. A pure-python equivalent for technical indicators.
-   **Database Requirements:** N/A for MVP. Data can be cached locally as CSV files for performance.

### Technical Constraints

-   **No External Paid APIs:** The entire system must function using free data sources (`yfinance`) and the free tier of the OpenRouter API. This is a hard constraint.
-   **Python-Only Ecosystem:** All components must be implemented in Python to ensure seamless integration.
-   **Offline Capability:** Once data is fetched, the core signal generation, statistical analysis, and LLM audit must be able to run without an active internet connection.

### Deployment Considerations

-   **Deployment Frequency:** N/A for MVP. This is a research and signal-generation tool, not a continuously running service.
-   **CI/CD Requirements:** A simple CI pipeline using GitHub Actions to run linters (`black`, `flake8`) and unit tests on push would be beneficial.
-   **Environment Requirements:** A `requirements.txt` or `pyproject.toml` file must be maintained for reproducible environments. A `.env.example` file must be provided, and the `.env` file must contain a valid OpenRouter API key.

### Local Development & Testing Requirements

-   **Local Environment:** Must be fully runnable on a standard developer machine (Windows 11).
-   **Testing:** Unit tests are required for all statistical functions (`hurst`, `adf_test`) and indicator calculations. Integration tests should verify the end-to-end flow for a single stock, from data fetching to final trade decision. The backtesting engine itself is the primary system test.
-   **Utility Scripts:** A `run_backtest.py` script should be provided to execute the full backtest on the Nifty 500. A `generate_report.py` script should run the logic on the latest data to produce the weekly opportunities.