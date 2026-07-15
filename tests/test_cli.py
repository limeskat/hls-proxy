import socket
import pytest
from hlsproxy.cli import get_available_port, get_lan_ip


class TestGetAvailablePort:
    def test_returns_requested_port_when_free(self):
        port = get_available_port("127.0.0.1", 19999)
        assert port == 19999

    def test_skips_occupied_port(self):
        # Occupy a port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 19998))
            s.listen(1)
            port = get_available_port("127.0.0.1", 19998)
            assert port == 19999

    def test_returns_different_host_port(self):
        port = get_available_port("0.0.0.0", 19997)
        assert port == 19997


class TestGetLanIp:
    def test_returns_string(self):
        ip = get_lan_ip()
        assert isinstance(ip, str)

    def test_returns_valid_ip_or_localhost(self):
        ip = get_lan_ip()
        # Should be either a valid IP or the fallback
        assert ip == "127.0.0.1" or "." in ip
