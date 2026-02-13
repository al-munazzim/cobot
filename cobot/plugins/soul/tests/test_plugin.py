"""Tests for soul plugin."""

import tempfile
from pathlib import Path


from .. import create_plugin


class TestSoulPlugin:
    """Tests for the soul plugin."""

    def test_soul_reads_soul_md(self):
        """Soul plugin should read SOUL.md from workspace."""
        plugin = create_plugin()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create SOUL.md
            soul_content = "You are a helpful assistant named Bob."
            (Path(tmpdir) / "SOUL.md").write_text(soul_content)

            # Mock workspace path
            plugin.configure({"_workspace_path": tmpdir})
            plugin.start()

            assert plugin.get_soul() == soul_content

    def test_soul_returns_empty_if_no_file(self):
        """Soul plugin should return empty string if SOUL.md missing."""
        plugin = create_plugin()

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin.configure({"_workspace_path": tmpdir})
            plugin.start()

            assert plugin.get_soul() == ""

    def test_soul_implements_context_extension_point(self):
        """Soul plugin should implement context.system_prompt."""
        plugin = create_plugin()

        assert "context.system_prompt" in plugin.meta.implements
