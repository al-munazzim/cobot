"""Memory plugin - conversation history storage.

Stores and retrieves conversation history from workspace/memory/.
Implements context.history extension point.

Priority: 16 (after workspace, before context)
"""

import sys
from pathlib import Path

from ..base import Plugin, PluginMeta


class MemoryPlugin(Plugin):
    """Memory storage plugin - persists conversations."""

    meta = PluginMeta(
        id="memory",
        version="1.0.0",
        dependencies=["workspace"],
        implements={
            "context.history": "get_history",
        },
        priority=16,
    )

    def __init__(self):
        self._workspace_path: Path = Path(".")
        self._memory_dir: Path = Path(".")
        self._registry = None

    def configure(self, config: dict) -> None:
        """Get workspace path from config."""
        if "_workspace_path" in config:
            self._workspace_path = Path(config["_workspace_path"])
            self._memory_dir = self._workspace_path / "memory"

    def start(self) -> None:
        """Initialize memory directory."""
        # Try to get workspace from registry if available
        if self._registry:
            try:
                workspace = self._registry.get_plugin("workspace")
                if workspace:
                    self._workspace_path = workspace.get_path()
                    self._memory_dir = workspace.get_path("memory")
            except Exception:
                pass
        
        # Ensure memory directory exists
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        print(f"[Memory] {self._memory_dir}", file=sys.stderr)

    def stop(self) -> None:
        """Nothing to clean up."""
        pass

    def store(self, key: str, content: str) -> None:
        """Store content in memory.
        
        Args:
            key: Identifier for the memory (becomes filename)
            content: Content to store
        """
        filepath = self._memory_dir / f"{key}.md"
        filepath.write_text(content)

    def retrieve(self, key: str) -> str:
        """Retrieve content from memory.
        
        Args:
            key: Identifier for the memory
            
        Returns:
            Content or empty string if not found
        """
        filepath = self._memory_dir / f"{key}.md"
        if filepath.exists():
            return filepath.read_text()
        return ""

    def list_memories(self) -> list[str]:
        """List all memory keys.
        
        Returns:
            List of memory keys (filenames without .md)
        """
        return [f.stem for f in self._memory_dir.glob("*.md")]

    def get_history(self) -> list[dict]:
        """Get conversation history for context.
        
        Implements context.history extension point.
        
        Returns:
            List of message dicts from recent memory.
        """
        # For now, return empty - can be expanded to parse memory files
        # and return relevant history
        return []


def create_plugin() -> MemoryPlugin:
    """Factory function for plugin discovery."""
    return MemoryPlugin()
