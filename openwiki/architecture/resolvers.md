# Resolver System

hlsproxy uses a plugin-based resolver system to extract HLS streams from protected sites. Resolvers handle anti-bot bypasses, API interception, and stream extraction. Site-specific logic lives in external resolvers to keep the core repository neutral.

## BaseResolver Interface

All resolvers inherit from `BaseResolver` in `hlsproxy/resolvers/base.py`:

```python
class BaseResolver(ABC):
    """Subclass this to add support for a new site."""
    domains: list = []
    catch_all: bool = False
    priority: int = 100

    @abstractmethod
    def resolve(self, url: str, **kwargs) -> ResolverResult:
        """
        Take a user-provided URL, return a ResolverResult.
        Raise ResolverError if the stream cannot be resolved.
        """
        ...

    def can_handle(self, url: str) -> bool:
        """Check if this resolver should handle the given URL."""
        if self.catch_all:
            return True
        url_lower = url.lower()
        return any(d in url_lower for d in self.domains)
```

**Key Attributes:**
- `domains`: List of domain patterns this resolver handles (empty for catch-all)
- `catch_all`: If True, resolver handles all URLs (used for GenericResolver)
- `priority`: Used for resolver selection when multiple match (lower is preferred)

## Resolver Loading

Resolvers are discovered and loaded dynamically at runtime:

### 1. Internal Resolvers
Located in `hlsproxy/resolvers/`, the core repository hosts:
- `base.py`: BaseResolver and ResolverError
- `generic.py`: GenericResolver (catch-all fallback)

### 2. Persistent User Resolvers
Installed via `--install-resolver` to `~/.config/hlsproxy/resolvers/`

### 3. External Resolvers
Loaded via `--resolvers-source` flag:

```bash
# Local directory
hlsproxy https://example.com/stream-page --resolvers-source /path/to/resolvers/

# GitHub repository
hlsproxy https://example.com/stream-page --resolvers-source https://github.com/username/my-resolvers.git
```

External resolvers are cached in `~/.cache/hlsproxy_resolvers/` and cloned/updated via git.

**Loading Process:**
1. Scan `hlsproxy/resolvers/` for internal resolvers
2. Load from `~/.config/hlsproxy/resolvers/` for user-installed resolvers
3. Clone/update external resolvers from `--resolvers-source`
4. Scan all directories for classes inheriting from `BaseResolver`
5. Return list of available resolver classes

## ResolverResult

Resolvers return a `ResolverResult` containing:
- `stream`: `StreamInfo` object with m3u8 URL, headers, cookies, etc.
- `title`: Display title for the stream
- `quality_options`: List of quality variants (for multi-variant playlists)

```python
result = ResolverResult(
    stream=StreamInfo(
        m3u8_url="https://example.com/stream.m3u8",
        headers={"Referer": "https://example.com"},
        impersonate="chrome124",
    ),
    title="Example Stream",
)
```

## Available Internal Resolvers

### GenericResolver
**Domains:** *(Catch-all)*

**Features:**
- Fallback resolver for direct `.m3u8` URLs
- Assumes the provided URL is already a direct playlist
- No anti-bot bypasses or Playwright detection

**Priority:** 999 (always tried last)

## Example External Resolvers

> **Note:** The following resolvers are examples of site-specific logic and are **not** included in the core `hlsproxy` repository. They must be loaded as external plugins via `--resolvers-source` or installed locally.

### VidwishResolver
**Domains:** `vidwish.live`, `megaplay.buzz`

**Features:**
- Bypasses `devtools-detector` anti-debugging scripts
- Forces correct `video/MP2T` Content-Type headers to bypass `.jpg` file extension obfuscation
- Supports `--referer` injection to bypass strict Origin tracking (404/410 errors)

### VidtubeResolver
**Domains:** `vidtube.site`

**Features:**
- Bypasses Playwright detection
- Intercepts JSON APIs to extract obfuscated `.m3u8` links
- Cleans corrupt junk-byte headers injected into raw `.ts` segments

### GoozResolver
**Domains:** `gooz.aapmains.net` (and subdomains)

**Features:**
- Uses `curl_cffi` to impersonate standard Chrome TLS fingerprints
- Bypasses Cloudflare and strict CDN blocks

## Resolver Selection

When resolving a URL, hlsproxy:
1. Discovers all available resolvers
2. Filters to resolvers where `can_handle(url)` returns True
3. Sorts by priority (lower is preferred)
4. Calls `resolve()` on the first matching resolver
5. Falls back to GenericResolver if no other resolver matches

## CLI Integration

The CLI manages resolvers:

```python
# List available resolvers
hlsproxy --list-resolvers

# Install custom resolver
hlsproxy --install-resolver /path/to/resolver.py

# Remove installed resolver
hlsproxy --remove-resolver foxtrend
```

## Writing a Resolver

To create a new resolver:

1. **Inherit from BaseResolver:**
```python
from hlsproxy.resolvers.base import BaseResolver, ResolverError
from hlsproxy.models import StreamInfo, ResolverResult

class MySiteResolver(BaseResolver):
    domains = ["mysite.com", "www.mysite.com"]
    priority = 100

    def resolve(self, url: str, **kwargs) -> ResolverResult:
        # Extract m3u8 URL from page
        m3u8_url = self._extract_m3u8(url)

        # Return stream info
        return ResolverResult(
            stream=StreamInfo(
                m3u8_url=m3u8_url,
                headers=self._get_headers(url),
                impersonate="chrome124",
            ),
            title="My Site Stream",
        )

    def _extract_m3u8(self, url: str) -> str:
        # Use curl_cffi to fetch page
        # Parse HTML/JSON to find m3u8 URL
        pass
```

2. **Install or distribute:**
- Place in `~/.config/hlsproxy/resolvers/` for local use
- Publish as a GitHub repo and use `--resolvers-source`
- Submit a PR to merge into the core repository

## Limitations

- **No site logic in core:** Site-specific scraping logic must live in external resolvers
- **Single URL resolution:** Resolvers handle one URL at a time
- **No streaming extraction:** Resolvers must return a complete m3u8 URL, not stream segments directly
