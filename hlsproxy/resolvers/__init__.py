import importlib
import pkgutil
from typing import List, Type
from .base import BaseResolver

def discover_resolvers() -> List[Type[BaseResolver]]:
    """
    Auto-discover all resolver classes in this package.
    Any .py file (except __init__.py and base.py) that defines
    a BaseResolver subclass gets picked up automatically.
    """
    resolvers = []
    
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        if module_name in ("__init__", "base"):
            continue
        
        module = importlib.import_module(f".{module_name}", package=__name__)
        
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) 
                and issubclass(attr, BaseResolver) 
                and attr is not BaseResolver
                and not getattr(attr, '_is_abstract', False)):
                resolvers.append(attr)
    
    # Sort by priority
    resolvers.sort(key=lambda r: r.priority)
    return resolvers

def find_resolver(url: str) -> BaseResolver:
    """Find the best resolver for a given URL."""
    resolver_classes = discover_resolvers()
    
    for cls in resolver_classes:
        instance = cls()
        if instance.can_handle(url):
            return instance
    
    raise RuntimeError("No resolver found. Is generic.py installed?")
