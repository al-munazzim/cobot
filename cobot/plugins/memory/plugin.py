"""Memory plugin - defines extension points for memory storage.

This plugin defines the memory extension points that different
storage backends can implement (files, vector DB, etc.)

It also provides a "super tool" that aggregates results from
all implementations.

Priority: 12 (after workspace, before implementations)
"""

import sys
from typing import Optional

from ..base import Plugin, PluginMeta


class MemoryPlugin(Plugin):
    """Memory extension point definer and aggregator."""

    meta = PluginMeta(
        id="memory",
        version="1.0.0",
        dependencies=["workspace"],
        extension_points=[
            "memory.store",     # Store a memory: store(key, content) -> None
            "memory.retrieve",  # Retrieve by key: retrieve(key) -> str
            "memory.search",    # Search memories: search(query) -> list[dict]
        ],
        priority=12,
    )

    def __init__(self):
        self._registry = None

    def configure(self, config: dict) -> None:
        """Store configuration."""
        self._config = config

    def start(self) -> None:
        """Initialize memory aggregator."""
        print("[Memory] Ready (extension point definer)", file=sys.stderr)

    def stop(self) -> None:
        """Nothing to clean up."""
        pass

    def store(self, key: str, content: str) -> None:
        """Store content using all implementations.
        
        Calls all plugins that implement memory.store.
        
        Args:
            key: Identifier for the memory
            content: Content to store
        """
        if not self._registry:
            return
        
        for plugin_id, plugin, method_name in self._registry.get_implementations("memory.store"):
            try:
                method = getattr(plugin, method_name)
                method(key, content)
            except Exception as e:
                print(f"[Memory] Error storing via {plugin_id}: {e}", file=sys.stderr)

    def retrieve(self, key: str) -> Optional[str]:
        """Retrieve content from first implementation that has it.
        
        Args:
            key: Identifier for the memory
            
        Returns:
            Content or None if not found
        """
        if not self._registry:
            return None
        
        for plugin_id, plugin, method_name in self._registry.get_implementations("memory.retrieve"):
            try:
                method = getattr(plugin, method_name)
                result = method(key)
                if result:
                    return result
            except Exception as e:
                print(f"[Memory] Error retrieving via {plugin_id}: {e}", file=sys.stderr)
        
        return None

    def search(self, query: str) -> list[dict]:
        """Search across all memory implementations.
        
        Aggregates results from all plugins that implement memory.search.
        
        Args:
            query: Search query
            
        Returns:
            List of results: [{"source": "plugin-id", "key": "...", "content": "...", "score": 0.9}]
        """
        results = []
        
        if not self._registry:
            return results
        
        for plugin_id, plugin, method_name in self._registry.get_implementations("memory.search"):
            try:
                method = getattr(plugin, method_name)
                impl_results = method(query)
                for r in impl_results:
                    r["source"] = plugin_id
                results.extend(impl_results)
            except Exception as e:
                print(f"[Memory] Error searching via {plugin_id}: {e}", file=sys.stderr)
        
        # Sort by score if available
        results.sort(key=lambda r: r.get("score", 0), reverse=True)
        return results


def create_plugin() -> MemoryPlugin:
    """Factory function for plugin discovery."""
    return MemoryPlugin()
