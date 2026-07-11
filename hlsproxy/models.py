from dataclasses import dataclass, field
from typing import Optional
import urllib.parse

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
    subtitles: list = field(default_factory=list) # List of dicts like {'url': ..., 'lang': ...}
    proxy_delegate: Optional[type] = None  # Class derived from BaseProxyDelegate

    def __post_init__(self):
        if not self.base_url:
            p = urllib.parse.urlparse(self.m3u8_url)
            self.base_url = f"{p.scheme}://{p.netloc}"

@dataclass
class ResolverResult:
    """What a resolver returns."""
    stream: StreamInfo
    title: str = "Stream"
    quality_options: list = field(default_factory=list)  # For multi-variant playlists
