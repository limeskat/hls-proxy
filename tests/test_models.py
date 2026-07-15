import pytest
from hlsproxy.models import StreamInfo, ResolverResult


class TestStreamInfo:
    def test_base_url_derived_from_m3u8_url(self):
        stream = StreamInfo(m3u8_url="https://example.com/path/to/playlist.m3u8")
        assert stream.base_url == "https://example.com"

    def test_base_url_with_port(self):
        stream = StreamInfo(m3u8_url="https://example.com:8080/stream.m3u8")
        assert stream.base_url == "https://example.com:8080"

    def test_base_url_with_path(self):
        stream = StreamInfo(m3u8_url="http://cdn.example.com/live/track.m3u8")
        assert stream.base_url == "http://cdn.example.com"

    def test_base_url_not_overridden_if_set(self):
        stream = StreamInfo(m3u8_url="https://example.com/stream.m3u8", base_url="https://custom.com")
        assert stream.base_url == "https://custom.com"

    def test_default_headers_empty(self):
        stream = StreamInfo(m3u8_url="https://example.com/stream.m3u8")
        assert stream.headers == {}

    def test_default_impersonate(self):
        stream = StreamInfo(m3u8_url="https://example.com/stream.m3u8")
        assert stream.impersonate == "chrome124"

    def test_default_proxy_none(self):
        stream = StreamInfo(m3u8_url="https://example.com/stream.m3u8")
        assert stream.proxy is None

    def test_proxy_set(self):
        stream = StreamInfo(m3u8_url="https://example.com/stream.m3u8", proxy="socks5://127.0.0.1:1080")
        assert stream.proxy == "socks5://127.0.0.1:1080"

    def test_default_chunk_size(self):
        stream = StreamInfo(m3u8_url="https://example.com/stream.m3u8")
        assert stream.chunk_size == 131072

    def test_default_subtitles_empty(self):
        stream = StreamInfo(m3u8_url="https://example.com/stream.m3u8")
        assert stream.subtitles == []

    def test_proxy_delegate_default_none(self):
        stream = StreamInfo(m3u8_url="https://example.com/stream.m3u8")
        assert stream.proxy_delegate is None

    def test_headers_not_shared_between_instances(self):
        s1 = StreamInfo(m3u8_url="https://a.com/s.m3u8")
        s2 = StreamInfo(m3u8_url="https://b.com/s.m3u8")
        s1.headers["Referer"] = "https://a.com"
        assert "Referer" not in s2.headers

    def test_cookies_not_shared_between_instances(self):
        s1 = StreamInfo(m3u8_url="https://a.com/s.m3u8")
        s2 = StreamInfo(m3u8_url="https://b.com/s.m3u8")
        s1.cookies["session"] = "abc"
        assert "session" not in s2.cookies


class TestResolverResult:
    def test_default_title(self):
        result = ResolverResult(stream=StreamInfo(m3u8_url="https://example.com/s.m3u8"))
        assert result.title == "Stream"

    def test_custom_title(self):
        result = ResolverResult(
            stream=StreamInfo(m3u8_url="https://example.com/s.m3u8"),
            title="My Stream",
        )
        assert result.title == "My Stream"

    def test_default_quality_options_empty(self):
        result = ResolverResult(stream=StreamInfo(m3u8_url="https://example.com/s.m3u8"))
        assert result.quality_options == []
