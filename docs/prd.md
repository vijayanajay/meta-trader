Of course. As the Product Manager agent, my primary goal is to translate your vision into a clear, actionable set of requirements. The "Self-Improving Quant" project is a fantastic example of combining classical quantitative finance with modern AI, and a well-defined MVP is crucial for success.

Here is the Product Requirements Document (PRD) for the project, based on your description and structured using the provided template.

***

# Self-Improving Quant Engine PRD

## Intro

This document outlines the requirements for the "Self-Improving Quant Engine," a system designed to automate the discovery and refinement of stock trading strategies. For its Minimum Viable Product (MVP), the system will use a feedback loop where it backtests a strategy, generates a performance report, and inputs that report into a Large Language Model (LLM). The LLM then suggests improvements for the next iteration, creating a learning cycle that aims to discover strategies superior to a simple baseline.

## Goals and Context

-   **Project Objectives:**
    -   To build a functional, automated framework for iteratively discovering and improving quantitative trading strategies.
    -   To validate the use of LLMs as a "quantitative analyst" agent capable of suggesting data-driven strategy modifications.
    -   To create a baseline system that can be expanded upon for more complex, multi-asset, and robust strategy research in the future.

-   **Measurable Outcomes:**
    -   The system can successfully complete a minimum of 5 automated iterations without critical failure.
    -   The final strategy discovered by the system demonstrates a higher Sharpe Ratio than the initial baseline strategy on the same 2-year backtest period.

-   **Success Criteria:**
    -   The end-to-end loop (data fetch -> backtest -> report -> LLM -> new strategy -> backtest) is fully automated.
    -   The LLM consistently returns syntactically correct and logically plausible strategy modifications in the specified JSON format.
    -   The system produces a clear, final report summarizing the performance of all tested strategies and identifying the best one.

-   **Key Performance Indicators (KPIs):**
    -   **Edge Score:** The primary metric for ranking strategies, calculated as `(Net Profit % / Exposure Time %) * (abs(Sharpe Ratio) / abs(Sortino Ratio))`.
    -   Sharpe Ratio of generated strategies.
    -   Sortino Ratio of generated strategies.
    -   Maximum Drawdown [%] of generated strategies.
    -   Final Return [%] vs. Baseline Return [%] on validation data.

## Scope and Requirements (MVP / Current Version)

### Functional Requirements (High-Level)

-   **FR1: Data Ingestion:** The system must fetch 10 years of historical daily stock price data for a single, user-specified Indian stock ticker (e.g., `RELIANCE.NS`) from a public data source.
-   **FR2: Baseline Strategy:** The system must implement a hard-coded baseline strategy (e.g., RSI crossover) to serve as the starting point (Iteration 0).
-   **FR3: Backtesting Engine:** The system must perform a backtest of a given strategy on the most recent 2 years of the fetched data, calculating standard performance metrics.
-   **FR4: Performance Reporting:** The system must generate a structured, machine-readable report (JSON object) after each backtest, detailing the strategy used, performance metrics, and basic market context.
-   **FR5: LLM Integration & Prompting:** The system must be able to send the cumulative history of all previous reports to an LLM API. The prompt must instruct the LLM to act as a quantitative analyst and suggest a new strategy.
-   **FR6: Strategy Parsing & Execution:** The system must securely parse the structured JSON response from the LLM to extract new indicator definitions and buy/sell logic. It must then apply these to the data for the next backtest iteration.
-   **FR7: Iteration Loop:** The system must orchestrate the process from FR3 to FR6 in an automated loop for a pre-defined number of iterations.
-   **FR8: Results Persistence & Output:** The system must store the full report from every iteration. Upon completion, it must present a summary identifying the best-performing strategy found during the run.

### Non-Functional Requirements (NFRs)

-   **Performance:** A single backtest iteration (excluding the LLM API call) should complete in under 60 seconds.
-   **Scalability:** The MVP is designed for a single user running on a single machine. It does not require horizontal scalability.
-   **Reliability/Availability:** The system must include error handling to gracefully manage common issues like API failures from the data source or LLM, or syntactically incorrect suggestions from the LLM. It should log the error and halt the process cleanly.
-   **Security:**
    -   All API keys (data provider, LLM) must be managed via environment variables, not hard-coded.
    -   LLM-generated code/logic strings **must not** be executed using `eval()`. A safe expression parser must be used to prevent arbitrary code execution.
-   **Maintainability:** The codebase must be modular, with clear separation between data handling, strategy calculation, backtesting, reporting, and LLM interaction.
-   **Usability/Accessibility:** The system will be a Command-Line Interface (CLI) tool. All output, progress, and results must be logged to the console in a clear, human-readable format.

### User Experience (UX) Requirements (High-Level)

-   The user interacts with the system via a CLI.
-   The system provides real-time feedback on its current stage (e.g., "Fetching data...", "Running backtest for Iteration 2...", "Awaiting LLM response...").
-   The final output is a clean summary of the best strategy found and its performance metrics.

### Integration Requirements (High-Level)

-   **Integration Point 1:** A financial data provider API (e.g., `yfinance` library).
-   **Integration Point 2:** A Large Language Model API. The system is designed to be compatible with multiple providers through environment variable configuration.
    -   **Primary Provider:** OpenAI (e.g., `gpt-4-turbo`).
    -   **Alternative Provider:** OpenRouter, which enables access to a variety of models. The recommended model is `moonshotai/kimi-k2:free`.

### Testing Requirements (High-Level)

-   Comprehensive unit tests are required for core logic modules (e.g., report generation, LLM response parsing).
-   An integration test for the full loop is required, using a mocked LLM API to ensure all components work together.

## Epic Overview (MVP / Current Version)

-   **Epic 1: Core Backtesting Pipeline** - Goal: To build a non-iterative pipeline that can fetch data for one stock, apply a hard-coded baseline strategy, run a backtest, and generate a performance report. This validates the core quantitative components.
-   **Epic 2: LLM-Powered Iteration Engine** - Goal: To integrate the LLM API, construct the dynamic prompt with historical context, and build the main loop that parses LLM responses to drive subsequent backtest iterations.
-   **Epic 3: CLI & Operational Polish** - Goal: To wrap the system in a user-friendly CLI, implement robust error handling, add secure API key management, and ensure clear logging and final reporting.

## Key Reference Documents

-   `docs/architecture.md`
-   `docs/tech-stack.md`

## Post-MVP / Future Enhancements

-   **Walk-Forward Validation:** Implement a more robust testing methodology instead of a single train/test split.
-   **Multi-Asset Analysis:** Expand the system to run on a portfolio of stocks to find more generalized strategies.
-   **Human-in-the-Loop UI:** Create a simple web interface for a user to review and approve/reject LLM suggestions before they are run.
-   **LLM Self-Critique:** Add a step where the LLM critiques its own suggestion to identify potential flaws before the backtest is run.
-   **Expanded Action Space:** Allow the LLM to modify a wider range of parameters, such as indicator lengths, stop-loss/take-profit levels, and position sizing.

## Change Log

| Change      | Date       | Version | Description      | Author |
|-------------|------------|---------|------------------|--------|
| Initial PRD | 2023-10-27 | 1.0     | First draft of MVP | PM Agent |

## Initial Architect Prompt

### Technical Infrastructure

-   **Starter Project/Template:** None. To be built from scratch.
-   **Hosting/Cloud Provider:** Not applicable for MVP. The system will be a local CLI tool.
-   **Frontend Platform:** Not applicable for MVP.
-   **Backend Platform:** Python is required due to its mature data science and quantitative finance ecosystem (`pandas`, `pandas-ta`, `backtesting.py`).
-   **Database Requirements:** No formal database is required for the MVP. Iteration history and reports can be stored in-memory and written to a local JSON or CSV file at the end of a run.

### Technical Constraints

-   The `pandas-ta` library must be used for technical indicator calculations as specified.
-   The `backtesting.py` library is strongly recommended for its simplicity and detailed reporting.
-   Direct use of `eval()` on LLM output is strictly forbidden. A secure alternative like `asteval` or a custom-built parser is required.
-   The solution must integrate with a major LLM provider's API.

### Deployment Considerations

-   Deployment will be via a standard Python package setup (`pyproject.toml` or `setup.py`) and published to a Git repository.
-   No CI/CD pipeline is required for the MVP.

### Local Development & Testing Requirements

-   The project must include a `requirements.txt` or similar file for easy environment setup.
-   A simple CLI entry point should be provided to run the entire process (e.g., `python main.py --ticker RELIANCE.NS --iterations 10`).
-   Unit tests should be runnable via a single command (e.g., `pytest`).

### Other Technical Considerations

-   The architecture should be modular to easily swap out components in the future (e.g., different backtesting engines, different LLMs).
-   Focus on clear, well-documented code, as the logic of the prompts and the parsing of responses will be complex and critical to the system's success.