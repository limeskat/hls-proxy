import re
from urllib.parse import urlparse
from curl_cffi import requests
from hlsproxy.models import ResolverResult, StreamInfo
from hlsproxy.resolvers.base import BaseResolver, ResolverError

class GoozResolver(BaseResolver):
    """
    Resolver for gooz.aapmains.net
    Scrapes the embed page to find the underlying playlist URL.
    """
    
    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "gooz.aapmains.net" in url.lower()
        
    def resolve(self, url: str, **kwargs) -> ResolverResult:
        try:
            # Impersonate a browser to fetch the page
            r = requests.get(url, impersonate="chrome124")
            if r.status_code != 200:
                raise ResolverError(f"Failed to fetch embed page: HTTP {r.status_code}")
                
            # Search for the source URL in the Javascript
            # const source = "https://chatgpt.hereisman.net/playlist/52961/load-playlist";
            match = re.search(r'const\s+source\s*=\s*["\']([^"\']+)["\']', r.text)
            if not match:
                raise ResolverError("Could not find stream source URL in the page source.")
                
            stream_url = match.group(1)
            
            # Streaming CDN requires Referer and Origin headers matching the embed
            parsed = urlparse(url)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            
            return ResolverResult(
                stream=StreamInfo(
                    m3u8_url=stream_url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0.0.0 Safari/537.36"
                        ),
                        "Referer": url,
                        "Origin": origin,
                    },
                    impersonate="chrome124"
                ),
                title="Gooz Stream"
            )
        except Exception as e:
            raise ResolverError(f"Error while fetching embed page: {str(e)}")
