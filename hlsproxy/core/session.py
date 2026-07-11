try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    import requests
    HAS_CURL_CFFI = False

from hlsproxy.models import StreamInfo

def create_session(stream: StreamInfo):
    """Create a session configured for the stream."""
    if HAS_CURL_CFFI:
        return cffi_requests.Session(
            impersonate=stream.impersonate,
            headers=stream.headers,
            cookies=stream.cookies,
            proxies={"https": stream.proxy, "http": stream.proxy} if stream.proxy else None,
        )
    else:
        # Fallback to standard requests if the evasion library is not installed
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        })
        session.headers.update(stream.headers)
        if stream.cookies:
            session.cookies.update(stream.cookies)
        if stream.proxy:
            session.proxies.update({"https": stream.proxy, "http": stream.proxy})
        return session
