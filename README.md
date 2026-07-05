# hlsproxy

A command-line tool designed to bypass modern anti-scraping and anti-bot protections on embedded video streaming sites. It allows users to input a URL from a streaming site, automatically resolves the underlying HLS (`.m3u8`) stream, circumvents CDN restrictions (such as TLS fingerprinting, CORS, and strict header enforcement), and plays the video directly in `mpv` via a local proxy server.

## Installation

```bash
pip install -e .
```

## Requirements
* Python 3.8+
* `mpv` installed and available in your system's `$PATH`.

## Usage
Play a stream:
```bash
hlsproxy https://example.com/stream-page
```

Options:
* `--port <PORT>`: Specify local proxy port.
* `--impersonate <PROFILE>`: Specify TLS fingerprint profile (default: chrome124).
* `--no-play`: Start proxy without launching mpv.
* `--list-resolvers`: List all loaded plugins.
