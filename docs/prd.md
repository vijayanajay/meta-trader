# Self-Improving Quant Engine PRD (v2.0)

## 1. Intro

This document outlines the requirements for the "Self-Improving Quant Engine." The project's purpose is to create a robust, automated system for discovering and refining stock trading strategies.

The core architectural principle of this MVP is **simplicity and constraint**. We are not building a system where a Large Language Model (LLM) generates arbitrary code. Instead, we are building a deterministic backtesting engine with a well-defined, constrained "action space" (a curated set of technical indicators and logical conditions). The LLM's role is not to code, but to act as an intelligent **parameter selector**, proposing new configurations within this safe and structured framework.

The system's feedback loop is the engine of discovery:
1.  Backtest a strategy configuration on a **training** dataset.
2.  Generate a dense, information-rich performance report.
3.  Feed the history of these reports to an LLM.
4.  The LLM proposes a new strategy **configuration (as JSON)**.
5.  Repeat.

This approach focuses the LLM's reasoning capabilities on the core problem of strategy discovery, eliminating security risks and the complexities of code generation and parsing.

## 2. Goals and Context

-   **Project Objectives:**
    -   To build a simple, reliable, and fully automated framework for iteratively optimizing a quantitative trading strategy's parameters.
    -   To validate that an LLM can, given structured feedback, learn to navigate a parameter space to improve strategy performance.
    -   To create a foundational tool that directly addresses and measures strategy overfitting from the outset.

-   **Measurable Outcomes:**
    -   The system can successfully complete a 10-iteration run for a list of 3+ tickers specified in a config file without manual intervention.
    -   The final strategy discovered for at least one ticker must demonstrate a higher Sharpe Ratio on the **training data** than the initial baseline.
    -   The final strategy must also demonstrate a positive Sharpe Ratio on the unseen **validation data**, proving it has generalized beyond the training set.

-   **Success Criteria:**
    -   The end-to-end loop is fully automated and driven by a single command.
    -   The LLM consistently returns valid JSON that conforms to the predefined strategy schema.
    -   **Zero use of `eval()`** or other unsafe methods for executing LLM output. The system is secure by design.
    -   The final output provides a clear, auditable trail of the entire optimization process for each ticker.

-   **Key Performance Indicators (KPIs):**
    -   **Primary:** Sharpe Ratio (on both training and validation data).
    -   **Secondary:** Sortino Ratio, Max Drawdown [%], Calmar Ratio.
    -   **Generalization KPI:** `Performance Drop-off %` = `(Train Sharpe - Validation Sharpe) / abs(Train Sharpe)`. A low value indicates good generalization.
    -   **Efficiency KPI:** Number of iterations required to surpass the baseline performance.

## 3. Scope and Requirements (MVP)

### Functional Requirements (FRs)

-   **FR1: Configuration-Driven Setup:** The system must be executed via a single entry point (e.g., `python main.py`). All parameters—tickers, iteration count, API keys, data ranges—must be loaded from a single `config.ini` file.

-   **FR2: Data Ingestion & Splitting:** For each ticker, the system will fetch 10 years of historical daily price data. This data will be deterministically split into two segments:
    -   **Training Set:** The first 8 years of data. The iterative optimization loop runs exclusively on this set.
    -   **Validation Set:** The final 2 years of data. This set is held out and used only once at the end to test the final, best-performing strategy for overfitting.

-   **FR3: Constrained Strategy Engine:** The system will use a predefined strategy template. The LLM's task is to provide the parameters for this template.
    -   The engine will use the `pandas-ta` library to generate a curated list of technical indicators (e.g., `RSI`, `SMA`, `EMA`, `MACD`, `BBANDS`).
    -   The strategy logic (buy/sell conditions) will be constructed programmatically based on a JSON object received from the LLM. This JSON will specify indicators, their parameters (e.g., `length: 14`), and the logical conditions (`cross_above`, `greater_than`, etc.).

-   **FR4: Backtesting & Reporting:**
    -   For each iteration, the system backtests the configured strategy on the **Training Set**.
    -   It must generate a structured report containing:
        1.  The exact JSON configuration of the strategy used.
        2.  Standard performance metrics (Sharpe, Sortino, Max Drawdown, etc.) from the training run.
        3.  An **Information-Dense Statistical Trade Summary** (as per Point 4, Option 2):
            -   `total_trades`: Integer
            -   `win_rate_pct`: Float
            -   `profit_factor`: Float
            -   `avg_win_pct`: Float
            -   `avg_loss_pct`: Float
            -   `max_consecutive_losses`: Integer
            -   `avg_trade_duration_bars`: Integer

-   **FR5: LLM Prompting & Interaction:** The system will manage a cumulative history of the reports from FR4. For each new iteration, it will send this history to the LLM with a prompt instructing it to:
    -   Act as a quantitative analyst.
    -   Analyze the performance history, noting which configurations worked and which failed.
    -   Propose a new strategy configuration by returning **only a valid JSON object** that conforms to the system's predefined schema.

-   **FR6: Iteration Loop with Pruning (Optimization):**
    -   The system orchestrates the process from backtest (FR4) to LLM suggestion (FR5) in an automated loop for the configured number of iterations.
    -   **Pruning Mechanism:** If a suggested strategy results in a Sharpe Ratio below a predefined threshold (e.g., 0.1) on the training data, the system will discard this result. The next prompt to the LLM will revert to the *previous best-performing strategy* and explicitly state that the last attempt was a failure, encouraging a different path.

-   **FR7: Final Validation & Output Generation:**
    -   After the loop completes, the system identifies the single best strategy based on its performance on the **Training Set**.
    -   It then runs this single best strategy on the unseen **Validation Set**.
    -   It generates a final, comprehensive report detailing the entire process.

-   **FR8: Intelligent Baseline (Optimization):** The starting point for Iteration 0 will not be random. It will be a hard-coded, simple, well-known strategy (e.g., SMA(50) / SMA(200) crossover) to provide the LLM with a sensible performance benchmark to improve upon.

### Non-Functional Requirements (NFRs)

-   **Security:**
    -   API keys must be loaded from the config file or environment variables, never hard-coded.
    -   **The use of `eval()`, `exec()`, or any other method of executing strings from the LLM is strictly forbidden.** The system's architecture (parsing JSON into fixed function calls) inherently prevents arbitrary code execution.
-   **Performance:** A single backtest iteration (excluding the LLM API call) must complete in under 30 seconds.
-   **Reliability:** The system must include robust error handling for API failures (data source, LLM) and for malformed JSON responses from the LLM. It should retry a configurable number of times before halting gracefully.
-   **Maintainability:** The codebase must be modular: `data_handler.py`, `strategy_engine.py`, `backtester.py`, `llm_interface.py`, `main.py`. The strategy definition (JSON) is fully decoupled from the execution logic.
-   **Usability:** The system is a CLI tool. It must provide clear, real-time console output indicating its current state (e.g., "RELIANCE.NS: Running Iteration 3/10...", "Awaiting LLM response...").

### Detailed Final Report Structure (FR7)

Upon completion of a run for a single ticker, the system must generate a timestamped output directory (e.g., `results/RELIANCE.NS_2023-10-27_15-30-00/`). This directory will be a complete, self-contained record of the discovery process and must contain:

1.  **`summary_report.md`**: A human-readable Markdown file with the final results.
    -   **Header:** Ticker, Run Duration, Total Iterations.
    -   **Best Strategy Found:**
        -   The final JSON configuration of the winning strategy.
    -   **Performance Comparison Table:**
        | Metric             | Baseline (Iter 0) | Best on Training Set | Best on Validation Set |
        |--------------------|-------------------|----------------------|------------------------|
        | Sharpe Ratio       | 0.45              | 1.52                 | 1.15                   |
        | Sortino Ratio      | 0.60              | 2.10                 | 1.75                   |
        | Max Drawdown [%]   | -25.2%            | -12.5%               | -15.8%                 |
        | Final Return [%]   | 35%               | 120%                 | 45%                    |
        | **Generalization** | ---               | ---                  | **Drop-off: 24.3%**    |
    -   **Run Log:** A brief summary of each iteration (e.g., "Iter 3: Sharpe 0.95, Iter 4: Pruned (Sharpe -0.2)").

2.  **`full_run_log.json`**: A machine-readable file containing the complete report object (strategy JSON, metrics, trade summary) for every single iteration.

3.  **`charts/` directory**:
    -   `best_strategy_training_plot.html`: The interactive plot generated by `backtesting.py` for the best strategy on the training data.
    -   `best_strategy_validation_plot.html`: The interactive plot for the best strategy on the validation data.

4.  **`iterations/` directory**:
    -   A subdirectory for each iteration (`iter_0/`, `iter_1/`, ...).
    -   Each subdirectory contains the `backtesting.py` plot (`report.html`) and the trade log (`trades.csv`) for that specific iteration's run on the training data. This allows for detailed forensic analysis of any specific step in the process.

## 4. Epic Overview (MVP)

-   **Epic 1: The Deterministic Backtesting Engine:**
    -   Goal: Build a self-contained system that can be run programmatically. It takes a ticker and a strategy JSON as input and produces the full set of artifacts (training report, validation report, plots).
    -   Key Tasks: `config.ini` parsing, data fetching and splitting, `pandas-ta` integration, `backtesting.py` wrapper, statistical summary generation. This epic is complete when we can manually test strategies without any LLM.

-   **Epic 2: The LLM Optimization Loop:**
    -   Goal: To wrap the deterministic engine from Epic 1 in an intelligent optimization loop.
    -   Key Tasks: Implement the main loop logic, manage the history of reports, engineer the system prompt for the LLM, handle JSON parsing and validation, and implement the pruning logic.

-   **Epic 3: CLI & Operational Polish:**
    -   Goal: To create the final user-facing tool.
    -   Key Tasks: Build the main CLI entry point, add clear logging and console output, structure the final output directory, and write comprehensive documentation (`README.md`).

## 5. Post-MVP / Future Enhancements

-   **Expanded Action Space:** Gradually add more indicators, logical conditions, and even risk management parameters (e.g., stop-loss percentages) to the JSON schema for the LLM to control.
-   **Walk-Forward Analysis:** Upgrade the Train/Validation split to a more robust rolling walk-forward validation method for continuous adaptation.
-   **Multi-Ticker Strategy Generalization:** Modify the objective to find a single strategy configuration that performs well across a *portfolio* of tickers.
-   **LLM Self-Critique:** Add a step where the LLM is asked to critique its own JSON suggestion before it's run, potentially catching logical flaws early.

## 6. Initial Architect Prompt

-   **Backend Platform:** Python 3.9+. Key libraries: `pandas`, `yfinance`, `pandas-ta`, `backtesting.py`, `openrouter`, `configparser`. The designated LLM provider is **OpenRouter**, with the API key configured in the `.env` file. The recommended model for this project is **`moonshotai/kimi-k2:free`**. (Updated as per implementation)
-   **Technical Constraints:**
    -   The strategy "action space" must be defined in a schema. The LLM's output must be validated against this schema.
    -   The system must be stateless between runs. All necessary information is read from the config file at startup.
-   **Local Development:**
    -   A `requirements.txt` file is mandatory.
    -   The entry point will be `python main.py`. No arguments are needed as all configuration is in `config.ini`.
    -   Unit tests using `pytest` are required for core, non-stochastic components like the statistical summary generator and the strategy engine's JSON parser.