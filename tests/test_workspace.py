"""Tests for workspace plugin and related context plugins."""

import os
import tempfile
from pathlib import Path

import pytest


class TestWorkspacePlugin:
    """Tests for the workspace plugin."""

    def test_workspace_provides_paths(self):
        """Workspace plugin should provide path accessors."""
        from cobot.plugins.workspace import create_plugin

        plugin = create_plugin()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin.configure({"workspace": tmpdir})
            plugin.start()
            
            # Should provide workspace root
            assert plugin.get_path() == Path(tmpdir)
            
            # Should provide subdirectory paths
            assert plugin.get_path("memory") == Path(tmpdir) / "memory"
            assert plugin.get_path("skills") == Path(tmpdir) / "skills"

    def test_workspace_creates_dirs_on_start(self):
        """Workspace should create subdirectories if missing."""
        from cobot.plugins.workspace import create_plugin

        plugin = create_plugin()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_dir = Path(tmpdir) / "workspace"
            plugin.configure({"workspace": str(workspace_dir)})
            plugin.start()
            
            # Should create workspace and subdirs
            assert workspace_dir.exists()
            assert (workspace_dir / "memory").exists()
            assert (workspace_dir / "skills").exists()
            assert (workspace_dir / "plugins").exists()
            assert (workspace_dir / "logs").exists()

    def test_workspace_priority_cli_over_env(self):
        """CLI arg should win over env var."""
        from cobot.plugins.workspace import create_plugin

        plugin = create_plugin()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cli_path = Path(tmpdir) / "cli"
            env_path = Path(tmpdir) / "env"
            
            os.environ["COBOT_WORKSPACE"] = str(env_path)
            try:
                # _resolved_workspace simulates CLI resolution
                plugin.configure({
                    "workspace": str(env_path),
                    "_cli_workspace": str(cli_path),
                })
                plugin.start()
                
                assert plugin.get_path() == cli_path
            finally:
                del os.environ["COBOT_WORKSPACE"]

    def test_workspace_priority_env_over_config(self):
        """Env var should win over config."""
        from cobot.plugins.workspace import create_plugin

        plugin = create_plugin()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / "env"
            config_path = Path(tmpdir) / "config"
            
            os.environ["COBOT_WORKSPACE"] = str(env_path)
            try:
                plugin.configure({"workspace": str(config_path)})
                plugin.start()
                
                assert plugin.get_path() == env_path
            finally:
                del os.environ["COBOT_WORKSPACE"]

    def test_workspace_default_location(self):
        """Should default to ~/.cobot/workspace."""
        from cobot.plugins.workspace import create_plugin

        plugin = create_plugin()
        plugin.configure({})
        
        expected = Path.home() / ".cobot" / "workspace"
        assert plugin.get_path() == expected


class TestSoulPlugin:
    """Tests for the soul plugin."""

    def test_soul_reads_soul_md(self):
        """Soul plugin should read SOUL.md from workspace."""
        from cobot.plugins.soul import create_plugin

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
        from cobot.plugins.soul import create_plugin

        plugin = create_plugin()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin.configure({"_workspace_path": tmpdir})
            plugin.start()
            
            assert plugin.get_soul() == ""

    def test_soul_implements_context_extension_point(self):
        """Soul plugin should implement context.system_prompt."""
        from cobot.plugins.soul import create_plugin

        plugin = create_plugin()
        
        assert "context.system_prompt" in plugin.meta.implements


class TestContextPlugin:
    """Tests for the context plugin."""

    def test_context_defines_extension_points(self):
        """Context plugin should define extension points."""
        from cobot.plugins.context import create_plugin

        plugin = create_plugin()
        
        assert "context.system_prompt" in plugin.meta.extension_points
        assert "context.history" in plugin.meta.extension_points

    def test_context_collects_system_prompts(self):
        """Context should collect from all system_prompt implementers."""
        from cobot.plugins.context import create_plugin

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


class TestMemoryPlugin:
    """Tests for the memory plugin."""

    def test_memory_stores_in_workspace(self):
        """Memory should store files in workspace/memory/."""
        from cobot.plugins.memory import create_plugin

        plugin = create_plugin()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_dir = Path(tmpdir) / "memory"
            memory_dir.mkdir()
            
            plugin.configure({"_workspace_path": tmpdir})
            plugin.start()
            
            # Store a memory
            plugin.store("test_conversation", "Hello world")
            
            # Check file was created
            assert (memory_dir / "test_conversation.md").exists()

    def test_memory_retrieves_from_workspace(self):
        """Memory should retrieve files from workspace/memory/."""
        from cobot.plugins.memory import create_plugin

        plugin = create_plugin()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_dir = Path(tmpdir) / "memory"
            memory_dir.mkdir()
            
            # Create a memory file
            (memory_dir / "test.md").write_text("Previous conversation")
            
            plugin.configure({"_workspace_path": tmpdir})
            plugin.start()
            
            content = plugin.retrieve("test")
            assert content == "Previous conversation"

    def test_memory_implements_context_extension_point(self):
        """Memory plugin should implement context.history."""
        from cobot.plugins.memory import create_plugin

        plugin = create_plugin()
        
        assert "context.history" in plugin.meta.implements
