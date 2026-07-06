from abc import ABC, abstractmethod
from hlsproxy.models import ResolverResult

class BaseResolver(ABC):
    """
    Subclass this to add support for a new site.
    """
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

class ResolverError(Exception):
    pass
