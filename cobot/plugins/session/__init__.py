"""Session plugin - channel communication orchestrator.

This plugin implements communication.* extension points and defines
session.* extension points for channel plugins to implement.

See README.md for full documentation.
"""

from .plugin import SessionPlugin, create_plugin

# Re-export message types from communication for convenience
from ..communication import IncomingMessage, OutgoingMessage

__all__ = ["SessionPlugin", "IncomingMessage", "OutgoingMessage", "create_plugin"]
