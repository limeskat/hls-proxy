from hlsproxy.resolvers.jwplayer import JWPlayerResolver

class VidtubeResolver(JWPlayerResolver):
    """Resolver for vidtube.site and vidtube.net streams."""
    domains = [
        "vidtube.site",
        "vidtube.net"
    ]
    
    # Vidtube/Nekostream strictly requires exact base_url spoofing
    strict_domain_headers = True
    
    # Vidtube uses getSourcesNew or getSources
    api_endpoint = "getsources"
    _is_abstract = False
