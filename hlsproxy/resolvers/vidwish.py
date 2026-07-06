from hlsproxy.resolvers.jwplayer import JWPlayerResolver

class VidwishResolver(JWPlayerResolver):
    """Resolver for vidwish.live streams."""
    domains = [
        "vidwish.live",
        "megaplay.buzz"
    ]
    
    strict_domain_headers = True
    
    api_endpoint = "getsources"
    _is_abstract = False
