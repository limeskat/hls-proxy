import re
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from curl_cffi import requests as cffi_requests
from hlsproxy.models import StreamInfo
from hlsproxy.core.session import create_session

class HLSProxyServer(ThreadingHTTPServer):
    def __init__(self, server_address, RequestHandlerClass, stream: StreamInfo, session: cffi_requests.Session):
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
        if self.path == "/playlist.m3u8":
            self.fetch_and_rewrite(self.server.stream.m3u8_url)
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
                self.fetch_and_rewrite(upstream_url)
            else:
                self.fetch_and_stream(upstream_url)
        else:
            self.send_response(404)
            self.end_headers()
            
    def fetch_and_rewrite(self, url):
        session = self.server.session
        try:
            r = session.get(url, timeout=10)
            r.raise_for_status()
            text = r.text
        except Exception as e:
            print(f"[!] Playlist fetch failed for {url}: {e}")
            self.send_response(502)
            self.end_headers()
            return
            
        lines = text.splitlines()
        
        # Clean custom junk before #EXTM3U (like "caxi" or "load")
        start_idx = 0
        for i, line in enumerate(lines):
            if line.strip() == "#EXTM3U":
                start_idx = i
                break
        lines = lines[start_idx:]
        
        host_header = self.headers.get("Host", f"127.0.0.1:{self.server.server_address[1]}")
        proxy_host = f"http://{host_header}"
        
        def make_proxy_url(absolute_uri, is_m3u8=False):
            encoded_uri = urllib.parse.quote(absolute_uri, safe="")
            type_param = "m3u8" if is_m3u8 else "seg"
            return f"{proxy_host}/req?type={type_param}&url={encoded_uri}"

        for i in range(len(lines)):
            stripped = lines[i].strip()
            if not stripped:
                continue
                
            # Rewrite URI="..." in EXT-X-KEY, EXT-X-MAP
            if stripped.startswith("#EXT-X-KEY:") or stripped.startswith("#EXT-X-MAP:"):
                def uri_replacer(match):
                    original_uri = match.group(1)
                    absolute_uri = urllib.parse.urljoin(url, original_uri)
                    return f'URI="{make_proxy_url(absolute_uri, is_m3u8=False)}"'
                lines[i] = re.sub(r'URI="([^"]+)"', uri_replacer, stripped)
                
            # Rewrite URI="..." in EXT-X-MEDIA
            elif stripped.startswith("#EXT-X-MEDIA:"):
                def uri_replacer(match):
                    original_uri = match.group(1)
                    absolute_uri = urllib.parse.urljoin(url, original_uri)
                    return f'URI="{make_proxy_url(absolute_uri, is_m3u8=True)}"'
                lines[i] = re.sub(r'URI="([^"]+)"', uri_replacer, stripped)
                
            # Rewrite segment and sub-playlist URIs (lines not starting with #)
            elif not stripped.startswith("#"):
                absolute_uri = urllib.parse.urljoin(url, stripped)
                # Check if previous line was a stream info tag indicating a variant playlist
                is_m3u8 = False
                if i > 0:
                    prev_line = lines[i-1].strip()
                    if prev_line.startswith("#EXT-X-STREAM-INF") or prev_line.startswith("#EXT-X-I-FRAME-STREAM-INF"):
                        is_m3u8 = True
                
                lines[i] = make_proxy_url(absolute_uri, is_m3u8=is_m3u8)

        body = "\n".join(lines).encode("utf-8")
        
        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.apple.mpegurl")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache, no-store")
        self.end_headers()
        self.wfile.write(body)

    def fetch_and_stream(self, upstream_url):
        session = self.server.session
        headers = {}
        if "Range" in self.headers:
            headers["Range"] = self.headers["Range"]
            
        try:
            r = session.get(upstream_url, stream=True, timeout=15, headers=headers)
            r.raise_for_status()
            
            self.send_response(r.status_code)
            self.send_header("Content-Type", r.headers.get("Content-Type", "video/MP2T"))
            if "Content-Length" in r.headers:
                self.send_header("Content-Length", r.headers["Content-Length"])
            if "Content-Range" in r.headers:
                self.send_header("Content-Range", r.headers["Content-Range"])
            self.end_headers()
            
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    self.wfile.write(chunk)
        except Exception as e:
            # We don't print full URL to avoid spam, just a snippet
            print(f"[!] Segment fetch failed: {e}")

def start_proxy(stream: StreamInfo, host: str = "0.0.0.0", port: int = 18888) -> ThreadingHTTPServer:
    """Start the proxy server in a background thread."""
    session = create_session(stream)
    server = HLSProxyServer((host, port), HLSProxyHandler, stream, session)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server
