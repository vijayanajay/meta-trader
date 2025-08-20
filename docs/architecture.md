# Architecture

## 1. Introduction

This document outlines the technical architecture for the "Self-Improving Quant Engine." This revised architecture incorporates critical feedback focused on robustness, cost management, and improving the integrity of the AI-driven learning loop. The system remains a Command-Line Interface (CLI) tool for the MVP, but is now designed to be more resilient and to produce more generalizable results by directly addressing the risk of overfitting.

## 2. Architectural Goals & Constraints

The architecture is designed to meet the following key objectives and constraints:

*   **Modularity:** Each component has a distinct responsibility, allowing for easier testing and future extension.
*   **Security:** The system maintains its strict policy against executing LLM-generated code via `eval()`, using a sandboxed expression parser instead.
*   **Robustness & Resumability:** The system must be able to survive interruptions and resume a run from the last completed iteration, preventing loss of work and compute.
*   **Generalization:** The architecture explicitly incorporates a train/validation data split to combat overfitting and measure a strategy's out-of-sample performance.
*   **Cost-Awareness:** The system must track and manage LLM API costs by monitoring token usage and employing context management strategies.
*   **Rich Feedback:** The learning loop is enhanced with a more descriptive feedback signal, moving beyond a single metric to provide the LLM with deeper context for its suggestions.

## 3. System Architecture Overview

The system remains a sequential pipeline orchestrated by a central `Orchestrator`. However, it now includes explicit state management and a more sophisticated validation process.

### C4 Model - Level 2: Container Diagram

The high-level component interactions remain similar, but their internal responsibilities have been significantly enhanced.

```mermaid
graph TD
    subgraph SelfImprovingQuantEngine [Self-Improving Quant Engine (Python CLI Application)]
        direction LR
        Orchestrator(Orchestrator)
        StateManager(State Manager)
        DataService(Data Service)
        Backtester(Backtesting Engine)
        ReportGenerator(Rich Report Generator)
        LLMService(LLM Service)
        StrategyParser(Secure Strategy Parser)

        Orchestrator -- "Load/Save State" --> StateManager
        Orchestrator -- "1. Get Data" --> DataService
        Orchestrator -- "2. Run Backtest" --> Backtester
        Orchestrator -- "3. Generate Report" --> ReportGenerator
        Orchestrator -- "4. Get Suggestion" --> LLMService
        Orchestrator -- "5. Parse Suggestion" --> StrategyParser
    end

    User[CLI User] -- "python main.py --ticker [TICKER]" --> Orchestrator
    DataService -- "Fetches OHLCV Data" --> ExternalDataProvider[External Data Provider API<br/>(e.g., yfinance)]
    LLMService -- "Sends Reports, Gets JSON Strategy" --> ExternalLLM[External LLM API<br/>(e.g., OpenAI)]
    StateManager -- "Reads/Writes run_state.json" --> LocalFS[(Local Filesystem)]
    DataService -- "Reads/Writes stock.parquet" --> LocalFS
    Orchestrator -- "Outputs Final Summary" --> User
```

## 4. Component Breakdown

| Component | Responsibility | Inputs | Outputs | Implementation Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Orchestrator** | Manages the main iteration loop, coordinates components, and orchestrates the final validation run. | CLI arguments. | Final summary report to console. | On startup, it uses the `StateManager` to check for and load a previous run. |
| **State Manager** | Handles persistence. Reads and writes the complete run state (history of reports) to disk after each iteration. | The current list of reports. | A `run_state.json` file. | This ensures that if the process fails, it can be resumed from the last successful iteration. |
| **Data Service** | Fetches historical data and stores it in a versioned Parquet file. Splits data into training and validation sets. | Ticker, date range. | Two `pandas` DataFrames: `train_data`, `validation_data`. | Using Parquet with metadata is more robust than a simple pickle/CSV cache. |
| **Backtesting Engine** | Executes a backtest on the **training data**. Enforces a strict execution timeout to prevent runaway calculations. | `train_data` DataFrame, strategy definition. | A results object from `backtesting.py`. | The timeout is a critical safeguard against computationally expensive LLM suggestions. |
| **Rich Report Generator** | Creates a detailed JSON report with a rich feedback signal. Calculates a custom **Edge Score**. | Backtest results, strategy definition. | A structured JSON object. | The report includes the Edge Score (`(Net Profit % / Exposure Time %) * (abs(Sharpe Ratio) / abs(Sortino Ratio))`), drawdown details, and a summary of the 5 worst trades to give the LLM deep context. |
| **LLM Service** | Manages LLM interaction, tracks token usage, and implements a context summarization strategy. | Cumulative history of reports. | Raw JSON string from the LLM. | For long histories, it will summarize older reports to keep the prompt within cost and token limits. Logs token count for each call. |
| **Secure Strategy Parser** | Safely parses and validates the LLM's JSON response, including an expanded set of "tools" for risk management. | Raw JSON string from the LLM. | A validated strategy definition object. | Uses `asteval` for safe expression evaluation. Can now parse optional risk management parameters. |

## 5. Data Flow and State Management

The system is designed for resilience and to produce generalizable results.

1.  **Initialization:** The `Orchestrator` starts. It instructs the `StateManager` to look for a `run_state.json` file.
    *   **If found:** The state (history of reports) is loaded, and the loop resumes from the next iteration.
    *   **If not found:** A new run is initiated, starting with the hard-coded baseline strategy (Iteration 0).
2.  **Data Split:** The `Data Service` fetches 10 years of data, saving it to a local Parquet file. It splits this into an 8-year **training set** and a 2-year **validation set**. The validation set is held aside and is not used in the main loop.
3.  **The Iteration Loop (on Training Data):**
    a. The `Backtesting Engine` runs the current strategy on the **training set** within a fixed timeout.
    b. The `Rich Report Generator` creates a detailed report, including the **Edge Score**.
    c. The new report is appended to the `history` list.
    d. The `StateManager` saves the entire `history` list to `run_state.json`.
    e. The `LLM Service` takes the `history`, potentially summarizing older entries, and sends it to the LLM. It logs the token count for the call.
    f. The `Secure Strategy Parser` validates and parses the LLM's response into a new strategy definition.
4.  **Final Validation (Out-of-Sample Testing):**
    a. After all iterations are complete, the `Orchestrator` selects the top 3-5 strategies from the `history` based on their **Edge Score on the training data**.
    b. It then runs these top strategies through the `Backtesting Engine` one by one, but this time using the unseen **validation set**.
    c. The final strategy presented to the user is the one with the highest **Edge Score on the validation data**. This provides a much more honest assessment of the strategy's potential performance.

## 6. LLM Action Space & Secure Parsing

To give the LLM more sophisticated control, its "action space" is expanded beyond simple signals. It can now suggest risk management rules.

### Expanded LLM Output Contract (JSON)

The LLM is prompted to return a JSON object that may include an optional `risk_management` block.

```json
{
  "rationale": "The previous strategy had high returns but also a large drawdown. I am adding a 10% stop-loss to control risk.",
  "indicators": [
    { "name": "SMA_fast", "type": "sma", "params": { "length": 20 } },
    { "name": "SMA_slow", "type": "sma", "params": { "length": 50 } }
  ],
  "buy_signal": "SMA_fast > SMA_slow",
  "sell_signal": "SMA_fast < SMA_slow",
  "risk_management": {
    "stop_loss_pct": 0.10,
    "take_profit_pct": 0.25
  }
}
```

The `Secure Strategy Parser` will safely parse this structure. If the `risk_management` block or its keys are absent, the backtest will run without stop-loss or take-profit orders. This provides a "dictionary of tools" the LLM can choose to use.

## 7. Validation and Generalization Strategy

To address the critical risk of overfitting, the system's core methodology is built around a train/validation split.

*   **Purpose:** The LLM's job is to find strategies that work well on the **training data**. This is the learning phase.
*   **Insulation:** The LLM *never* sees the performance results from the validation data during its iteration loop. This prevents it from cheating and fitting to the out-of-sample period.
*   **Final Judgment:** The validation set acts as an unbiased judge. A strategy that performs well on both training and validation data is more likely to be robust and have true predictive power. Reporting the validation score as the final result provides a more realistic performance expectation.

## 8. Error Handling and Logging

*   **API Failures:** `Data Service` and `LLM Service` will use exponential backoff for retries on transient errors.
*   **State Corruption:** If `run_state.json` is malformed, the `StateManager` will log an error and prompt the user to start a new run.
*   **Backtest Timeout:** If a backtest exceeds its allocated time (e.g., 60 seconds), it will be terminated, the iteration will be marked as a failure in the report, and the loop will continue.
*   **Token Usage Logging:** The `LLM Service` will log the prompt and completion token count for every API call to the console, providing visibility into costs.

## 9. Directory Structure

```
self_improving_quant/
├── main.py                 # CLI entry point
├── data/
│   └── stock_data.parquet  # Stored financial data
├── core/
│   ├── __init__.py
│   ├── orchestrator.py     # Main control loop
│   ├── strategy.py         # Strategy definition
│   ├── backtester.py       # Wrapper for backtesting.py
│   └── models.py           # Pydantic models for reports, strategies
├── services/
│   ├── __init__.py
│   ├── data_service.py     # Fetches and splits data
│   ├── llm_service.py      # Interacts with LLM, manages context
│   ├── parser_service.py   # Secure strategy parser
│   └── state_manager.py    # Handles reading/writing run state
├── utils/
│   ├── __init__.py
│   └── logging_config.py   # Centralized logging configuration
├── prompts/
│   └── quant_analyst.txt   # The main prompt template for the LLM
├── run_state.json          # Persisted state of the current run
├── .env
├── .env.example
├── requirements.txt
└── pyproject.toml
```