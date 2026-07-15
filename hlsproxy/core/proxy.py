import re
import ipaddress
import socket
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from hlsproxy.models import StreamInfo
from hlsproxy.core.session import create_session

BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / cloud metadata
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),         # IPv6 ULA
    ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
]

def is_safe_url(url: str) -> bool:
    """Check if a URL resolves to a non-private IP address."""
    try:
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False
        # Allow localhost only if it's the proxy itself (checked separately)
        ip = ipaddress.ip_address(socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)[0][4][0])
        for network in BLOCKED_NETWORKS:
            if ip in network:
                return False
        return True
    except (socket.gaierror, ValueError, IndexError):
        return False

def is_loopback_url(url: str) -> bool:
    """Check if a URL points to the loopback address."""
    try:
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False
        ip = ipaddress.ip_address(socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)[0][4][0])
        return ip.is_loopback
    except (socket.gaierror, ValueError, IndexError):
        return False

class HLSProxyServer(ThreadingHTTPServer):
    def __init__(self, server_address, RequestHandlerClass, stream: StreamInfo, session, allow_private: bool = False):
        self.stream = stream
        self.session = session
        self.allow_private = allow_private
        super().__init__(server_address, RequestHandlerClass)

class HLSProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Only log non-200s and playlists
        if len(args) > 1 and args[1] != "200":
            print(f"[proxy] {self.path}  →  {args[1]}")
        elif "m3u8" in self.path or "playlist" in self.path:
            print(f"[proxy] {self.path[:60]}...  →  200 (playlist)")
    
    def do_GET(self):
        try:
            delegate = getattr(self.server.stream, "proxy_delegate", None)
            if delegate is None:
                from hlsproxy.core.proxy_delegate import DefaultProxyDelegate
                delegate = DefaultProxyDelegate
                self.server.stream.proxy_delegate = delegate
                
            delegate_instance = delegate()

            if self.path == "/playlist.m3u8":
                delegate_instance.handle_playlist(self, self.server.stream.m3u8_url)
            elif self.path.startswith("/req"):
                parsed = urllib.parse.urlparse(self.path)
                qs = urllib.parse.parse_qs(parsed.query)
                upstream_url = qs.get("url", [""])[0]
                req_type = qs.get("type", ["seg"])[0]
                
                if not upstream_url:
                    self.send_response(400)
                    self.end_headers()
                    return
                
                # SSRF protection: block private/internal IPs unless explicitly allowed
                if not self.server.allow_private:
                    # Allow loopback URLs (proxy talking to itself is fine)
                    if not is_loopback_url(upstream_url) and not is_safe_url(upstream_url):
                        print(f"[!] Blocked request to private/internal address: {upstream_url[:80]}")
                        self.send_response(403)
                        self.end_headers()
                        return
                    
                if req_type == "m3u8":
                    delegate_instance.handle_playlist(self, upstream_url)
                else:
                    delegate_instance.handle_segment(self, upstream_url, req_type=req_type)
            else:
                self.send_response(404)
                self.end_headers()
        except ConnectionError:
            pass
            

def start_proxy(stream: StreamInfo, host: str = "0.0.0.0", port: int = 18888, allow_private: bool = False) -> ThreadingHTTPServer:
    """Start the proxy server in a background thread."""
    session = create_session(stream)
    server = HLSProxyServer((host, port), HLSProxyHandler, stream, session, allow_private=allow_private)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server
