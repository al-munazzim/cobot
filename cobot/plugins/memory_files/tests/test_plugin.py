"""Tests for memory-files plugin (file-based implementation)."""

import tempfile
from pathlib import Path


from .. import create_plugin


class TestMemoryFilesPlugin:
    """Tests for the memory-files plugin (file-based implementation)."""

    def test_memory_files_stores_in_workspace(self):
        """Memory-files should store in workspace/memory/files/."""
        plugin = create_plugin()

        with tempfile.TemporaryDirectory() as tmpdir:
            files_dir = Path(tmpdir) / "memory" / "files"
            files_dir.mkdir(parents=True)

            plugin.configure({"_workspace_path": tmpdir})
            plugin.start()

            plugin.store("test_key", "Hello world")

            assert (files_dir / "test_key.md").exists()
            assert (files_dir / "test_key.md").read_text() == "Hello world"

    def test_memory_files_retrieves(self):
        """Memory-files should retrieve stored content."""
        plugin = create_plugin()

        with tempfile.TemporaryDirectory() as tmpdir:
            files_dir = Path(tmpdir) / "memory" / "files"
            files_dir.mkdir(parents=True)
            (files_dir / "test.md").write_text("Previous content")

            plugin.configure({"_workspace_path": tmpdir})
            plugin.start()

            content = plugin.retrieve("test")
            assert content == "Previous content"

    def test_memory_files_search(self):
        """Memory-files should search file contents."""
        plugin = create_plugin()

        with tempfile.TemporaryDirectory() as tmpdir:
            files_dir = Path(tmpdir) / "memory" / "files"
            files_dir.mkdir(parents=True)
            (files_dir / "note1.md").write_text("Meeting about project Alpha")
            (files_dir / "note2.md").write_text("Lunch plans for Tuesday")

            plugin.configure({"_workspace_path": tmpdir})
            plugin.start()

            results = plugin.search("Alpha")
            assert len(results) == 1
            assert "Alpha" in results[0]["content"]

    def test_memory_files_implements_extension_points(self):
        """Memory-files should implement memory extension points."""
        plugin = create_plugin()

        assert "memory.store" in plugin.meta.implements
        assert "memory.retrieve" in plugin.meta.implements
        assert "memory.search" in plugin.meta.implements
