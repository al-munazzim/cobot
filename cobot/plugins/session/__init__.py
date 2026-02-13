"""Session plugin - channel communication orchestrator.

This plugin defines extension points for channel plugins to implement,
providing a unified interface for multi-channel messaging.

See README.md for full documentation.
"""

from .plugin import IncomingMessage, OutgoingMessage, SessionPlugin, create_plugin

__all__ = ["SessionPlugin", "IncomingMessage", "OutgoingMessage", "create_plugin"]
