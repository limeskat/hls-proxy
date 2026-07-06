import re
import urllib.parse
from abc import ABC

class BaseProxyDelegate(ABC):
    """
    Base class for custom proxy logic. Resolvers can subclass this
    and attach it to StreamInfo.proxy_delegate to customize how
    playlists and segments are fetched and rewritten.
    """
    def handle_playlist(self, handler, url):
        raise NotImplementedError

    def handle_segment(self, handler, url, req_type="seg"):
        raise NotImplementedError

class DefaultProxyDelegate(BaseProxyDelegate):
    """
    The default proxy implementation with robust TS start stripping
    and strict Range header handling.
    """
    def handle_playlist(self, handler, url):
        session = handler.server.session
        try:
            r = session.get(url, timeout=10)
            r.raise_for_status()
            text = r.text
        except Exception as e:
            print(f"[!] Playlist fetch failed for {url}: {e}")
            handler.send_response(502)
            handler.end_headers()
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
            handler.send_response(502)
            handler.end_headers()
            return

        lines = lines[start_idx:]

        host_header = handler.headers.get("Host", f"127.0.0.1:{handler.server.server_address[1]}")
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

        handler.send_response(200)
        handler.send_header("Content-Type", "application/vnd.apple.mpegurl")
        handler.send_header("Content-Length", str(len(body)))
        handler.send_header("Cache-Control", "no-cache, no-store")
        handler.end_headers()
        handler.wfile.write(body)

    def handle_segment(self, handler, upstream_url, req_type="seg"):
        session = handler.server.session
        headers = {}
        # We explicitly DO NOT forward the Range header for segments to avoid offset corruption.
        # But for subtitles, it's fine.
        if req_type == "sub" and "Range" in handler.headers:
            headers["Range"] = handler.headers["Range"]
            
        # Force identity encoding to prevent chunked dynamic gzipping of TS files which breaks slow reads
        headers["Accept-Encoding"] = "identity"
            
        max_retries = 3
        import time
        for attempt in range(max_retries):
            r = None
            headers_sent = False
            try:
                r = session.get(upstream_url, stream=True, timeout=120, headers=headers)
                
                if r.status_code == 404 and attempt < max_retries - 1:
                    if hasattr(r, 'close'):
                        try: r.close()
                        except: pass
                    time.sleep(1.0)
                    continue
                    
                r.raise_for_status()
                
                upstream_ct = r.headers.get("Content-Type", "video/MP2T")
                
                # If it's a subtitle, just stream it directly
                if req_type == "sub":
                    handler.send_response(r.status_code)
                    handler.send_header("Content-Type", upstream_ct)
                    if "Content-Length" in r.headers:
                        handler.send_header("Content-Length", r.headers["Content-Length"])
                    if "Content-Range" in r.headers:
                        handler.send_header("Content-Range", r.headers["Content-Range"])
                    if "Accept-Ranges" in r.headers:
                        handler.send_header("Accept-Ranges", r.headers["Accept-Ranges"])
                    handler.end_headers()
                    headers_sent = True
                    for chunk in r.iter_content(chunk_size=handler.server.stream.chunk_size):
                        if chunk:
                            handler.wfile.write(chunk)
                    return
                    
                # For segments, buffer first to find TS start
                buffer = bytearray()
                header_stripped = False
                content_length = r.headers.get("Content-Length")
                is_compressed = "Content-Encoding" in r.headers
                
                for chunk in r.iter_content(chunk_size=handler.server.stream.chunk_size):
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
                            
                            # Now send the HTTP headers
                            handler.send_response(r.status_code)
                            handler.send_header("Content-Type", upstream_ct)
                            if content_length and content_length.isdigit() and not is_compressed:
                                handler.send_header("Content-Length", str(int(content_length) - ts_start))
                            handler.end_headers()
                            headers_sent = True
                            
                            if ts_start > 0:
                                chunk_to_write = bytes(buffer[ts_start:])
                            else:
                                chunk_to_write = bytes(buffer)
                                
                            handler.wfile.write(chunk_to_write)
                            header_stripped = True
                            buffer = None
                        else:
                            handler.wfile.write(chunk)
                
                if not header_stripped and buffer:
                    handler.send_response(r.status_code)
                    handler.send_header("Content-Type", upstream_ct)
                    if content_length and content_length.isdigit() and not is_compressed:
                        handler.send_header("Content-Length", content_length)
                    handler.end_headers()
                    headers_sent = True
                    handler.wfile.write(bytes(buffer))
                    
                break
            except Exception as e:
                if r and hasattr(r, 'close'):
                    try: r.close()
                    except: pass
                
                err_str = str(e)
                if "Broken pipe" in err_str or "Connection reset" in err_str:
                    break
                    
                if not headers_sent and attempt < max_retries - 1:
                    time.sleep(1.0)
                    continue
                    
                if not headers_sent:
                    print(f"[!] {req_type} fetch failed: {e}")
                    handler.send_response(502)
                    handler.end_headers()
                break
