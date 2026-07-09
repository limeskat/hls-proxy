# hlsproxy Quickstart

hlsproxy is a local HTTP proxy that extracts and plays HLS (`.m3u8`) streams directly in `mpv`. It supports loading custom scripts to bypass stream protections. The project follows a plugin-based architecture where site-specific extraction logic lives in external resolvers.

## What hlsproxy Does

hlsproxy provides a neutral network tool for playing HLS streams from protected sites:

- **Local HTTP Proxy**: Binds to a local port and proxies HLS playlists and segments
- **Stream Extraction**: Uses resolvers to extract `.m3u8` URLs from protected pages
- **mpv Integration**: Launches `mpv` with optimized settings for low-latency playback
- **Plugin System**: Supports custom resolvers for bypassing anti-bot and CDN protections
- **Header Injection**: Manually injects Referer/Origin headers to bypass strict tracking

> **Note**: This repository contains no site-specific extraction logic. It is a neutral network tool. Site-specific bypasses are provided as external resolvers.

## Installation

```bash
# Install in development mode
pip install -e .

# Requirements
# - Python 3.8+
# - mpv installed and available in $PATH
```

## Basic Usage

Play a stream using a generic or manually provided URL:

```bash
# Play a stream
hlsproxy https://example.com/stream-page

# Or use a direct m3u8 URL
hlsproxy https://example.com/stream.m3u8
```

### Loading External Resolvers

Load your own resolvers from a local path or a GitHub repo:

```bash
# From local directory
hlsproxy https://example.com/stream-page --resolvers-source /path/to/resolvers/

# From GitHub repo
hlsproxy https://example.com/stream-page --resolvers-source https://github.com/username/my-resolvers.git
```

### Managing Resolvers

```bash
# List available resolvers
hlsproxy --list-resolvers

# Install a custom resolver
hlsproxy --install-resolver /path/to/resolver.py

# Remove an installed resolver
hlsproxy --remove-resolver foxtrend
```

## Common Options

| Option | Description |
|--------|-------------|
| `--host <IP>` | Host IP to bind the proxy (default: 0.0.0.0) |
| `--port <PORT>` | Local proxy port (default: 18888) |
| `--impersonate <PROFILE>` | TLS fingerprint profile (e.g., `chrome124`) |
| `--no-play` | Start proxy without launching mpv |
| `--referer <URL>` | Manually override Referer header |
| `--origin <URL>` | Manually override Origin header |
| `--resolvers-source <URL/PATH>` | Load external resolvers from a directory or git repo |
| `--list-resolvers` | List currently available resolvers |
| `--install-resolver <PATH>` | Install a custom resolver script |
| `--remove-resolver <NAME>` | Remove an installed resolver |
| `--proxy <URL>` | Use upstream HTTP/SOCKS proxy |

## Architecture Overview

hlsproxy consists of several key components:

- **CLI (`hlsproxy/cli.py`)**: Command-line interface and entrypoint
- **Proxy Server (`hlsproxy/core/proxy.py`)**: Local HTTP proxy that serves playlists and segments
- **Proxy Delegate (`hlsproxy/core/proxy_delegate.py`)**: Handles request rewriting and header manipulation
- **Player (`hlsproxy/core/player.py`)**: mpv launcher
- **Resolver System (`hlsproxy/resolvers/`)**: Plugin system for extracting streams from protected sites
- **Session Management (`hlsproxy/core/session.py`)**: HTTP session handling with curl_cffi or requests

## Next Steps

- [Architecture: Proxy Server](architecture/proxy-server.md) - Understand how the proxy works
- [Architecture: Resolvers](architecture/resolvers.md) - Learn about the plugin system
- [Architecture: Data Models](architecture/models.md) - See the core data structures
- [Workflows: Usage](workflows/usage.md) - Detailed usage patterns and examples
- [Development Guide](development/development.md) - How to extend hlsproxy

## Supported Sites

As a neutral network tool, `hlsproxy` itself does not include support for specific sites out of the box. You must install external resolvers to add support for specific sites.

See [Architecture: Resolvers](architecture/resolvers.md) for more details on how the resolver plugin system works and examples of external resolvers.

## Troubleshooting

If you encounter 403 Forbidden or 410 Gone errors on supported sites, try using the `--referer` flag to provide the URL of the parent webpage where the video is embedded:

```bash
hlsproxy https://example.com/video --referer https://example.com/
```

## Legal Disclaimer

**hlsproxy** is a generic network utility. It does not host, store, or distribute any media content, and it has no affiliation with any third-party content providers.
