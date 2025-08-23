Of course. Here is a comprehensive architecture document for the "Praxis" project, written from the perspective and with the mindset of Kailash Nadh, ensuring every requirement from the provided documents is meticulously addressed.

---

# **Architecture Document: "Praxis" Mean-Reversion Engine**

## 1. Introduction & Philosophy

This document outlines the technical architecture for "Praxis," a quantitative trading system for the Indian markets. It is not a blueprint for a money-printing machine. It is a design for a robust, deterministic filtering engine. The architecture is rooted in two non-negotiable truths about building systems for the real world, especially the chaotic Indian market.

1.  **Pragmatic Simplicity (The Nadh Principle):** Complexity is the primary vector for failure. This system will be built from simple, discrete, and brutally testable components. We are not building a general-purpose AI; we are building a specialized machine that applies a sequence of deterministic statistical checks. The LLM is a pluggable component—a calculator for a specific, non-linear function—not the brain. Over-engineering is a luxury we cannot afford.

2.  **The Edge is in the Filter (The Real-World Principle):** The core purpose of this system is not to find trades, but to find reasons *not* to trade. Profitability in quantitative trading, particularly mean-reversion, comes from surviving periods where the strategy does not work. Therefore, the architecture must be obsessed with the integrity of its filters: market regime, liquidity, statistical validity, and costs. Every component is designed to be a "guardrail" that protects capital.

The result is a system designed to be run locally, that is secure by design, resilient to failure, and focused entirely on identifying a small number of high-probability opportunities that have survived a gauntlet of rigorous, reality-based checks.

## 2. Architectural Principles

*   **Modularity & Single Responsibility:** Each component does one thing and does it well. The `DataService` knows nothing of statistics; the `ValidationService` knows nothing of backtesting. This separation is paramount for testing, maintenance, and future replacement of any single part without collapsing the whole structure.
*   **Determinism & Reproducibility:** A backtest is a scientific experiment. For a given set of stocks, configuration, and data vintage, a run must be 100% reproducible. This is achieved through versioned data caching and deterministic logic. There is no room for randomness.
*   **Stateless Orchestration:** The main application logic is a stateless orchestrator. All state (the results of a backtest, for instance) is explicitly managed and persisted. The system can be stopped and restarted without data loss, but it does not maintain a persistent "state" during a run.
*   **Constrained Interfaces:** All external inputs, especially from the LLM, are treated as data, never as code. The LLM's role is strictly defined by a "contract": it receives a structured set of statistics and returns a single floating-point number. This eliminates an entire class of security and reliability problems from the outset.
*   **Realism First (The Cost Principle):** The system is architecturally aware of real-world trading frictions. Costs (brokerage, STT, slippage) are not an afterthought to be applied to a report; they are fundamental parameters integrated into the core logic of the `ExecutionSimulator` and backtesting loop. Gross returns are a vanity metric and will not be tracked.

## 3. System Overview (C4 Model - Level 2)

The system is a sequential filtering pipeline orchestrated by a central `Orchestrator`. It is designed to run in two modes: `backtest` and `generate-report`. The diagram below illustrates the `backtest` flow for a single time step.

```mermaid
graph TD
    subgraph PraxisEngine [Praxis Engine (Local Python Application)]
        direction LR
        Orchestrator(Orchestrator)
        ConfigService(Config Service)
        DataService(Data Service)
        SignalEngine(Signal Engine)
        ValidationService(Validation Service)
        LLMAuditService(LLM Audit Service)
        ExecutionSimulator(Execution Simulator)
        ReportGenerator(Report Generator)

        Orchestrator -- "Reads Config" --> ConfigService
        Orchestrator -- "1. Get Historical Data Window" --> DataService
        Orchestrator -- "2. Generate Preliminary Signal" --> SignalEngine
        Orchestrator -- "3. Validate Signal with Guards" --> ValidationService
        Orchestrator -- "4. Perform LLM Audit" --> LLMAuditService
        Orchestrator -- "5. Simulate Trade & Costs" --> ExecutionSimulator
        Orchestrator -- "6. Aggregate & Report Results" --> ReportGenerator
    end

    User[Quant Analyst (CLI User)] -- "python main.py backtest" --> Orchestrator
    ConfigService -- "Reads config.ini" --> LocalFS[(Local Filesystem)]
    DataService -- "Fetches OHLCV Data" --> yfinance[yfinance API]
    LLMAuditService -- "Sends Stats, Gets Score" --> LocalLLM[Local LLM Server<br/>(Ollama / Llama 3)]
    DataService -- "Caches data.parquet" --> LocalFS
    ReportGenerator -- "Writes backtest_summary.md" --> LocalFS
```

## 4. Component Breakdown

This table maps the PRD's functional requirements directly to architectural components.

| Component | Responsibility | Inputs | Outputs | PRD Mapping | Implementation Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Orchestrator** | The brain. Manages the primary application modes (`backtest`, `generate-report`). In `backtest` mode, it runs the walk-forward loop over the entire dataset for each stock. | CLI arguments (`mode`, `config_path`). | Final report files to the filesystem. | FR7, FR8 | The walk-forward logic is its core responsibility. It slices the main DataFrame into expanding windows and passes them to the pipeline for each time step. |
| **Config Service** | Parses and validates `config.ini`, providing a typed configuration object (Pydantic model) to the system. | `config.ini` file path. | A `Config` data object. | NFR (Maintainability) | All thresholds (volatility, liquidity, Hurst, etc.) and parameters (lookback periods) are defined here. |
 | **Data Service** | Fetches, cleans, caches, and prepares market data. Handles Indian market specifics. | Stock symbol, sector map, date range. | A `pandas` DataFrame with OHLCV, volume, and `sector_vol` columns. | **FR1** | Uses `yfinance` for equities and sector indices. Caches data in Parquet format keyed by stock and date range. Includes logic to handle Indian market holidays. |
| **Signal Engine** | Generates preliminary mean-reversion signals based on multi-frame indicator alignment. | A `pandas` DataFrame window. | A `Signal` object (or `None`) containing entry/stop-loss targets. | **FR2** | Resamples the daily data to create weekly and monthly views. Calculates BBands and RSI on all three frames and applies the alignment logic from `project_brief.md`. |
| **Validation Service** | The core of the filtering philosophy. Applies a cascade of statistical and contextual "guardrails" to a preliminary signal. | A `Signal` object, a `pandas` DataFrame window. | A `ValidationResult` object with boolean flags for each passed guard. | **FR3, FR4** | This is a container for smaller, single-purpose "Guard" modules: `StatGuard` (ADF, Hurst), `RegimeGuard` (Sector Volatility), `LiquidityGuard` (Turnover), `HistoryGuard` (Historical Efficacy). |
| **LLM Audit Service** | Performs the final statistical audit by querying a local LLM. Adheres to the strict "no price data" rule. | A `pandas` DataFrame window, a `Signal` object, `ValidationResult`. | A confidence score (float between 0.0 and 1.0). | **FR5** | Constructs the prompt using only statistical aggregates (win rate, profit factor, sample size, current volatility) derived from the historical data window. Uses the `ollama` library to interact with a local Llama 3 instance. |
| **Execution Simulator** | Calculates position size and simulates the trade, applying a realistic cost model. | A `Signal` object, confidence score, current price. | A `Trade` object with net return, costs incurred, etc. | **FR6** | Contains the detailed cost model (brokerage, STT, volume-based slippage). Implements the risk management logic (e.g., risk 0.5% of capital per trade). |
| **Report Generator** | Aggregates results from the backtest or generates the weekly opportunity report. | A list of `Trade` objects (for backtest) or a list of valid opportunities. | A formatted Markdown file (`.md`). | **FR8** | For backtesting, calculates all KPIs from the PRD (Net Return, Sharpe, Profit Factor, Max Drawdown). For weekly reports, creates the specified table. |

## 5. Data Flow & The Filtering Cascade

This flow describes the `backtest` mode, which is the most comprehensive execution path. The `generate-report` mode is identical but runs only once on the most recent data window.

1.  **Initialization:** The `Orchestrator` is invoked. It loads the configuration via `ConfigService`, which includes the list of Nifty 500 stocks and all system parameters.

2.  **Outer Loop (Per-Stock):** The `Orchestrator` iterates through each stock symbol.
    a. **Data Fetching:** It calls `DataService.get_full_data(stock)`. The service fetches data from `yfinance` if not present in the local Parquet cache, then returns the complete historical DataFrame.

3.  **Inner Loop (Walk-Forward):** The `Orchestrator` iterates through the time series for the stock, from a minimum history size (e.g., 200 days) to the end. For each day `i`:
    a. **Create Data Window:** A DataFrame `window = df.iloc[0:i]` is created. This represents all information known up to that day.
    b. **Phase 1: Signal Generation:** The `window` is passed to the `SignalEngine`.
        *   *If no multi-frame alignment is found*, it returns `None`. The loop continues to day `i+1`.
        *   *If alignment is found*, it returns a `Signal` object.
    c. **Phase 2: Guardrail Validation:** The `Signal` and `window` are passed to the `ValidationService`. It executes its guards sequentially:
        *   `LiquidityGuard`: Checks if 5-day avg turnover > ₹5 Crore. **If fails, reject signal.**
        *   `RegimeGuard`: Checks if sector volatility < 22%. **If fails, reject signal.**
        *   `StatGuard`: Checks if ADF p-value < 0.05 AND Hurst < 0.45. **If fails, reject signal.**
        *   *If any guard fails*, the reason is logged, and the loop continues to day `i+1`.
    d. **Phase 3: LLM Audit:** If all guards pass, the `window` and `Signal` are passed to the `LLMAuditService`.
        *   It calculates the historical performance statistics of the *exact same setup* within the `window`.
        *   It constructs the prompt and queries the local LLM.
        *   It receives a confidence score. If the score is below the configured threshold (e.g., 0.7), the signal is rejected, and the loop continues to `i+1`.
    e. **Phase 4: Execution Simulation:** If the LLM confidence is sufficient, the `Signal` is passed to the `ExecutionSimulator`.
        *   It calculates the position size based on the risk model.
        *   It simulates the trade entry at `df['Open'].iloc[i]`.
        *   It determines the exit (e.g., 20 days later or hitting the stop-loss).
        *   It calculates the **net return** after applying the full cost model (brokerage, STT, slippage).
        *   A `Trade` object containing all this information is created and appended to a results list.

4.  **Final Aggregation:** After the inner and outer loops complete, the full list of all simulated `Trade` objects is passed to the `ReportGenerator`. It calculates the final system-wide KPIs and writes the `backtest_summary.md` file.

## 6. The LLM Contract: The Statistical Auditor

The interface with the LLM is rigidly defined to prevent misuse. The LLM is a stateless function that maps a set of statistical features to a confidence score.

**Input to LLM (via structured prompt):** A JSON-like block of text containing only statistical aggregates calculated from the historical data window.

```
- Historical Win Rate (>1.77% net return in 20 days): 28.1%
- Historical Profit Factor: 1.62
- Historical Sample Size (number of past signals): 21
- Current Sector Volatility (annualized): 14.5%
- Current Hurst Exponent: 0.41
```

**Output from LLM:** A single floating-point number, stripped of any text, between 0.0 and 1.0.

The `LLMAuditService` is responsible for parsing this response. If the output is not a valid float, it is treated as a score of 0.0, and the failure is logged. This ensures system stability even with a misbehaving model.

## 7. The Cost & Slippage Model

This is not an afterthought; it is a core component (`ExecutionSimulator`) and must be implemented precisely as specified in the PRD.

*   **Brokerage:** A function that calculates `max(0.0003 * trade_value, 20)` for both entry and exit.
*   **Securities Transaction Tax (STT):** A fixed percentage (e.g., 0.025%) applied to the trade value.
*   **Slippage:** A function that takes the stock's recent average volume as input and returns a slippage percentage. This will be modeled as a tiered function:
    *   `if avg_volume > 1,000,000: return 0.001` (0.1%)
    *   `else: return 0.005` (0.5%)
    This slippage is added to the entry price and subtracted from the exit price.

## 8. Error Handling & Resilience

-   **API Failures (`nsepy`/`yfinance`):** The `DataService` will implement a retry mechanism with exponential backoff for transient network errors. If data for a stock cannot be fetched after 3 retries, it will be logged as a failure for that stock and the orchestrator will move to the next one.
-   **Statistical Calculation Errors:** Any exceptions within the `ValidationService` (e.g., from `statsmodels`) will be caught, logged, and treated as a failed validation. The signal will be rejected.
-   **LLM Failures:** If the local Ollama server is down or the `LLMAuditService` fails to get a valid float response after 2 retries, it will return a confidence score of 0.0, effectively rejecting the signal and allowing the system to continue running.
-   **Configuration Errors:** On startup, the `ConfigService` will validate the `config.ini` file using Pydantic. If critical values are missing or malformed, the application will exit with a clear error message.

## 9. Directory Structure

This structure promotes clean separation of concerns and maps directly to the components described above.

```
praxis_engine/
├── main.py                 # CLI entry point (using Typer/Click)
├── config.ini              # Central configuration file
├── core/
│   ├── __init__.py
│   ├── orchestrator.py     # Main backtest/report generation loops
│   ├── models.py           # Pydantic models for Config, Signal, Trade, etc.
│   └── guards/             # Sub-package for validation logic
│       ├── __init__.py
│       ├── base_guard.py   # Abstract base class for guards
│       ├── stat_guard.py   # ADF, Hurst logic
│       ├── regime_guard.py # Sector volatility logic
│       └── liquidity_guard.py # Turnover logic
├── services/
│   ├── __init__.py
│   ├── config_service.py   # Loads and parses config.ini
│   ├── data_service.py     # Fetches, caches, and prepares data
│   ├── signal_engine.py    # Multi-frame signal generation
│   ├── validation_service.py # Orchestrates all guards
│   ├── llm_audit_service.py# Interacts with local LLM
│   ├── execution_simulator.py # Cost model and trade simulation
│   └── report_generator.py # Creates final Markdown reports
├── prompts/
│   └── statistical_auditor.txt # Jinja2 template for the LLM prompt
├── data_cache/             # Local CSV cache (ignored by git)
│   └── HDFCBANK_2010-01-01_2023-12-31.CSV
├── results/                # Output directory for all reports (ignored by git)
│   └── backtest_summary_2024-05-21.md
├── .env                    # Not strictly needed for MVP, but good practice
├── requirements.txt
└── pyproject.toml
```