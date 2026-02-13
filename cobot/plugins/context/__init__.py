"""Context plugin - defines extension points for system prompt building."""

from .plugin import ContextPlugin, create_plugin

__all__ = ["ContextPlugin", "create_plugin"]
