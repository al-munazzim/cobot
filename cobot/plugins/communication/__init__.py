"""Communication plugin - defines extension points for messaging.

This plugin defines the communication extension points that different
implementations can provide (session, direct channels, etc.)
"""

from .plugin import (
    CommunicationPlugin,
    IncomingMessage,
    OutgoingMessage,
    create_plugin,
)

__all__ = ["CommunicationPlugin", "IncomingMessage", "OutgoingMessage", "create_plugin"]
