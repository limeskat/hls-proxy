from curl_cffi import requests as cffi_requests
from hlsproxy.models import StreamInfo

def create_session(stream: StreamInfo) -> cffi_requests.Session:
    """Create a curl_cffi session configured for the stream with keep-alive pooling."""
    return cffi_requests.Session(
        impersonate=stream.impersonate,
        headers=stream.headers,
        cookies=stream.cookies,
        proxies={"https": stream.proxy, "http": stream.proxy} if stream.proxy else None,
    )
