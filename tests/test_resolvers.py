import pytest
from unittest.mock import patch, MagicMock
from hlsproxy.resolvers.base import BaseResolver, ResolverError
from hlsproxy.resolvers.generic import GenericResolver
from hlsproxy.resolvers import discover_resolvers, find_resolver
from hlsproxy.models import StreamInfo, ResolverResult


class TestBaseResolver:
    def test_can_handle_with_matching_domain(self):
        class TestResolver(BaseResolver):
            domains = ["example.com"]
            def resolve(self, url, **kwargs):
                pass

        r = TestResolver()
        assert r.can_handle("https://example.com/video") is True

    def test_can_handle_with_non_matching_domain(self):
        class TestResolver(BaseResolver):
            domains = ["example.com"]
            def resolve(self, url, **kwargs):
                pass

        r = TestResolver()
        assert r.can_handle("https://other.com/video") is False

    def test_can_handle_case_insensitive(self):
        class TestResolver(BaseResolver):
            domains = ["example.com"]
            def resolve(self, url, **kwargs):
                pass

        r = TestResolver()
        assert r.can_handle("https://EXAMPLE.COM/video") is True

    def test_catch_all(self):
        class CatchAll(BaseResolver):
            catch_all = True
            def resolve(self, url, **kwargs):
                pass

        r = CatchAll()
        assert r.can_handle("https://anything-goes.com/video") is True

    def test_default_priority(self):
        class TestResolver(BaseResolver):
            def resolve(self, url, **kwargs):
                pass

        assert TestResolver.priority == 100

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseResolver()


class TestGenericResolver:
    def test_catch_all_is_true(self):
        assert GenericResolver.catch_all is True

    def test_priority_is_999(self):
        assert GenericResolver.priority == 999

    def test_resolve_returns_stream_info(self):
        r = GenericResolver()
        result = r.resolve("https://example.com/stream.m3u8")
        assert isinstance(result, ResolverResult)
        assert result.stream.m3u8_url == "https://example.com/stream.m3u8"
        assert result.title == "Direct Stream"

    def test_resolve_any_url(self):
        r = GenericResolver()
        result = r.resolve("https://anything.com/playlist/123")
        assert result.stream.m3u8_url == "https://anything.com/playlist/123"


class TestDiscoverResolvers:
    def test_discovers_generic(self):
        resolvers = discover_resolvers()
        names = [r.__name__ for r in resolvers]
        assert "GenericResolver" in names

    def test_generic_is_last(self):
        resolvers = discover_resolvers()
        assert resolvers[-1].__name__ == "GenericResolver"

    def test_excludes_base(self):
        resolvers = discover_resolvers()
        names = [r.__name__ for r in resolvers]
        assert "BaseResolver" not in names


class TestFindResolver:
    def test_finds_generic_for_unknown_url(self):
        r = find_resolver("https://unknown-site.com/video")
        assert isinstance(r, GenericResolver)

    def test_raises_on_empty_discovery(self):
        with patch("hlsproxy.resolvers.discover_resolvers", return_value=[]):
            with pytest.raises(ResolverError, match="No resolver found"):
                find_resolver("https://example.com/video")
