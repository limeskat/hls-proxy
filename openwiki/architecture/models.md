# Data Models

hlsproxy uses a small set of dataclasses to represent streams, resolvers, and their configurations.

## StreamInfo

The central dataclass representing everything needed to fetch and play a stream.

**Location:** `hlsproxy/models.py`

```python
@dataclass
class StreamInfo:
    """Everything needed to fetch and play a stream."""
    m3u8_url: str
    base_url: str = ""
    headers: dict = field(default_factory=dict)
    impersonate: str = "chrome124"
    cookies: dict = field(default_factory=dict)
    proxy: Optional[str] = None  # upstream HTTP/SOCKS proxy
    chunk_size: int = 131072  # Default to 128KB chunks to reduce latency on live streams
    subtitles: list = field(default_factory=list)  # List of dicts like {'url': ..., 'lang': ...}
    proxy_delegate: Optional[type] = None  # Class derived from BaseProxyDelegate
```

### Fields

- **m3u8_url**: The primary HLS playlist URL to play
- **base_url**: Automatically set to the scheme+netloc of m3u8_url (defaults to empty)
- **headers**: Custom HTTP headers to include in requests (e.g., Referer, Origin, User-Agent)
- **impersonate**: TLS fingerprint profile for `curl_cffi` (e.g., "chrome124", "firefox")
- **cookies**: Cookie dictionary for authentication
- **proxy**: Optional upstream HTTP/SOCKS proxy (e.g., "socks5://127.0.0.1:1080")
- **chunk_size**: Buffer size for streaming TS segments (default: 128KB)
- **subtitles**: List of subtitle tracks, each with URL and language
- **proxy_delegate**: Custom proxy behavior class (see [Proxy Server Architecture](./proxy-server.md))

### Default Behavior

```python
# Create with defaults
stream = StreamInfo(m3u8_url="https://example.com/stream.m3u8")

# Create with headers
stream = StreamInfo(
    m3u8_url="https://example.com/stream.m3u8",
    headers={"Referer": "https://example.com/watch"},
    impersonate="chrome124"
)
```

## ResolverResult

Returned by resolvers to indicate stream resolution success.

**Location:** `hlsproxy/models.py`

```python
@dataclass
class ResolverResult:
    """What a resolver returns."""
    stream: StreamInfo
    title: str = "Stream"
    quality_options: list = field(default_factory=list)  # For multi-variant playlists
```

### Fields

- **stream**: The `StreamInfo` object containing stream details
- **title**: Human-readable title for the stream (used in mpv title)
- **quality_options**: List of quality variants for multi-variant playlists

### Example Usage

```python
# Simple resolution
result = ResolverResult(
    stream=StreamInfo(m3u8_url="https://example.com/stream.m3u8"),
    title="Example Stream",
)

# Resolution with headers
result = ResolverResult(
    stream=StreamInfo(
        m3u8_url="https://example.com/stream.m3u8",
        headers={"Referer": "https://example.com"},
        impersonate="chrome124",
    ),
    title="Example Stream",
)
```

## Type Relationships

```
ResolverResult
    └── stream: StreamInfo
            ├── m3u8_url: str
            ├── headers: dict
            ├── impersonate: str
            ├── cookies: dict
            ├── proxy: Optional[str]
            ├── chunk_size: int
            ├── subtitles: list
            └── proxy_delegate: Optional[type]
```

## StreamInfo in Practice

### Session Creation

`hlsproxy/core/session.py` creates a session from `StreamInfo`:

```python
def create_session(stream: StreamInfo):
    """Create a session configured for the stream with keep-alive pooling."""
    if HAS_CURL_CFFI:
        return cffi_requests.Session(
            impersonate=stream.impersonate,
            headers=stream.headers,
            cookies=stream.cookies,
            proxies={"https": stream.proxy, "http": stream.proxy} if stream.proxy else None,
        )
    else:
        # Fallback to standard requests
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        })
        session.headers.update(stream.headers)
        if stream.cookies:
            session.cookies.update(stream.cookies)
        if stream.proxy:
            session.proxies.update({"https": stream.proxy, "http": stream.proxy})
        return session
```

### Proxy Server Attachment

The proxy server attaches `StreamInfo` to enable request customization:

```python
server = HLSProxyServer((host, port), HLSProxyHandler, stream, session)
```

This allows the `HLSProxyHandler` to access stream metadata and delegate to custom proxy logic.

### Default Proxy Delegate

If no custom delegate is set, the proxy uses `DefaultProxyDelegate`:

```python
delegate = getattr(self.server.stream, "proxy_delegate", None)
if delegate is None:
    from hlsproxy.core.proxy_delegate import DefaultProxyDelegate
    delegate = DefaultProxyDelegate
    self.server.stream.proxy_delegate = delegate
```

## Extending StreamInfo

Resolvers can extend `StreamInfo` by setting the `proxy_delegate` attribute:

```python
from hlsproxy.core.proxy_delegate import CustomProxyDelegate

result = ResolverResult(
    stream=StreamInfo(m3u8_url="https://example.com/stream.m3u8"),
    title="Custom Stream",
)
result.stream.proxy_delegate = CustomProxyDelegate
```

This enables per-stream customization of playlist and segment handling.
