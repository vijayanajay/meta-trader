# System Memory & Design Log

This document records significant architectural decisions, refactorings, and learnings encountered during development.

---

### 2025-08-20: Flexible LLM Service Integration

**Context:**
The initial `LLMService` was tightly coupled to the OpenAI API. Task 2 required integrating OpenRouter to allow for a wider variety of models, such as `kimi-2` (Moonshot).

**Decision:**
The `LLMService` was refactored to support both OpenAI and any OpenAI-compatible API (like OpenRouter) via environment variables. This was achieved with minimal code changes by reusing the `openai` Python client, which can be configured with a custom `base_url`.

**Implementation:**
- **`.env` Configuration:** Introduced `LLM_PROVIDER` ("openai" or "openrouter") to select the active service. Added provider-specific variables for API keys, model names, and base URLs (`OPENROUTER_*`, `OPENAI_*`).
- **`LLMService.__init__`:** The constructor now reads `LLM_PROVIDER` and conditionally configures the `openai.OpenAI` client with the appropriate `api_key` and `base_url`.
- **Testing:** The test suite for `LLMService` was updated to mock `python-dotenv.load_dotenv` to prevent `.env` files from interfering with tests that rely on a clean environment. Tests were parameterized to cover both OpenAI and OpenRouter configurations.

**Learning:**
- A `load_dotenv()` call within a class constructor can lead to non-obvious test failures. When tests need to manipulate environment variables, the `load_dotenv` call itself should be mocked to ensure the test environment is properly isolated.
- The `openai` library's support for a custom `base_url` is a powerful feature for abstracting away the specific backend provider with very little effort, perfectly aligning with a "minimal LOC" philosophy.
