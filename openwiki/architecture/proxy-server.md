# Proxy Server Architecture

hlsproxy uses a local HTTP proxy server to serve HLS playlists and segments to `mpv`. The proxy handles request rewriting, header manipulation, and streaming of TS segments with anti-corruption measures.

## Core Components

### HLSProxyServer (`hlsproxy/core/proxy.py`)

A `ThreadingHTTPServer` that serves HLS content. It attaches a `StreamInfo` and `Session` to each request handler.

**Key Responsibilities:**
- Binds to a local port and listens for HTTP GET requests
- Routes requests to `/playlist.m3u8` and `/req` endpoints
- Manages proxy delegate instances for request handling

### HLSProxyHandler (`hlsproxy/core/proxy.py`)

The HTTP request handler class that processes incoming requests:

```python
def do_GET(self):
    delegate = getattr(self.server.stream, "proxy_delegate", None)
    if delegate is None:
        from hlsproxy.core.proxy_delegate import DefaultProxyDelegate
        delegate = DefaultProxyDelegate
        self.server.stream.proxy_delegate = delegate

    delegate_instance = delegate()

    if self.path == "/playlist.m3u8":
        delegate_instance.handle_playlist(self, self.server.stream.m3u8_url)
    elif self.path.startswith("/req"):
        # Handle segment/subtitle requests
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        upstream_url = qs.get("url", [""])[0]
        req_type = qs.get("type", ["seg"])[0]

        if req_type == "m3u8":
            delegate_instance.handle_playlist(self, upstream_url)
        else:
            delegate_instance.handle_segment(self, upstream_url, req_type=req_type)
    else:
        self.send_response(404)
```

**Endpoints:**
- `/playlist.m3u8`: Serves the main playlist with rewritten URIs
- `/req.m3u8?type=m3u8&url=<URL>`: Serves upstream playlists
- `/req.ts?type=seg&url=<URL>`: Serves TS segments
- `/req.vtt?type=sub&url=<URL>`: Serves subtitle files

> [!NOTE]
> The proxy code handles any path starting with `/req` and relies on the `type` query parameter for routing. The `.m3u8`, `.ts`, and `.vtt` file extensions in the endpoint path are purely cosmetic to ensure client compatibility (e.g., some players might refuse a URL that doesn't end in `.ts`).

### DefaultProxyDelegate (`hlsproxy/core/proxy_delegate.py`)

The default proxy implementation with robust TS start stripping and strict Range header handling. Resolvers can subclass this to customize behavior.

## Playlist Rewriting

The proxy rewrites all URIs in the playlist to point to itself, enabling seamless streaming:

1. **Junk Byte Stripping**: Removes junk bytes before `#EXTM3U` tag (e.g., "caxi" or "load" prefixes)
2. **URI Rewrite**: Replaces all `URI="..."` in tags with proxied URLs
3. **Segment Rewriting**: Rewrites segment and sub-playlist URIs to use `/req` endpoints
4. **Variant Detection**: Automatically detects variant playlists by checking for `#EXT-X-STREAM-INF` tags

### Example Rewrite

**Original playlist:**
```
#EXTM3U
#EXT-X-KEY:METHOD=AES-128,URI="https://example.com/key.bin"
segment001.ts
segment002.ts
```

**Rewritten playlist:**
```
#EXTM3U
#EXT-X-KEY:METHOD=AES-128,URI="http://127.0.0.1:18888/req.ts?type=seg&url=https%3A%2F%2Fexample.com%2Fkey.bin"
http://127.0.0.1:18888/req.ts?type=seg&url=https%3A%2F%2Fexample.com%2Fsegment001.ts
http://127.0.0.1:18888/req.ts?type=seg&url=https%3A%2F%2Fexample.com%2Fsegment002.ts
```

## Segment Proxying

The proxy handles TS segments with several important features:

### TS Start Stripping

Many CDNs inject junk bytes at the start of TS segments (e.g., "caxi", "load"). The proxy buffers the first 2KB of data to find the MPEG-TS sync byte pattern (`0x47 0x47 0x47`):

```python
# The buffer must be at least a few kilobytes (e.g. 2KB) to ensure we have enough bytes 
# to check the pattern, avoiding negative ranges for very small buffers.
for i in range(max(0, len(buffer) - 188*3)):
    if buffer[i] == 0x47 and buffer[i+188] == 0x47 and buffer[i+188*2] == 0x47:
        ts_start = i
        break
```

The proxy then strips the junk bytes before sending the segment to `mpv`.

### Range Header Handling

The proxy explicitly does **not** forward the Range header for TS segments to avoid offset corruption. This is critical because:
- The proxy must strip junk bytes, which changes the segment length
- Forwarding Range headers would cause `mpv` to request incorrect byte ranges
- For subtitles, Range headers are forwarded because they don't require byte-level offset correction

### Encoding Handling

The proxy forces `Accept-Encoding: identity` to prevent dynamic chunked gzipping of TS files, which breaks slow reads and causes corruption.

### Retry Logic

Segments are retried up to 3 times on failure, with a 1-second delay between attempts.

## Proxy Delegate Pattern

The proxy delegate pattern allows resolvers to customize how the proxy handles requests:

```python
class CustomProxyDelegate(BaseProxyDelegate):
    def handle_playlist(self, handler, url):
        # Custom playlist rewriting logic
        pass

    def handle_segment(self, handler, url, req_type="seg"):
        # Custom segment handling logic
        pass
```

Resolvers attach delegates to `StreamInfo`:

```python
from hlsproxy.core.proxy_delegate import CustomProxyDelegate

result.stream.proxy_delegate = CustomProxyDelegate
```

## Session Management

The proxy uses `curl_cffi` when available for TLS fingerprint spoofing, falling back to `requests`:

```python
# Create session with impersonation
session = cffi_requests.Session(
    impersonate="chrome124",
    headers=stream.headers,
    cookies=stream.cookies,
    proxies={"https": stream.proxy, "http": stream.proxy} if stream.proxy else None,
)
```

This enables bypassing Cloudflare and strict CDN blocks when combined with appropriate resolvers.

## Logging

The proxy only logs non-200 responses and playlist requests:

```python
def log_message(self, fmt, *args):
    if len(args) > 1 and args[1] != "200":
        print(f"[proxy] {self.path}  →  {args[1]}")
    elif "m3u8" in self.path or "playlist" in self.path:
        print(f"[proxy] {self.path[:60]}...  →  200 (playlist)")
```

This keeps the console output clean while still showing errors.
