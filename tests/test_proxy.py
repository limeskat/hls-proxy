import pytest
from hlsproxy.core.proxy import is_safe_url, is_loopback_url


class TestIsSafeUrl:
    def test_public_url_is_safe(self):
        assert is_safe_url("https://example.com/stream.m3u8") is True

    def test_public_cdn_is_safe(self):
        assert is_safe_url("https://cloudflare.com/cdn/live/track.m3u8") is True

    def test_blocks_10_x(self):
        assert is_safe_url("http://10.0.0.1/metadata") is False

    def test_blocks_172_16_x(self):
        assert is_safe_url("http://172.16.0.1/metadata") is False

    def test_blocks_192_168_x(self):
        assert is_safe_url("http://192.168.1.1/admin") is False

    def test_blocks_127_x(self):
        assert is_safe_url("http://127.0.0.1:8080/internal") is False

    def test_blocks_link_local(self):
        assert is_safe_url("http://169.254.169.254/latest/meta-data/") is False

    def test_blocks_localhost_resolved(self):
        assert is_safe_url("http://localhost:8080/secret") is False

    def test_blocks_ipv6_loopback(self):
        assert is_safe_url("http://[::1]/secret") is False

    def test_unresolvable_hostname(self):
        assert is_safe_url("http://this-host-does-not-exist-xyz123.invalid/stream") is False

    def test_empty_url(self):
        assert is_safe_url("") is False

    def test_no_hostname(self):
        assert is_safe_url("file:///etc/passwd") is False


class TestIsLoopbackUrl:
    def test_127_0_0_1_is_loopback(self):
        assert is_loopback_url("http://127.0.0.1:18888/playlist.m3u8") is True

    def test_localhost_is_loopback(self):
        assert is_loopback_url("http://localhost:18888/playlist.m3u8") is True

    def test_public_url_not_loopback(self):
        assert is_loopback_url("https://example.com/stream.m3u8") is False

    def test_empty_url(self):
        assert is_loopback_url("") is False
