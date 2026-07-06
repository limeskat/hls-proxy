import sys
import argparse
import socket
import urllib.parse
from hlsproxy.resolvers import find_resolver, discover_resolvers
from hlsproxy.resolvers.base import ResolverError
from hlsproxy.core.proxy import start_proxy
from hlsproxy.core.player import launch_mpv

def get_available_port(host: str, start_port: int) -> int:
    port = start_port
    while port < 65535:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                port += 1
    raise RuntimeError("No available ports found.")

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def main():
    parser = argparse.ArgumentParser(
        prog="hlsproxy",
        description="Play HLS streams from protected sites in mpv.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("url", nargs="?", help="URL of the stream or event page")
    parser.add_argument("--host", default="0.0.0.0", help="Host IP to bind the proxy to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=18888, help="Local proxy port")
    parser.add_argument("--list-resolvers", action="store_true", 
                        help="List available resolvers and exit")
    parser.add_argument("--impersonate", default="chrome124",
                        help="curl_cffi TLS profile (default: chrome124)")
    parser.add_argument("--no-play", action="store_true",
                        help="Don't launch mpv; just print the proxy URL")
    parser.add_argument("--referer", help="Manually override the Referer header")
    parser.add_argument("--origin", help="Manually override the Origin header")
    
    args = parser.parse_args()
    
    if args.list_resolvers:
        print("Available resolvers:")
        for cls in discover_resolvers():
            instance = cls()
            domains = ", ".join(instance.domains) if instance.domains else "(catch-all)"
            print(f"  {cls.__name__:30s}  domains: {domains}")
        return
    
    if not args.url:
        parser.print_help()
        sys.exit(1)
    
    print(f"[*] Resolving: {args.url}")
    try:
        resolver = find_resolver(args.url)
        print(f"[*] Using resolver: {resolver.__class__.__name__}")
        kwargs = {}
        if args.referer:
            kwargs["referer"] = args.referer
        result = resolver.resolve(args.url, **kwargs)
    except ResolverError as e:
        print(f"[!] Resolution failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Unexpected error during resolution: {e}")
        sys.exit(1)
    
    # Override impersonate if user specified
    result.stream.impersonate = args.impersonate
    
    # Apply manual header overrides only if not already captured by the resolver
    if args.referer and "Referer" not in result.stream.headers:
        result.stream.headers["Referer"] = args.referer
    if args.origin and "Origin" not in result.stream.headers:
        result.stream.headers["Origin"] = args.origin
    
    print(f"[+] Stream:  {result.stream.m3u8_url}")
    print(f"[+] Title:   {result.title}")
    
    # Port conflict handling
    port = get_available_port(args.host, args.port)
    if port != args.port:
        print(f"[*] Port {args.port} in use. Using next available port: {port}")
    
    print(f"[*] Starting proxy...")
    server = start_proxy(result.stream, host=args.host, port=port)
    
    local_url = f"http://127.0.0.1:{port}/playlist.m3u8"
    lan_url = f"http://{get_lan_ip()}:{port}/playlist.m3u8"
    
    print(f"\n==================================================")
    print(f"[+] PROXY BOUND TO   : {args.host}:{port}")
    print(f"[+] LOCAL STREAM URL : {local_url}")
    if args.host == "0.0.0.0":
        print(f"[+] LAN STREAM URL   : {lan_url}")
    print(f"==================================================\n")
    
    if args.no_play:
        print(f"[*] Proxy running. Press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
        return
    
    print(f"[*] Launching mpv...\n")
    try:
        extra_args = []
        if result.stream.subtitles:
            for sub in result.stream.subtitles:
                encoded_sub_url = urllib.parse.quote(sub["url"], safe="")
                sub_proxy_url = f"http://127.0.0.1:{port}/req.vtt?type=sub&url={encoded_sub_url}"
                extra_args.append(f"--sub-file={sub_proxy_url}")
                
        launch_mpv(local_url, title=f"{result.title} (Local Port: {port})", extra_args=extra_args)
    except FileNotFoundError as e:
        print(f"[!] Error: {e}")
        print("[!] Please install mpv and ensure it is in your system's $PATH.")
    except KeyboardInterrupt:
        pass
    finally:
        print("\n[*] Shutting down proxy.")
        server.shutdown()
