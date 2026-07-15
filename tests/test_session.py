import pytest
from unittest.mock import patch, MagicMock
from hlsproxy.models import StreamInfo
from hlsproxy.core.session import create_session


class TestCreateSession:
    def test_creates_session_with_headers(self):
        stream = StreamInfo(
            m3u8_url="https://example.com/stream.m3u8",
            headers={"Referer": "https://example.com/"},
        )
        session = create_session(stream)
        # The session should have the custom headers
        assert "Referer" in session.headers
        assert session.headers["Referer"] == "https://example.com/"

    def test_creates_session_with_cookies(self):
        stream = StreamInfo(
            m3u8_url="https://example.com/stream.m3u8",
            cookies={"session": "abc123"},
        )
        session = create_session(stream)
        assert session.cookies.get("session") == "abc123"

    def test_creates_session_with_proxy(self):
        stream = StreamInfo(
            m3u8_url="https://example.com/stream.m3u8",
            proxy="socks5://127.0.0.1:1080",
        )
        session = create_session(stream)
        assert session.proxies.get("https") == "socks5://127.0.0.1:1080"
        assert session.proxies.get("http") == "socks5://127.0.0.1:1080"

    def test_creates_session_without_proxy(self):
        stream = StreamInfo(m3u8_url="https://example.com/stream.m3u8")
        session = create_session(stream)
        # Should not have proxy set (or have empty/default proxies)
        assert session.proxies == {} or session.proxies is None or "https" not in session.proxies

    def test_session_has_get_and_headers(self):
        stream = StreamInfo(m3u8_url="https://example.com/stream.m3u8")
        session = create_session(stream)
        # Should be a curl_cffi Session
        assert hasattr(session, 'get')
        assert hasattr(session, 'headers')
