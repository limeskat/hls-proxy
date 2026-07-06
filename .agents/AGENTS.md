# AI Agent Instructions (hlsproxy)

This file serves as the programmatic contract for any AI agents interacting with the `hlsproxy` repository. Adhere strictly to the guidelines and workflows defined below.

## 1. Commands
* **Setup**: Ensure dependencies are installed via `pip install -e .`.
* **Run Proxy Locally**: Use `hlsproxy <URL>` or `python -m hlsproxy <URL>`.
* **Testing**: Run tests using `pytest tests/`.
* **Linting**: No strict linter is enforced, but adhere to PEP 8 standards.

## 2. Testing Architecture
* **Framework**: `pytest`.
* **Location**: All tests must reside in the `/tests` directory at the project root.
* **Mocks**: When testing components, always mock network requests to avoid slow, stateful integration tests.

## 3. Code Style and Git Workflow
* **Commit Messages**: Do NOT use standard conventional commits with parenthesis or long descriptions. You must strictly use the following exact format:
  `- type : message`
  *Examples:*
  `- feat : added vidtube.site support/resolver`
  `- fix : repaired jwplayer referer logic`
  `- refactor : simplified base resolver`

## 4. Project Architecture
* **`hlsproxy/cli.py`**: The entrypoint for parsing user arguments (e.g., `--referer`, `--origin`). Do not place parsing logic elsewhere.
* **`hlsproxy/core/proxy.py`**: The local HTTP proxy server. This handles payload manipulation (like stripping junk bytes or forcing M2PT headers) and stream fetching.
* **`hlsproxy/resolvers/`**: The core modular plugin system. 
  * Site-specific scraping logic MUST NOT be added to the core repository. All new site support must be developed as external plugins.
  * The core repository only hosts `BaseResolver` and `GenericResolver`.
  * External resolvers are loaded dynamically via the `--resolvers-source` CLI flag.


## 5. Immutable Boundaries
* **DO NOT** add evasion libraries like `curl_cffi`, `playwright`, or `playwright-stealth` to the core `pyproject.toml`. The core repository must remain a neutral HTTP proxy. If users need them for external plugins, they must install them manually.
* **DO NOT** modify the `pyproject.toml` unless explicitly instructed to add a standard, neutral library (like `requests`).
