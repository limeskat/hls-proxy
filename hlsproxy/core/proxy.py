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
                self.fetch_and_stream(upstream_url, req_type=req_type)
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
        start_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("#EXTM3U"):
                start_idx = i
                break
                
        if start_idx == -1:
            print(f"[!] Invalid playlist: No #EXTM3U found in {url}")
            self.send_response(502)
            self.end_headers()
            return
            
        lines = lines[start_idx:]
        
        host_header = self.headers.get("Host", f"127.0.0.1:{self.server.server_address[1]}")
        proxy_host = f"http://{host_header}"
        
        def make_proxy_url(absolute_uri, is_m3u8=False):
            encoded_uri = urllib.parse.quote(absolute_uri, safe="")
            if is_m3u8:
                return f"{proxy_host}/req.m3u8?type=m3u8&url={encoded_uri}&ext=.m3u8"
            else:
                return f"{proxy_host}/req.ts?type=seg&url={encoded_uri}&ext=.ts"

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

    def fetch_and_stream(self, upstream_url, req_type="seg"):
        session = self.server.session
        headers = {}
        # We explicitly DO NOT forward the Range header for segments to avoid offset corruption.
        # But for subtitles, it's fine.
        if req_type == "sub" and "Range" in self.headers:
            headers["Range"] = self.headers["Range"]
            
        try:
            r = session.get(upstream_url, stream=True, timeout=15, headers=headers)
            r.raise_for_status()
            
            # If it's a subtitle, just stream it directly
            if req_type == "sub":
                self.send_response(r.status_code)
                self.send_header("Content-Type", "text/vtt")
                if "Content-Length" in r.headers:
                    self.send_header("Content-Length", r.headers["Content-Length"])
                if "Content-Range" in r.headers:
                    self.send_header("Content-Range", r.headers["Content-Range"])
                if "Accept-Ranges" in r.headers:
                    self.send_header("Accept-Ranges", r.headers["Accept-Ranges"])
                self.end_headers()
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        self.wfile.write(chunk)
                return
                
            # For segments, buffer first to find TS start
            buffer = bytearray()
            header_stripped = False
            content_length = r.headers.get("Content-Length")
            
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    if not header_stripped:
                        buffer.extend(chunk)
                        if len(buffer) < 2000:
                            continue
                            
                        ts_start = 0
                        for i in range(len(buffer) - 188*3):
                            if buffer[i] == 0x47 and buffer[i+188] == 0x47 and buffer[i+188*2] == 0x47:
                                ts_start = i
                                break
                        
                        # Now send the HTTP headers with the corrected Content-Length
                        self.send_response(r.status_code)
                        self.send_header("Content-Type", "video/MP2T")
                        if content_length and content_length.isdigit():
                            self.send_header("Content-Length", str(int(content_length) - ts_start))
                        self.end_headers()
                        
                        if ts_start > 0:
                            chunk_to_write = bytes(buffer[ts_start:])
                        else:
                            chunk_to_write = bytes(buffer)
                            
                        self.wfile.write(chunk_to_write)
                        header_stripped = True
                        buffer = None
                    else:
                        self.wfile.write(chunk)
            
            if not header_stripped and buffer:
                self.send_response(r.status_code)
                self.send_header("Content-Type", "video/MP2T")
                if content_length and content_length.isdigit():
                    self.send_header("Content-Length", content_length)
                self.end_headers()
                self.wfile.write(bytes(buffer))
                
        except Exception as e:
            err_str = str(e)
            if "Broken pipe" not in err_str and "Connection reset" not in err_str:
                print(f"[!] {req_type} fetch failed: {e}")

def start_proxy(stream: StreamInfo, host: str = "0.0.0.0", port: int = 18888) -> ThreadingHTTPServer:
    """Start the proxy server in a background thread."""
    session = create_session(stream)
    server = HLSProxyServer((host, port), HLSProxyHandler, stream, session)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server
