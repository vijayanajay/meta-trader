# **HARD RULES — "Praxis" Mean-Reversion Engine**

These 30 rules are the engineering constitution for this project. They translate the project's philosophy—pragmatic simplicity for the chaotic Indian markets and an unwavering commitment to the integrity of the statistical learning process—into strict, actionable directives. They are not suggestions. Adherence is mandatory.

────────────────────────────

### I. System Integrity & Simplicity (The Nadh Principles)

[H-1] **100% Type Hints, Strictly Enforced.** All code must pass `mypy --strict`. We are building a deterministic machine, not a research script. Ambiguity is a bug.

[H-2] **Stateless Services, Always.** All services (`DataService`, `SignalEngine`, etc.) are instantiated by the `Orchestrator` and hold no state between calls. Configuration is passed down via dependency injection. Global state is forbidden.

[H-3] **Functions > 40 Lines Are a Code Smell.** If a function exceeds 40 logical lines, it must be refactored. The only exception is if the author can prove in the PR description that splitting it introduces more complexity than it removes.

[H-4] **No New Abstractions Without Proof.** Do not add a new class or design pattern unless it demonstrably removes more lines of duplicated code than it adds. Justify it with a before/after diff in the PR.

[H-5] **Prefer Deletion Over Abstraction.** If code is unused, delete it. Do not comment it out. The goal is the smallest possible codebase that fulfills the PRD. Every line is a liability.

[H-6] **`print()` Is Forbidden Outside the CLI Entry Point.** All diagnostic output, errors, and status updates must go through the centralized logger configured in `main.py`.

[H-7] **Side Effects Must Be Labeled.** Any function that performs I/O (filesystem, network) must have a `# impure` comment on the line directly above its definition. This makes pure, testable logic distinct from impure, mockable logic.

[H-8] **Strict Dependency Stack.** External dependencies are limited to: `pandas`, `numpy`, `statsmodels`, `yfinance`, `pydantic`, `ollama`, `openai`, `typer`, `python-dotenv`, `pytest`, `hurst`, `jinja2`, `pyarrow`, `tqdm`, and `numba`. Adding a new dependency is a major architectural decision and requires formal approval.

[H-9] **Zero Silent Failures.** Every `try...except` block must catch specific, anticipated exceptions (e.g., `FileNotFoundError`, `KeyError`). Bare `except:` clauses are forbidden. Failures must be logged with context and handled gracefully.

[H-10] **Configuration is Centralized and Immutable.** All operational parameters (thresholds, lookback periods, file paths) must be defined in `config.ini` and loaded into a Pydantic model once at startup. No magic numbers.

### II. Architectural Boundaries & Realism (The Market Principles)

[H-11] **`yfinance` is the Source of Truth.** For Indian equity data, `yfinance` is the only acceptable source. This is non-negotiable.

[H-12] **I/O Is Confined to `services/`.** All network and filesystem I/O is restricted to modules within the `services` directory. The `core/` logic (indicators, statistics, orchestration) must be pure and runnable offline with cached data.

[H-13] **The LLM is Blind to Price.** The LLM will **never** be given OHLCV data, charts, or any raw time-series information. This is the single most important rule to prevent it from overfitting to noise and hallucinating predictions.

[H-14] **The LLM Audits, It Does Not Originate.** The LLM's role is to provide a confidence score on a signal that has *already* been generated and validated by deterministic statistical rules. It is the final quality check, not the first step. It is a calculator, not a creator.

[H-15] **The Backtester is Brutally Realistic.** The cost model (brokerage, STT, volume-based slippage) is not an optional feature. It must be integrated into the core of the `ExecutionSimulator`. Reporting "gross returns" is forbidden.

[H-16] **Liquidity is a Non-Negotiable Gate.** The ₹5 Crore average daily turnover filter is the first check after a signal is generated. No computational resources will be spent analyzing a signal in an illiquid stock.

[H-17] **Market Regime Dictates Action.** The sector volatility filter is the primary defense. If the calculated sector volatility exceeds the threshold in `config.ini` (e.g., 22%), all signals for that stock are rejected, regardless of any other factor.

[H-18] **Secrets From Environment Only.** All API keys (if any are ever needed) must be loaded from environment variables via `.env`. The repository must contain a `.env.example` file.

[H-19] **Walk-Forward Testing is Mandatory.** The backtesting engine must use a walk-forward methodology, iterating one day at a time and using an expanding data window. A simple, single-pass backtest is scientifically invalid and forbidden.

[H-20] **The Codebase is the Strategy.** The system is a single, coherent strategy engine. Do not introduce frameworks for managing multiple strategies or agents (e.g., CrewAI, AutoGen). The focus is on perfecting this one specific, rigorous filtering process.

### III. Learning Integrity & Reproducibility (The Hinton Principles)

[H-21] **NO DATA LEAKAGE. EVER.** The entire signal generation, validation, and LLM audit pipeline must operate exclusively on the historical data window provided by the walk-forward loop. The final performance of the system is judged on a hold-out set that is touched exactly once, after all backtesting is complete. Violation of this rule invalidates the entire project.

[H-22] **The Objective Function is Explicit and Unchanging.** The primary metric for judging a signal's historical efficacy is a combination of Net Win Rate (>1.77%) and Profit Factor (>1.5), as defined in the PRD. This provides a clear, unambiguous objective for the learning process.

[H-23] **A Backtest is a Scientific Experiment.** For a given stock, configuration file, and data vintage, a backtest run must be 100% reproducible. There will be no stochastic elements in the core logic.

[H-24] **The Learning Signal is Recorded.** Every call to the `LLMAuditService` must log the exact statistical summary sent to the LLM. We must have a perfect, auditable record of what the model saw before it made its decision.

[H-25] **The LLM's Action Space is Constrained.** The `LLMAuditService` is responsible for parsing the LLM's response. It must expect and handle only a single floating-point number between 0.0 and 1.0. Any other output (text, JSON, etc.) is treated as a failure (score 0.0) and logged.

[H-26] **The Baseline is Deterministic.** The first N signals in a backtest (where N is the minimum sample size) are generated without an LLM audit, or with a default confidence score. This provides a fixed, reproducible benchmark against which the LLM's contribution is measured.

[H-27] **Statistical Guards are Immutable.** The core statistical tests (ADF, Hurst) and their thresholds are the "physics" of our system. They are defined in the configuration and are not to be altered by the LLM or any adaptive process in v1.0.

[H-28] **The Final Report is The Ground Truth.** The ultimate output of a backtest run is a report that clearly and honestly presents the performance metrics (Sharpe, Drawdown, etc.) after all costs. It must be the single source of truth for evaluating the system's efficacy.

[H-29] **PRs Must State Their Intent.** Every PR description must include a one-line rationale and the net change in Lines of Code (LOC), enforcing a conscious, minimalist decision-making process for every change.

[H-30] **Follow The Architecture.** The component responsibilities and data flows defined in the architecture document are not suggestions. Code must be placed in the correct module according to its function to maintain the system's conceptual integrity.