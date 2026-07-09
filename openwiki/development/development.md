# Development Guide

This guide explains how to extend and contribute to hlsproxy.

## Project Structure

```
hlsproxy/
├── hlsproxy/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                 # CLI entrypoint and argument parsing
│   ├── models.py              # StreamInfo and ResolverResult dataclasses
│   ├── core/
│   │   ├── __init__.py
│   │   ├── proxy.py           # Local HTTP proxy server
│   │   ├── proxy_delegate.py  # Request handling and playlist/segment proxying
│   │   ├── session.py         # HTTP session creation (curl_cffi or requests)
│   │   └── player.py          # mpv launcher
│   └── resolvers/
│       ├── __init__.py        # Resolver discovery and loading
│       ├── base.py            # BaseResolver abstract class
│       └── generic.py         # GenericResolver (catch-all fallback)
├── tests/                     # Tests (currently empty)
├── pyproject.toml             # Project metadata and dependencies
└── README.md                  # User documentation
```

## Extension Points

### 1. Add a New Resolver

Create a new resolver by inheriting from `BaseResolver`:

```python
# hlsproxy/resolvers/mysite.py
from hlsproxy.resolvers.base import BaseResolver, ResolverError
from hlsproxy.models import StreamInfo, ResolverResult

class MySiteResolver(BaseResolver):
    domains = ["mysite.com", "www.mysite.com"]
    priority = 100

    def resolve(self, url: str, **kwargs) -> ResolverResult:
        """
        Extract m3u8 URL from mysite.com page.
        """
        # Fetch page
        session = self._get_session()
        r = session.get(url)
        html = r.text

        # Extract m3u8 URL (example: regex)
        import re
        m3u8_match = re.search(r'"(https://[^"]+\.m3u8[^"]*)"', html)
        if not m3u8_match:
            raise ResolverError("No m3u8 URL found")

        m3u8_url = m3u8_match.group(1)

        # Return stream info
        return ResolverResult(
            stream=StreamInfo(
                m3u8_url=m3u8_url,
                headers=self._get_headers(url),
                impersonate="chrome124",
            ),
            title="My Site Stream",
        )

    def _get_session(self):
        """Create session with appropriate headers."""
        from hlsproxy.core.session import create_session
        return create_session(StreamInfo(impersonate="chrome124"))

    def _get_headers(self, url: str) -> dict:
        """Return headers needed for the site."""
        return {"User-Agent": "Mozilla/5.0 ..."}
```

**To use your resolver:**

1. **Option A: Install locally**
   ```bash
   hlsproxy --install-resolver /path/to/mysite.py
   ```

2. **Option B: Publish as GitHub repo**
   ```bash
   hlsproxy --resolvers-source https://github.com/username/my-resolvers.git
   ```

### 2. Add a Custom Proxy Delegate

Customize how playlists and segments are fetched and rewritten:

```python
# hlsproxy/core/custom_delegate.py
import re
from abc import ABC
from hlsproxy.core.proxy_delegate import BaseProxyDelegate

class CustomProxyDelegate(BaseProxyDelegate):
    """Custom proxy logic for specific streams."""

    def handle_playlist(self, handler, url):
        # Call parent implementation
        super().handle_playlist(handler, url)

        # Additional playlist manipulation
        # ...

    def handle_segment(self, handler, upstream_url, req_type="seg"):
        # Call parent implementation
        super().handle_segment(handler, upstream_url, req_type)

        # Additional segment manipulation
        # ...
```

**To use your delegate:**

```python
from hlsproxy.core.custom_delegate import CustomProxyDelegate

result = ResolverResult(
    stream=StreamInfo(m3u8_url="https://example.com/stream.m3u8"),
    title="Custom Stream",
)
result.stream.proxy_delegate = CustomProxyDelegate
```

### 3. Modify CLI Arguments

The CLI is in `hlsproxy/cli.py`. To add new arguments:

```python
parser.add_argument("--my-flag", help="Description")
```

The argument will be available in the `args` namespace:

```python
if args.my_flag:
    # Do something
    pass
```

**Important:** Do not move argument parsing logic elsewhere. Keep it in `cli.py`.

## Code Style and Git Workflow

### Commit Message Format

Use the strict format: `- type: message`

**Types:**
- `feat`: New feature or resolver
- `fix`: Bug fix
- `refactor`: Code refactoring without behavior change
- `chore`: Maintenance tasks (dependencies, config)

**Examples:**
```bash
- feat: added vidtube.site support/resolver
- fix: repaired jwplayer referer logic
- refactor: simplified base resolver
- chore: update dependencies
```

**Do NOT use:**
- Conventional commits with parentheses
- Long descriptions
- Other commit message formats

### Git Workflow

1. Create feature branch: `git checkout -b feature/resolver-name`
2. Make changes following code style
3. Commit with correct format
4. Push and create pull request

## Testing

### Testing Framework

The project uses `pytest` for testing.

### Test Location

All tests must reside in `/tests` directory at the project root.

### Mocking Network Requests

When testing components, always mock network requests to avoid slow, stateful integration tests:

```python
# tests/test_resolver.py
import pytest
from unittest.mock import Mock, patch
from hlsproxy.resolvers.mysite import MySiteResolver

def test_resolve():
    resolver = MySiteResolver()

    with patch('hlsproxy.resolvers.mysite.requests.Session') as mock_session:
        # Setup mock response
        mock_response = Mock()
        mock_response.text = '{"url": "https://example.com/stream.m3u8"}'
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_session.return_value.get.return_value = mock_response

        # Test resolution
        result = resolver.resolve("https://mysite.com/video")
        assert result.stream.m3u8_url == "https://example.com/stream.m3u8"
```

### Running Tests

```bash
pytest tests/
```

## Immutable Boundaries

### Core Repository Neutrality

The core repository (`hlsproxy/`) must remain a neutral HTTP proxy. **DO NOT** add site-specific extraction logic to the core.

### No Heavy Evasion Libraries in pyproject.toml

Do not modify `pyproject.toml` to add heavy evasion libraries like `playwright` or `playwright-stealth`. These should only be used in external resolvers if needed.

**Exception:** `curl_cffi` is an allowed optional core dependency for TLS fingerprinting support via `session.py`, and standard libraries like `requests` are acceptable.

### Resolver Boundaries

- Site-specific scraping logic MUST NOT be added to the core repository
- All new site support must be developed as external plugins
- The core repository only hosts `BaseResolver` and `GenericResolver`
- External resolvers are loaded dynamically via `--resolvers-source` CLI flag

## Dependencies

### Core Dependencies

`pyproject.toml` defines core dependencies:

```toml
[project]
dependencies = [
    "curl_cffi>=0.5.0",  # Optional, for TLS fingerprinting
    "requests>=2.25.0",  # Required, for HTTP requests
]
```

### Adding Dependencies

Only add standard, neutral libraries to `pyproject.toml`. If a resolver needs a specific library (e.g., `playwright`), the user must install it manually.

## Documentation

### User Documentation

- `README.md`: Installation, usage, and features
- This development guide

### Code Comments

Add docstrings to public classes and methods:

```python
class MyResolver(BaseResolver):
    """Extract streams from mysite.com."""
    domains = ["mysite.com"]

    def resolve(self, url: str, **kwargs) -> ResolverResult:
        """
        Extract m3u8 URL from mysite.com page.

        Args:
            url: The page URL to extract from.
            **kwargs: Additional arguments (e.g., referer).

        Returns:
            ResolverResult with StreamInfo.

        Raises:
            ResolverError: If m3u8 URL cannot be extracted.
        """
        ...
```

## Common Patterns

### Using curl_cffi in Resolvers

```python
from hlsproxy.core.session import create_session
from hlsproxy.models import StreamInfo

class MyResolver(BaseResolver):
    def resolve(self, url: str, **kwargs) -> ResolverResult:
        # Create session with TLS fingerprinting
        stream = StreamInfo(impersonate="chrome124")
        session = create_session(stream)

        # Make requests
        r = session.get(url)
        # ...
```

### Handling Errors

```python
from hlsproxy.resolvers.base import ResolverError

class MyResolver(BaseResolver):
    def resolve(self, url: str, **kwargs) -> ResolverResult:
        try:
            # Extraction logic
            m3u8_url = self._extract_m3u8(url)
        except Exception as e:
            raise ResolverError(f"Failed to extract stream: {e}")
        # ...
```

### Parsing HTML

Use `requests` directly in resolvers:

```python
import requests

class MyResolver(BaseResolver):
    def _get_session(self):
        return requests.Session()

    def resolve(self, url: str, **kwargs) -> ResolverResult:
        session = self._get_session()
        r = session.get(url)
        r.raise_for_status()
        html = r.text
        # Parse HTML
        ...
```

## Getting Help

- Check existing resolvers in `hlsproxy/resolvers/` for examples
- Inspect proxy delegate logic in `hlsproxy/core/proxy_delegate.py` for request handling patterns
- Use `--list-resolvers` to see available resolvers during development
