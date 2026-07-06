from typing import List, Optional
import urllib.parse

from hlsproxy.resolvers.base import BaseResolver, ResolverError
from hlsproxy.models import StreamInfo, ResolverResult

class JWPlayerResolver(BaseResolver):
    """
    A generic resolver for sites that use JWPlayer and a backend API 
    (like getSources or getSourcesNew) to fetch stream URLs.
    """
    domains: List[str] = []
    
    # Whether to strictly set the Origin and Referer to the base domain
    strict_domain_headers: bool = True
    
    # The API endpoint name to intercept
    api_endpoint: str = "getsources"
    
    _is_abstract: bool = True

    def resolve(self, url: str, **kwargs) -> ResolverResult:
        """
        Uses Playwright to intercept the m3u8 and subtitles on page load.
        """
        referer = kwargs.get("referer")
        stream_url = None
        captured_headers = {}
        subtitles = []
        
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # Launch in headless mode
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--autoplay-policy=no-user-gesture-required",
                    "--disable-blink-features=AutomationControlled"
                ]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 720}
            )
            
            page = context.new_page()
            
            from playwright_stealth import Stealth
            Stealth().apply_stealth_sync(page)
            
            def on_route(route, request):
                nonlocal stream_url, captured_headers, subtitles
                url_lower = request.url.lower()
                
                if "devtools-detector" in url_lower:
                    route.abort()
                    return
                
                # Check for direct video playlist request
                if ".m3u8" in url_lower or ".mp4" in url_lower:
                    if not stream_url:
                        stream_url = request.url
                        captured_headers = request.headers
                
                # Check for JWPlayer API response
                if self.api_endpoint in url_lower:
                    try:
                        response = route.fetch()
                        data = response.json()
                        if "sources" in data:
                            if isinstance(data["sources"], dict) and "file" in data["sources"]:
                                stream_url = data["sources"]["file"]
                                captured_headers = request.headers
                            elif isinstance(data["sources"], list) and len(data["sources"]) > 0 and "file" in data["sources"][0]:
                                stream_url = data["sources"][0]["file"]
                                captured_headers = request.headers
                                
                        if "tracks" in data and isinstance(data["tracks"], list):
                            for track in data["tracks"]:
                                if track.get("kind") == "captions" and track.get("file"):
                                    subtitles.append({
                                        "url": track.get("file"),
                                        "lang": track.get("label", "Unknown")
                                    })
                                    
                        route.fulfill(response=response)
                        return
                    except Exception:
                        pass
                        
                route.continue_()
            
            page.route("**/*", on_route)
            
            try:
                # Load the page and wait for the network to idle
                kwargs_goto = {"wait_until": "domcontentloaded", "timeout": 15000}
                if referer:
                    kwargs_goto["referer"] = referer
                page.goto(url, **kwargs_goto)
                
            except Exception as e:
                pass
                
            # Wait a bit more in case on_route catches it late
            if not stream_url:
                page.wait_for_timeout(5000)
                if not stream_url:
                    page.mouse.click(640, 360)
                    for _ in range(20):
                        if stream_url:
                            break
                        page.wait_for_timeout(500)
                        
            browser.close()
            
        if not stream_url:
            raise ResolverError("Could not intercept stream URL via Playwright. The page might have failed to load or the video requires manual interaction.")
            
        parsed = urllib.parse.urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Clean up headers to pass along to hlsproxy
        headers = {}
        if "user-agent" in captured_headers:
            headers["User-Agent"] = captured_headers["user-agent"]
            
        if self.strict_domain_headers:
            # Some CDNs (like nekostream) strictly require exactly base_url + "/" as referer
            headers["Origin"] = base_url
            headers["Referer"] = base_url + "/"
        else:
            if "referer" in captured_headers:
                headers["Referer"] = captured_headers["referer"]
            else:
                headers["Referer"] = url
            if "origin" in captured_headers:
                headers["Origin"] = captured_headers["origin"]
            else:
                headers["Origin"] = base_url
            
        return ResolverResult(
            stream=StreamInfo(
                m3u8_url=stream_url,
                headers=headers,
                impersonate="chrome124",
                subtitles=subtitles
            ),
            title=f"JWPlayer Stream ({parsed.netloc})"
        )
