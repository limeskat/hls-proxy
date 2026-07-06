import re
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from hlsproxy.models import StreamInfo
from hlsproxy.core.session import create_session

class HLSProxyServer(ThreadingHTTPServer):
    def __init__(self, server_address, RequestHandlerClass, stream: StreamInfo, session):
        self.stream = stream
        self.session = session
        super().__init__(server_address, RequestHandlerClass)

class HLSProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Only log non-200s and playlists
        if len(args) > 1 and args[1] != "200":
            print(f"[proxy] {self.path}  →  {args[1]}")
        elif "m3u8" in self.path or "playlist" in self.path:
            print(f"[proxy] {self.path[:60]}...  →  200 (playlist)")
    
    def do_GET(self):
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
                
            if req_type == "m3u8":
                delegate_instance.handle_playlist(self, upstream_url)
            else:
                delegate_instance.handle_segment(self, upstream_url, req_type=req_type)
        else:
            self.send_response(404)
            self.end_headers()
            

def start_proxy(stream: StreamInfo, host: str = "0.0.0.0", port: int = 18888) -> ThreadingHTTPServer:
    """Start the proxy server in a background thread."""
    session = create_session(stream)
    server = HLSProxyServer((host, port), HLSProxyHandler, stream, session)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server
