# Architecture Document: Self-Improving Quant Engine

## 1. Introduction

This document outlines the technical architecture for the "Self-Improving Quant Engine," designed in accordance with the v2.0 PRD. The architecture's philosophy is rooted in two core principles:

1.  **Pragmatic Simplicity (The Nadh Principle):** The system must be simple, robust, and composed of discrete, testable components. We avoid over-engineering by building a straightforward, deterministic machine that uses the LLM as a specialized, pluggable component, not as a general-purpose coder. Complexity is the enemy of reliability.

2.  **Integrity of the Learning Signal (The Hinton Principle):** The system's primary purpose is to facilitate learning. Therefore, the architecture must obsessively protect the integrity of the feedback loop. This means providing the LLM with dense, high-quality information, preventing data leakage (via a strict train/validation split), and ensuring the learning problem is well-defined and constrained.

The result is a CLI tool that is secure by design, resilient to failure, and focused on discovering strategies that generalize to unseen data.

## 2. Architectural Principles

*   **Modularity:** Each component has a single, well-defined responsibility. The `DataService` knows nothing about the LLM; the `StrategyEngine` knows nothing about backtesting. This separation allows for independent development, testing, and future replacement.
*   **Security by Design:** The system is architecturally incapable of arbitrary code execution. The LLM's output is treated as a configuration data structure (JSON), not as executable code. This eliminates an entire class of security vulnerabilities from the outset.
*   **Determinism & Reproducibility:** For a given ticker, configuration, and model version, a run should be fully reproducible. This is achieved through deterministic data splitting and versioned data caching.
*   **Stateless Orchestration with Resumability:** The main application logic is stateless. All state is explicitly managed by the `StateManager`, which persists the run's history to the filesystem after every successful iteration. This makes the system resilient to crashes and interruptions.
*   **Generalization First:** The entire data flow is built around the train/validation split. The system's ultimate measure of success is not performance on data it has seen, but performance on data it has not. This is the only way to combat overfitting.

## 3. System Overview (C4 Model - Level 2)

The system is a sequential pipeline orchestrated by a central `Orchestrator`. It is designed as a collection of services that are called in a well-defined order.

```mermaid
graph TD
    subgraph SelfImprovingQuantEngine [Self-Improving Quant Engine (Python CLI Application)]
        direction LR
        Orchestrator(Orchestrator)
        ConfigService(Config Service)
        StateManager(State Manager)
        DataService(Data Service)
        StrategyEngine(Strategy Engine)
        Backtester(Backtester)
        ReportGenerator(Report Generator)
        LLMService(LLM Service)

        Orchestrator -- "Reads Config" --> ConfigService
        Orchestrator -- "Load/Save State" --> StateManager
        Orchestrator -- "1. Get Data" --> DataService
        Orchestrator -- "2. Build Strategy" --> StrategyEngine
        Orchestrator -- "3. Run Backtest" --> Backtester
        Orchestrator -- "4. Generate Report" --> ReportGenerator
        Orchestrator -- "5. Get Suggestion" --> LLMService
    end

    User[CLI User] -- "python main.py" --> Orchestrator
    ConfigService -- "Reads config.ini" --> LocalFS[(Local Filesystem)]
    DataService -- "Fetches OHLCV Data" --> ExternalDataProvider[External Data Provider API<br/>(e.g., yfinance)]
    LLMService -- "Sends Reports, Gets JSON" --> ExternalLLM[External LLM API<br/>(e.g., OpenRouter)]
    StateManager -- "Reads/Writes run_state.json" --> LocalFS
    DataService -- "Caches data.parquet" --> LocalFS
    Orchestrator -- "Outputs Final Report" --> LocalFS
```

## 4. Component Breakdown

| Component | Responsibility | Inputs | Outputs | Implementation Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Orchestrator** | The brain of the system. Manages the main iteration loop for each ticker, coordinates all services, and handles the final validation run. | None (initiates the process). | Final report files to the filesystem. | Implements the pruning logic: if a strategy is poor, it reverts to the previous best state before calling the LLM. |
| **Config Service** | Parses and validates the `config.ini` file, providing a clean, typed configuration object to the rest of the system. | `config.ini` file path. | A configuration data object. | Uses Python's `configparser`. Provides default values for non-critical settings. |
| **State Manager** | Handles persistence for resumability. Reads and writes the entire run history to disk after each successful iteration. | The current list of all past reports. | A `run_state.json` file. | Writes to a temporary file and then renames it to ensure atomic writes, preventing state corruption if the process is killed mid-write. |
| **Data Service** | Fetches, caches, and splits the historical market data. | Ticker, date range from config. | Two `pandas` DataFrames: `train_data`, `validation_data`. | Caches data locally in Parquet format, which is efficient and preserves data types. The train/validation split is deterministic. |
| **Strategy Engine** | The core of the "Security by Design" principle. Translates the LLM's JSON configuration into a backtest-ready DataFrame. | A `pandas` DataFrame, a strategy JSON object. | The same DataFrame with new columns for each indicator and the final buy/sell signals. | It iterates through the `indicators` in the JSON, calling the corresponding `pandas-ta` function. It then uses a sandboxed evaluator like `asteval` to safely evaluate the `buy_condition` and `sell_condition` strings against the DataFrame columns. |
| **Backtester** | A thin wrapper around the `backtesting.py` library. Executes the backtest and returns the results. | A `pandas` DataFrame with signal columns. | A results object from `backtesting.py`. | Encapsulates all library-specific logic, making it easy to swap out the backtesting engine in the future if needed. |
| **Report Generator** | Creates the dense, structured report that serves as the learning signal for the LLM. | `backtesting.py` results object, strategy JSON. | A structured report object (e.g., a Pydantic model or dict). | Calculates all primary/secondary KPIs and the crucial "Statistical Trade Summary" as defined in the PRD. |
| **LLM Service** | Manages all communication with the LLM API. Constructs the prompt, sends the request, and validates the response. | The cumulative history of reports. | A validated strategy JSON object. | Uses a provider like OpenRouter (with a model like `moonshotai/kimi-k2:free`) or OpenAI. Uses a prompt template. For long histories, it will employ a simple summarization: full details for the last 5 iterations, and only the metrics and strategy JSON for older ones. It also handles API retries with exponential backoff. |

## 5. Data Flow & The Learning Loop

This flow is executed sequentially for each ticker listed in the `config.ini`.

1.  **Initialization:** The `Orchestrator` starts. It uses the `ConfigService` to load the run parameters. It creates a unique, timestamped output directory for the current run.

2.  **State Check:** The `Orchestrator` asks the `StateManager` to look for a `run_state.json` for the current ticker.
    *   **If found:** The history of reports is loaded. The loop will resume from the next iteration number. This is a critical resilience feature.
    *   **If not found:** An empty history is created, and the run starts from Iteration 0 using the hard-coded baseline strategy.

3.  **Data Preparation:** The `DataService` is called.
    *   It checks for a local Parquet cache of the data. If it's missing or stale, it fetches the data from the external API and saves it.
    *   It splits the full DataFrame into the **Training Set** (first 80%) and the **Validation Set** (last 20%). The Validation Set is now held aside and will not be touched again until the very end.

4.  **The Iterative Optimization Loop (on Training Data):** The `Orchestrator` runs a loop from the current iteration number to the configured maximum.
    a. **Strategy Creation:** The `StrategyEngine` takes the current strategy JSON and the **Training Set** and adds the necessary indicator and signal columns.
    b. **Backtest:** The `Backtester` runs the strategy on the modified DataFrame.
    c. **Report Generation:** The `ReportGenerator` takes the backtest results and creates the detailed report object, including the statistical trade summary.
    d. **State Persistence:** The new report is appended to the history list, and the `StateManager` saves the entire list to `run_state.json`. This ensures that even if the LLM call fails, the progress from this iteration is saved.
    e. **LLM Suggestion:** The `LLMService` is given the full history. It constructs the prompt, sends it to the LLM API, and receives a new strategy JSON. It validates that the response is well-formed JSON and conforms to the required schema.
    f. **Loop:** The new JSON becomes the input for the next iteration.

5.  **Final Validation & Judgment (on Validation Data):** After the loop completes:
    a. The `Orchestrator` analyzes the full history of reports and identifies the single best-performing strategy based on its Sharpe Ratio on the **Training Set**.
    b. It takes the JSON for this winning strategy and runs it through the `StrategyEngine` and `Backtester` **one final time**, but using the unseen **Validation Set**.
    c. The performance on this validation run is the "true" measure of the strategy's quality. It represents a more honest, out-of-sample performance estimate.
    d. The `Orchestrator` generates the final `summary_report.md` and all associated artifacts (plots, logs) in the output directory, clearly comparing the Training vs. Validation performance.

## 6. The LLM Contract & Action Space

The system's reliability hinges on a strict, well-defined contract with the LLM. The LLM is not asked to be creative with structure; it is asked to fill in a template.

**Required LLM JSON Output Schema:**

```json
{
  "strategy_name": "A descriptive name, e.g., EMA_crossover_with_RSI_filter",
  "indicators": [
    { "name": "ema_fast", "function": "ema", "params": { "length": 20 } },
    { "name": "ema_slow", "function": "ema", "params": { "length": 50 } },
    { "name": "rsi", "function": "rsi", "params": { "length": 14 } }
  ],
  "buy_condition": "ema_fast > ema_slow AND rsi > 50",
  "sell_condition": "ema_fast < ema_slow"
}
```

-   `strategy_name`: A human-readable identifier.
-   `indicators`: A list of indicators to be calculated by `pandas-ta`. The `name` is the variable name that can be used in the conditions. `function` must be a function supported by the `StrategyEngine`.
-   `buy_condition` / `sell_condition`: A string expression that will be safely evaluated. The only variables available in its scope will be the names of the indicators defined above and the standard OHLCV columns (`open`, `high`, `low`, `close`, `volume`).

## 7. Error Handling & Resilience

-   **API Failures:** `DataService` and `LLMService` will use exponential backoff for retries on transient network or server errors (e.g., 502, 503).
-   **Invalid LLM Response:** If the LLM returns malformed JSON or a response that doesn't adhere to the schema after 3 retries, the iteration is marked as a failure, the error is logged, and the entire run for that ticker is halted to prevent wasted calls.
-   **State Corruption:** On startup, if `run_state.json` is unparseable, the `StateManager` will log a critical error and the application will exit, instructing the user to either fix the file or delete it to start a fresh run.
-   **Backtest Failure:** Any exception during the backtest (e.g., from a logically impossible strategy) is caught, logged as a failed iteration, and the loop continues to the next LLM suggestion.

## 8. Directory Structure

This structure maps directly to the modular components described above, promoting clean separation of concerns.

```
self_improving_quant/
├── main.py                 # CLI entry point, instantiates and runs Orchestrator
├── config.ini              # Central configuration file
├── core/
│   ├── __init__.py
│   ├── orchestrator.py     # Main control loop logic
│   └── models.py           # Pydantic models for Config, Report, Strategy JSON
├── services/
│   ├── __init__.py
│   ├── config_service.py   # Loads and parses config.ini
│   ├── data_service.py     # Fetches, caches, and splits data
│   ├── strategy_engine.py  # Translates JSON to signals
│   ├── backtester.py       # Wrapper for backtesting.py
│   ├── report_generator.py # Creates the structured report
│   ├── llm_service.py      # Interacts with LLM, manages context
│   └── state_manager.py    # Handles reading/writing run_state.json
├── prompts/
│   └── quant_analyst.txt   # Jinja2 template for the main LLM prompt
├── results/                  # Output directory for all runs (ignored by git)
│   └── RELIANCE.NS_2023-10-28_10-00-00/
│       ├── summary_report.md
│       ├── ...
├── .env                    # For API keys
├── requirements.txt
└── pyproject.toml
```