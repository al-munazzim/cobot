"""Tests for context plugin."""

from .. import create_plugin


class TestContextPlugin:
    """Tests for the context plugin."""

    def test_context_defines_extension_points(self):
        """Context plugin should define extension points."""
        plugin = create_plugin()

        assert "context.system_prompt" in plugin.meta.extension_points
        assert "context.history" in plugin.meta.extension_points

    def test_context_collects_system_prompts(self):
        """Context should collect from all system_prompt implementers."""
        plugin = create_plugin()

        # Mock registry with implementers
        class MockImplementer:
            def get_prompt(self):
                return "I am helpful."

        class MockRegistry:
            def get_implementations(self, ext_point):
                if ext_point == "context.system_prompt":
                    return [("soul", MockImplementer(), "get_prompt")]
                return []

        plugin._registry = MockRegistry()
        plugin.configure({})
        plugin.start()

        prompt = plugin.build_system_prompt()
        assert "I am helpful." in prompt
