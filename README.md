# hlsproxy

A local HTTP proxy to extract and play HLS (`.m3u8`) streams directly in `mpv`. It supports loading custom scripts to bypass stream protections.

> **Note**: This repository contains no site-specific extraction logic. It is a neutral network tool.

## Installation

```bash
pip install -e .
```

## Requirements
* Python 3.8+
* `mpv` installed and available in your system's `$PATH`.

## Usage

Play a stream using a generic or manually provided URL:
```bash
hlsproxy https://example.com/stream-page
```

### Loading External Resolvers
You can load your own resolvers from a local path or a GitHub repo link:

```bash
hlsproxy https://example.com/stream-page --resolvers-source /path/to/resolvers/
# OR
hlsproxy https://example.com/stream-page --resolvers-source https://github.com/username/my-resolvers.git
```

### Options:
* `--host <IP>`: Host IP to bind the proxy to (default: 0.0.0.0)
* `--port <PORT>`: Specify local proxy port (default: 18888).
* `--resolvers-source <DIR/URL>`: Path to a directory or a GitHub repo link containing external resolver scripts.
* `--install-resolver <PATH>`: Install a custom resolver Python script into the config folder (`~/.config/hlsproxy/resolvers`).
* `--remove-resolver <NAME>`: Remove an installed resolver by name (e.g. `foxtrend`).
* `--list-resolvers`: List all loaded plugins.
* `--impersonate <PROFILE>`: Specify TLS fingerprint profile (if `curl_cffi` is installed by the user).
* `--no-play`: Start proxy without launching mpv.
* `--referer <URL>`: Manually override the Referer header (useful for bypassing strict 403/410 errors).
* `--origin <URL>`: Manually override the Origin header.

---
## Documentation

This project's documentation is maintained using [OpenWiki](https://github.com/langchain-ai/openwiki), an AI-powered documentation agent.

You can view the full documentation in the `openwiki/` directory:
- [Quickstart](openwiki/quickstart.md)
- [Architecture](openwiki/architecture/)
- [Development](openwiki/development/development.md)
- [Workflows](openwiki/workflows/usage.md)

To update or regenerate the documentation, use the OpenWiki CLI:
```bash
npx openwiki --update
```

---
## Disclaimer
**hlsproxy** is a generic network utility. It does not host, store, or distribute any media content, and it has no affiliation with any third-party content providers.
