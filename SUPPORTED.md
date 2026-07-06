# Supported Sites

`hlsproxy` dynamically loads resolvers to bypass specific anti-bot and CDN obfuscation protections.

## Supported

### Vidwish / Megaplay
* **Domains**: `vidwish.live`, `megaplay.buzz`
* **Resolver**: `VidwishResolver`
* **Features**: Bypasses `devtools-detector` anti-debugging scripts, forces correct `video/MP2T` headers to bypass `.jpg` file extension obfuscation, and supports `--referer` injection to bypass strict Origin tracking (404/410 errors).

### Vidtube
* **Domains**: `vidtube.site`
* **Resolver**: `VidtubeResolver`
* **Features**: Bypasses Playwright detection, intercepts JSON APIs to extract obfuscated `.m3u8` links, and cleans corrupt junk-byte headers injected into the raw `.ts` segments.

### Gooz
* **Domains**: `gooz.aapmains.net` (and subdomains)
* **Resolver**: `GoozResolver`
* **Features**: Uses `curl_cffi` to impersonate standard Chrome TLS fingerprints to bypass Cloudflare and strict CDN blocks.

## Fallback Support

### Generic HLS
* **Domains**: *(Catch-all)*
* **Resolver**: `GenericResolver`
* **Features**: If a domain is not explicitly supported by a dedicated resolver, `hlsproxy` will fallback to the `GenericResolver`. This resolver assumes the provided URL is a direct `.m3u8` playlist and will attempt to proxy it directly without running Playwright or anti-bot bypasses.

---
*Note: If you encounter 403 Forbidden or 410 Gone errors on supported sites,try using the `--referer` flag to provide the URL of the parent webpage where the video is embedded.*
