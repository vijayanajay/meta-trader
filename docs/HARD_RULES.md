# HARD RULES — Self-Improving Quant Engine

These 30 hard rules are the engineering constitution for this project. They translate the project's philosophy—Kailash Nadh's pragmatic minimalism and Geoffrey Hinton's focus on learning signal integrity—into strict, actionable directives. They are not suggestions. Adherence is mandatory for all contributions to the v1.0 codebase.

────────────────────────────

### I. Code Quality & Simplicity (The Nadh Principles)

[H-1] **100% Type Hints, Strictly Enforced.** All new code must pass `mypy --strict`. No implicit `Any`. This is non-negotiable for creating a predictable, maintainable system.

[H-2] **No Mutable Global State.** Configuration is loaded once in `main.py` and passed down via dependency injection. All services and core components must be instantiable and stateless.

[H-3] **Functions > 40 Lines Require Justification.** If a function or method exceeds 40 logical lines of code, it must be refactored unless the author can prove in the PR description that splitting it harms clarity and increases net lines of code.

[H-4] **Zero New Abstractions Without Proof.** Do not add a new class, helper, or design pattern unless it demonstrably removes more lines of duplicated code than it adds. Provide a before/after diff in the PR to justify it.

[H-5] **Prefer Deletion Over Abstraction.** If code is unused, remove it. Do not comment it out or wrap it in a "just-in-case" abstraction. The goal is the smallest possible codebase that fulfills the PRD.

[H-6] **One Public Class Per Module.** A module's `__init__.py` should expose its primary public class. All helper classes or functions within that module must be private (prefixed with `_`).

[H-7] **Every Module Declares `__all__`.** The public API of every module must be made explicit. This prevents leaky abstractions and enforces clear boundaries between components.

[H-8] **Side Effects Must Be Labeled.** Any function that performs I/O (filesystem, network) or modifies state outside its local scope must have a `# impure` comment on the line directly above its definition.

[H-9] **No `TODO` or `FIXME` in Merged Code.** A PR is not "done" if it contains placeholders. Either complete the work or create a formal issue in the tracker and remove the comment.

[H-10] **`print()` Is Forbidden Outside `main.py`.** All diagnostic output, errors, and status updates must go through the centralized logger configured at application startup.

### II. System Architecture & Boundaries

[H-11] **Strict Dependency Stack.** External dependencies are limited to: `pandas`, `pandas-ta`, `backtesting.py`, `yfinance`, `python-dotenv`, `asteval`, `openai` (or equivalent LLM client), `configparser`, and `pytest`. Adding a new dependency requires a formal justification and approval.

[H-12] **Acyclic Import Graph.** Circular dependencies are a critical architectural failure and are forbidden. Use dependency injection to break cycles if necessary.

[H-13] **I/O Is Confined to `services/`.** All network and filesystem I/O is restricted to modules within the `services` directory (`data_service`, `llm_service`, `state_manager`). The `core/` logic must be pure and runnable offline.

[H-14] **Security Is Architectural, Not Optional.** The use of `eval()` or `exec()` on LLM output is forbidden. Strategy parsing **must** be implemented exclusively through the `StrategyEngine` which uses the sandboxed `asteval` library.

[H-15] **Secrets From Environment Only.** All API keys and sensitive credentials **must** be loaded from environment variables (via `.env`). The repository must contain a `.env.example` file. Hard-coding secrets is grounds for immediate PR rejection.

[H-16] **Configuration is Centralized.** All operational parameters (tickers, iterations, file paths) must be defined in `config.ini` and loaded by the `ConfigService`. No magic numbers or hard-coded strings in the application logic.

[H-17] **Observable Behavior is Stable.** The CLI entry point, the shape of `config.ini`, and the names of key output files (`run_state.json`, `summary_report.md`) are considered a stable API. Changes require explicit mention in the PR.

[H-18] **Green Tests Are The Gate.** All unit tests must pass, and a smoke test of the full loop (with a mocked LLM) must complete successfully before a PR can be merged.

### III. Experimental Integrity & Reproducibility (The Hinton Principles)

[H-19] **NO DATA LEAKAGE. EVER.** The LLM optimization loop **must** operate exclusively on the training dataset. The validation dataset is touched exactly once, by the `Orchestrator`, after all iterations are complete. This is the most important rule in this project.

[H-20] **State Is Atomic and Resumable.** The `StateManager` **must** write the `run_state.json` file atomically (e.g., write to temp then rename) after every single successful iteration. The `Orchestrator` **must** be able to resume an interrupted run from this file.

[H-21] **The Baseline Is Deterministic.** Iteration 0 is always the hard-coded baseline strategy (e.g., SMA Crossover). This provides a fixed, reproducible benchmark against which all LLM improvements are measured.

[H-22] **LLM Interaction Is Auditable.** Every call to the `LLMService` **must** log the essential metadata: `{model_name, timestamp, prompt_token_count, completion_token_count}`. The full prompt/response can be logged at a DEBUG level.

[H-23] **Cost Is Explicit.** Every LLM API call **must** log its prompt and completion token count to the console at an INFO level. API usage costs must never be invisible to the user running the tool.

[H-24] **The Optimization Target Is Explicit.** The primary metric for ranking strategies within the loop and for selecting the final winner is the Sharpe Ratio, as defined in the PRD. This provides a clear, unambiguous objective for the learning process.

[H-25] **Zero Silent Failures.** Every `try...except` block must catch specific, anticipated exceptions (e.g., `JSONDecodeError`, `requests.ConnectionError`). Bare `except:` clauses are forbidden. Failures must be logged with context and handled gracefully (retry or exit).

[H-26] **MVP-First Constraint.** For v1.0, the system is a single-agent, single-loop optimizer. Do not introduce complex orchestration frameworks (e.g., CrewAI, AutoGen, LangChain agents). The focus is on perfecting the core feedback loop.

[H-27] **The Core Loop Must Be Offline-Runnable.** The `Orchestrator` and `core` components must be testable without network access by mocking the `DataService` and `LLMService`.

[H-28] **PRs Must State Their Intent.** Every PR description must include a one-line rationale and the net change in Lines of Code (LOC), enforcing a conscious decision-making process for every change.

[H-29] **The Final Report Is The Ground Truth.** The `summary_report.md` is the ultimate output. It must clearly and honestly present the performance of the best strategy on both the training and the unseen validation data.

[H-30] **Follow The Architecture.** The component responsibilities and data flows defined in the architecture document are not suggestions. Code must be placed in the correct module according to its function.