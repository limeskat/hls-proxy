from .base import BaseResolver, ResolverError
from hlsproxy.models import StreamInfo, ResolverResult

class GenericResolver(BaseResolver):
    """Fallback resolver: assume the URL is already a direct .m3u8 link."""
    
    domains = []
    catch_all = True
    priority = 999  # Always tried last
    
    def resolve(self, url: str) -> ResolverResult:
        # We no longer strictly check for ".m3u8" because many custom playlists
        # use extension-less paths (like /playlist/123/caxi). We trust the user's input.
        
        return ResolverResult(
            stream=StreamInfo(
                m3u8_url=url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                },
            ),
            title="Direct Stream",
        )
