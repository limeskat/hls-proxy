import importlib
import pkgutil
from typing import List, Type
from .base import BaseResolver, ResolverError

def get_external_dir_path(external_dir: str) -> str:
    """If external_dir is a URL, clone or update it and return the local path."""
    import os
    import subprocess
    import hashlib
    
    if external_dir.startswith("http://") or external_dir.startswith("https://") or external_dir.startswith("git@"):
        cache_base = os.path.expanduser("~/.cache/hlsproxy_resolvers")
        os.makedirs(cache_base, exist_ok=True)
        
        repo_hash = hashlib.md5(external_dir.encode("utf-8")).hexdigest()
        repo_path = os.path.join(cache_base, repo_hash)
        
        if not os.path.exists(repo_path):
            print(f"[*] Fetching external resolvers from {external_dir}...")
            try:
                subprocess.run(["git", "clone", "--depth", "1", external_dir, repo_path], check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                print(f"[!] Failed to clone {external_dir}: {e.stderr.decode('utf-8')}")
                return ""
        else:
            print(f"[*] Updating external resolvers from {external_dir}...")
            try:
                subprocess.run(["git", "-C", repo_path, "pull"], check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                print(f"[!] Failed to update {external_dir} (maybe offline?): {e.stderr.decode('utf-8')}")
        
        # Check if the repo has a 'resolvers' subfolder
        if os.path.isdir(os.path.join(repo_path, "resolvers")):
            return os.path.join(repo_path, "resolvers")
        return repo_path
    
    return external_dir

def discover_resolvers(external_dir: str = None) -> List[Type[BaseResolver]]:
    """
    Auto-discover all resolver classes in this package and optionally an external directory.
    """
    import os
    import sys
    resolvers = []
    
    # Load internal resolvers
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        if module_name == "base":
            continue
        
        module = importlib.import_module(f".{module_name}", package=__name__)
        
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) 
                and issubclass(attr, BaseResolver) 
                and attr is not BaseResolver
                and not getattr(attr, '_is_abstract', False)):
                resolvers.append(attr)

    def load_from_dir(path: str):
        abs_path = os.path.abspath(path)
        if not os.path.isdir(abs_path):
            return
            
        path_added = abs_path not in sys.path
        if path_added:
            sys.path.insert(0, abs_path)
            
        try:
            for item in os.listdir(abs_path):
                item_path = os.path.join(abs_path, item)
                module_name = None
                
                if os.path.isfile(item_path) and item.endswith(".py") and item not in ("__init__.py", "base.py"):
                    module_name = item[:-3]
                elif os.path.isdir(item_path) and os.path.isfile(os.path.join(item_path, "__init__.py")):
                    module_name = item
                    
                if module_name:
                    try:
                        module = importlib.import_module(module_name)
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if (isinstance(attr, type) 
                                and issubclass(attr, BaseResolver) 
                                and attr is not BaseResolver
                                and not getattr(attr, '_is_abstract', False)):
                                if attr not in resolvers:
                                    resolvers.append(attr)
                    except Exception as e:
                        print(f"[!] Failed to load external resolver {item}: {e}")
        finally:
            if path_added:
                sys.path.remove(abs_path)

    # Load persistent user resolvers
    config_dir = os.path.expanduser("~/.config/hlsproxy/resolvers")
    load_from_dir(config_dir)

    # Load external resolvers
    if external_dir:
        actual_dir = get_external_dir_path(external_dir)
        if actual_dir:
            load_from_dir(actual_dir)
    
    # Sort by priority
    resolvers.sort(key=lambda r: r.priority)
    return resolvers

def find_resolver(url: str, external_dir: str = None) -> BaseResolver:
    """Find the best resolver for a given URL."""
    resolver_classes = discover_resolvers(external_dir)
    
    for cls in resolver_classes:
        instance = cls()
        if instance.can_handle(url):
            return instance
    
    raise ResolverError("No resolver found. Is generic.py installed?")
