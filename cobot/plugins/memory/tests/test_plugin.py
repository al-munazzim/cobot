"""Tests for memory plugin (extension point definer)."""


from .. import create_plugin


class TestMemoryPlugin:
    """Tests for the memory plugin (extension point definer)."""

    def test_memory_defines_extension_points(self):
        """Memory plugin should define memory extension points."""
        plugin = create_plugin()

        assert "memory.store" in plugin.meta.extension_points
        assert "memory.retrieve" in plugin.meta.extension_points
        assert "memory.search" in plugin.meta.extension_points

    def test_memory_search_aggregates_results(self):
        """Memory search should aggregate from all implementations."""
        plugin = create_plugin()

        # Mock registry with implementations
        class MockImpl:
            def search(self, query):
                return [{"source": "test", "content": "found it"}]

        class MockRegistry:
            def get_implementations(self, ext_point):
                if ext_point == "memory.search":
                    return [("memory-files", MockImpl(), "search")]
                return []

        plugin._registry = MockRegistry()
        plugin.configure({})
        plugin.start()

        results = plugin.search("test query")
        assert len(results) == 1
        assert results[0]["content"] == "found it"
