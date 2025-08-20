# HARD RULES — Self-Improving Quant Engine

These 30 hard rules express the combined mindset for this project: Kailash Nadh's pragmatism (minimalism, fast iteration, robust code) and Geoffrey Hinton's experimental rigor (reproducibility, measured discovery, auditable results). Follow them strictly for v1.0 development.

──────────────────────────── 3. HARD RULES ───────────────────────────────────

[H-1] **Preserve observable behaviour:** CLI flags, config shape, filenames (`run_state.json`, `stock_data.parquet`), and emitted logs must remain stable across changes unless an explicit migration note accompanies the change.

[H-2] **Touch only `self_improving_quant/`, `tests/`, and `docs/`.** Leave infra and root files (CI, `pyproject.toml`, lockfiles) unchanged unless a separate PR documents the reason.

[H-3] **Prefer deletion over clever rewrites:** Remove unused code rather than wrap it in abstraction. Keep the codebase minimal and focused on the core loop.

[H-4] **Zero new abstractions unless they eliminate ≥2 near-identical copies of logic.** Show before/after examples in the PR description to justify any new class or helper.

[H-5] **Every code suggestion or PR must show net LOC delta and a one-line rationale for the delta.** This enforces a bias toward simplicity.

[H-6] **Green tests are non-negotiable:** No merge without passing unit tests and a short smoke run of the orchestrator with a mocked LLM.

[H-7] **100% type hints.** Code must pass `mypy --strict` with no implicit `Any` except in third-party stubs.

[H-8] **No mutable global state.** Load runtime config once (in `main.py`) and pass dependencies explicitly; prefer pure functions.

[H-9] **Any function or method > 40 logical lines is a smell.** Refactor or delete unless splitting demonstrably harms clarity and adds net LOC.

[H-10] **External dependencies limited to the chosen stack:** `pandas`, `pandas-ta`, `backtesting.py`, `yfinance`, `python-dotenv`, `asteval`, an LLM client (`openai` or equivalent), and `pytest`. Add nothing else without a written justification in the PR.

[H-11] **Import graph must be acyclic.** In-function imports allowed only to avoid heavy startup cost and must include a comment explaining why.

[H-12] **Zero silent failures:** No bare `except:`; always catch concrete exceptions (e.g., `JSONDecodeError`, `APIError`), log via the shared logger, and re-raise or exit non-zero where appropriate.

[H-13] **Network I/O is explicit and confined:** All HTTP/LLM/data downloads live only in `services/data_service.py` and `services/llm_service.py`. Core logic (`orchestrator`, `backtester`) must be importable and runnable offline.

[H-14] **No `TODO`, `FIXME`, or commented-out code allowed in committed diffs.** Resolve the issue, create a ticket, or remove the code before merge.

[H-15] **Max one public class per module.** Helper classes/functions must be private (prefix with `_`).

[H-16] **Pure-function bias:** Functions with side-effects (I/O, state changes) must carry a `# impure` comment immediately above the definition.

[H-17] **Every module declares `__all__` to make its public API explicit.** Avoid `from x import *`.

[H-18] **`print()` allowed only in `main.py` or dedicated CLI output modules.** Use the shared logger elsewhere.

[H-19] **No `eval()`, `exec()`, or runtime monkey-patching.** Strategy parsing MUST use the sandboxed `asteval` module as specified in the architecture.

[H-20] **Config keys are `snake_case`.** Normalize or reject other keys at load time with a clear error message.

[H-21] **Core library must be offline-safe:** The main orchestration loop must be runnable with mocked data and LLM services without requiring network access.

[H-22] **LLM usage is experimental and auditable:** Every LLM call MUST log `{prompt_version, prompt_hash, model, temperature, token_count, response, timestamp}` to a local audit file.

[H-23] **Deterministic baseline first:** The LLM-enabled decision path must have a deterministic, hard-coded baseline strategy (RSI Crossover) as Iteration 0 to measure marginal lift.

[H-24] **Experiments are reproducible:** Every run writes a run-config JSON (inputs, scorer mode, prompt_version, seed) to `results/runs/` and seeds all RNGs for deterministic replay.

[H-25] **MVP-first constraint:** For v1.0, do not introduce complex agentic orchestration (e.g., CrewAI, AutoGen). The single-agent feedback loop is the sole focus.

[H-26] **No data leakage:** The LLM iteration loop MUST only operate on the training dataset. The validation dataset is touched exactly once, after all iterations are complete, for the final report. This is non-negotiable.

[H-27] **State is atomic and resumable:** The `run_state.json` file must be written successfully at the end of each complete iteration. The orchestrator must be able to resume from this state file if interrupted.

[H-28] **Cost management is explicit:** Every LLM API call must log its prompt and completion token count to the console. No invisible API calls.

[H-29] **Secrets are managed via environment:** All API keys MUST be loaded from environment variables (`.env` file) and never hard-coded in the source. The repo must include a `.env.example` file.

[H-30] **Optimization target is explicit:** The primary metric for ranking strategies during and after the loop is the custom "Edge Score" defined in the architecture, not a vague goal like "profitability."

---

**Notes:**
- These rules are intentionally strict to keep experiments fast, auditable, and reproducible. Follow them literally for v1.0; we can relax or extend specific items later with documented justification.
- Suggested follow-up: add `docs/HARD_RULES.md` to the repo and implement a pre-commit hook enforcing the `TODO`/`FIXME` ban, presence of `# impure` comments, and `__all__` declarations.