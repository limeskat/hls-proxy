# Usage Workflows

This guide covers common workflows for using hlsproxy, including CLI usage, resolver management, and troubleshooting.

## Basic Usage

### Play a Stream

```bash
hlsproxy https://example.com/stream-page
```

This will:
1. Discover and select an appropriate resolver
2. Extract the m3u8 URL from the page
3. Start a local HTTP proxy on port 18888
4. Launch mpv to play the stream

### Direct Playlist

If you have a direct `.m3u8` URL:

```bash
hlsproxy https://example.com/stream.m3u8
```

This uses the GenericResolver (catch-all fallback).

### Proxy Without mpv

To start the proxy without launching mpv:

```bash
hlsproxy https://example.com/stream-page --no-play
```

You can then use the proxy URL in another player:

```bash
mpv http://127.0.0.1:18888/playlist.m3u8
```

### Specify Port

```bash
hlsproxy https://example.com/stream-page --port 8080
```

### Bind to Specific Host

```bash
hlsproxy https://example.com/stream-page --host 127.0.0.1
```

## Resolver Management

### List Available Resolvers

```bash
hlsproxy --list-resolvers
```

Output:
```
Available resolvers:
  VidwishResolver            domains: vidwish.live, megaplay.buzz
  VidtubeResolver            domains: vidtube.site
  GoozResolver               domains: gooz.aapmains.net
  GenericResolver            domains: (catch-all)
```

> [!NOTE]
> This output reflects currently installed or loaded external resolvers. Out-of-the-box, only the `GenericResolver` is available in the core repository.

### Install Custom Resolver

Install a local resolver script:

```bash
hlsproxy --install-resolver /path/to/resolver.py
```

Or install a directory of resolvers:

```bash
hlsproxy --install-resolver /path/to/resolvers/
```

The resolver is installed to `~/.config/hlsproxy/resolvers/`.

### Remove Installed Resolver

```bash
hlsproxy --remove-resolver foxtrend
```

### Load External Resolvers

Load resolvers from a local directory:

```bash
hlsproxy https://example.com/stream-page --resolvers-source /path/to/resolvers/
```

Load resolvers from a GitHub repository:

```bash
hlsproxy https://example.com/stream-page --resolvers-source https://github.com/username/my-resolvers.git
```

External resolvers are cloned to `~/.cache/hlsproxy_resolvers/` and updated on subsequent runs.

## Header Overrides

### Override Referer

Many sites require the Referer header to bypass 403 Forbidden or 410 Gone errors:

```bash
hlsproxy https://example.com/stream-page --referer https://example.com/
```

This is especially useful for sites that employ strict hotlink protection.

### Override Origin

```bash
hlsproxy https://example.com/stream-page --origin https://example.com/
```

### Combined Header Overrides

```bash
hlsproxy https://example.com/stream-page --referer https://example.com/watch --origin https://example.com/
```

### Note on Resolver Headers

Resolvers can already inject headers. The `--referer` and `--origin` flags only apply if the resolver doesn't already capture these headers:

```python
# In cli.py
if args.referer and "Referer" not in result.stream.headers:
    result.stream.headers["Referer"] = args.referer
if args.origin and "Origin" not in result.stream.headers:
    result.stream.headers["Origin"] = args.origin
```

## TLS Fingerprinting

### Use curl_cffi for Bypass

Use TLS fingerprint spoofing to bypass Cloudflare and strict CDN blocks:

```bash
hlsproxy https://example.com/stream-page --impersonate chrome124
```

Available profiles: `chrome124`, `chrome118`, `firefox`, `safari`, etc.

### Install curl_cffi

```bash
pip install curl_cffi
```

If curl_cffi is not installed, hlsproxy falls back to standard requests with a basic User-Agent.

## Subtitles

hlsproxy automatically proxies subtitle tracks and passes them to mpv:

```bash
hlsproxy https://example.com/stream-page
```

Subtitles are automatically detected and loaded from the playlist.

## Troubleshooting

### Port Already in Use

If the specified port is in use, hlsproxy automatically uses the next available port:

```
[*] Port 18888 in use. Using next available port: 18889
```

### Resolution Failed

If a resolver cannot find a stream:

```
[!] Resolution failed: No m3u8 URL found on page
```

Try:
1. Using a different resolver (check with `--list-resolvers`)
2. Providing the Referer header: `--referer https://example.com/`
3. Using a direct m3u8 URL

### 403 Forbidden or 410 Gone

On supported sites, try providing the Referer header:

```bash
hlsproxy https://example.com/stream-page --referer https://example.com/watch
```

### mpv Not Found

```
[!] Error: [Errno 2] No such file or directory: 'mpv'
[!] Please install mpv and ensure it is in your system's $PATH.
```

Install mpv:
- **Linux:** `sudo apt install mpv` or `sudo pacman -S mpv`
- **macOS:** `brew install mpv`
- **Windows:** Download from mpv.io

### Stream Not Playing

If the stream doesn't play:
1. Check the proxy URL: `http://127.0.0.1:18888/playlist.m3u8`
2. Verify the stream is loading (check console output)
3. Try `--no-play` to debug without mpv
4. Check the proxy logs for errors

## Advanced Usage

### Use Custom Headers

Resolvers can inject custom headers. For example, a resolver might add:

```python
result.stream.headers = {
    "User-Agent": "Mozilla/5.0 ...",
    "Referer": "https://example.com/",
    "Origin": "https://example.com",
}
```

### Multi-variant Playlists

For variant playlists, hlsproxy automatically detects and serves the main playlist with quality options. Select a quality in mpv using `q` or the quality menu.

### LAN Access

When binding to `0.0.0.0`, hlsproxy shows the LAN URL:

```
[+] LAN STREAM URL   : http://192.168.1.100:18888/playlist.m3u8
```

Use this URL to play the stream from other devices on the same network.
