"""Session plugin - orchestrates channel communication.

This plugin defines extension points that channel plugins implement,
providing a unified interface for multi-channel messaging.

Priority: 10 (early - before channels)
"""

import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..base import Plugin, PluginMeta


@dataclass
class IncomingMessage:
    """Normalized message from any channel."""

    id: str  # Unique message ID
    channel_type: str  # "telegram", "discord", etc.
    channel_id: str  # Group/channel/room ID
    sender_id: str  # User ID
    sender_name: str  # Display name
    content: str  # Message text
    timestamp: datetime  # When sent
    reply_to: Optional[str] = None  # ID of message being replied to
    media: list = field(default_factory=list)  # Attachments
    metadata: dict = field(default_factory=dict)  # Channel-specific data


@dataclass
class OutgoingMessage:
    """Message to send to a channel."""

    channel_type: str  # Target channel type
    channel_id: str  # Target channel/group ID
    content: str  # Message text
    reply_to: Optional[str] = None  # Message to reply to
    media: list = field(default_factory=list)  # Attachments
    metadata: dict = field(default_factory=dict)  # Channel-specific options


class SessionPlugin(Plugin):
    """Session orchestrator - routes messages between channels and agent.

    Defines extension points:
    - session.receive: Get new messages (poll or drain queue)
    - session.send: Send a message to channel
    - session.typing: Show typing indicator
    - session.presence: Set online/offline status
    """

    meta = PluginMeta(
        id="session",
        version="1.0.0",
        extension_points=[
            "session.receive",  # () -> list[IncomingMessage]
            "session.send",  # (OutgoingMessage) -> bool
            "session.typing",  # (channel_id: str) -> None
            "session.presence",  # (status: str) -> None
            "session.edit",  # (channel_id, msg_id, content) -> bool
            "session.delete",  # (channel_id, msg_id) -> bool
            "session.react",  # (channel_id, msg_id, emoji) -> bool
        ],
        priority=10,  # Early - before channels
    )

    def __init__(self):
        self._registry = None
        self._config = {}
        self._default_channel = None

    def configure(self, config: dict) -> None:
        """Configure session plugin."""
        self._config = config
        self._default_channel = config.get("default_channel")

    def start(self) -> None:
        """Initialize session orchestrator."""
        print("[Session] Starting session orchestrator", file=sys.stderr)
        self._log_channels()

    def stop(self) -> None:
        """Nothing to clean up."""
        pass

    def _log_channels(self) -> None:
        """Log discovered channels."""
        if not self._registry:
            return

        channels = []
        for plugin_id, plugin, method_name in self._registry.get_implementations(
            "session.receive"
        ):
            channels.append(plugin_id)

        if channels:
            print(f"[Session] Channels: {', '.join(channels)}", file=sys.stderr)
        else:
            print("[Session] No channels registered", file=sys.stderr)

    def poll_all_channels(self) -> list[IncomingMessage]:
        """Poll all channels for new messages.

        Calls session.receive on every channel that implements it.

        Returns:
            List of normalized IncomingMessage objects, sorted by timestamp
        """
        messages = []

        if not self._registry:
            return messages

        for plugin_id, plugin, method_name in self._registry.get_implementations(
            "session.receive"
        ):
            try:
                method = getattr(plugin, method_name)
                channel_messages = method()

                # Ensure channel_type is set
                for msg in channel_messages:
                    if not msg.channel_type:
                        msg.channel_type = plugin_id
                    messages.append(msg)

            except Exception as e:
                print(f"[Session] Error polling {plugin_id}: {e}", file=sys.stderr)

        # Sort by timestamp
        messages.sort(key=lambda m: m.timestamp)
        return messages

    def send(self, message: OutgoingMessage) -> bool:
        """Send message to the appropriate channel.

        Routes to the channel matching message.channel_type.

        Args:
            message: OutgoingMessage with channel_type set

        Returns:
            True if sent successfully
        """
        if not self._registry:
            print("[Session] No registry available", file=sys.stderr)
            return False

        channel_type = message.channel_type

        for plugin_id, plugin, method_name in self._registry.get_implementations(
            "session.send"
        ):
            if plugin_id == channel_type:
                try:
                    method = getattr(plugin, method_name)
                    return method(message)
                except Exception as e:
                    print(
                        f"[Session] Error sending via {plugin_id}: {e}", file=sys.stderr
                    )
                    return False

        print(f"[Session] No channel found for type: {channel_type}", file=sys.stderr)
        return False

    def typing(self, channel_type: str, channel_id: str) -> None:
        """Show typing indicator on a channel.

        Args:
            channel_type: Channel plugin id ("telegram", "discord", etc.)
            channel_id: Channel/group/room ID
        """
        if not self._registry:
            return

        for plugin_id, plugin, method_name in self._registry.get_implementations(
            "session.typing"
        ):
            if plugin_id == channel_type:
                try:
                    method = getattr(plugin, method_name)
                    method(channel_id)
                except Exception as e:
                    print(
                        f"[Session] Error typing on {plugin_id}: {e}", file=sys.stderr
                    )
                return

    def presence(self, status: str) -> None:
        """Set presence status on all channels.

        Args:
            status: Status string ("online", "offline", "away", etc.)
        """
        if not self._registry:
            return

        for plugin_id, plugin, method_name in self._registry.get_implementations(
            "session.presence"
        ):
            try:
                method = getattr(plugin, method_name)
                method(status)
            except Exception as e:
                print(
                    f"[Session] Error setting presence on {plugin_id}: {e}",
                    file=sys.stderr,
                )

    def broadcast(self, content: str, exclude_channel: str = None) -> int:
        """Send message to all channels.

        Args:
            content: Message to broadcast
            exclude_channel: Optional channel to skip (avoid echo)

        Returns:
            Number of channels message was sent to
        """
        if not self._registry:
            return 0

        sent = 0
        for plugin_id, plugin, method_name in self._registry.get_implementations(
            "session.send"
        ):
            if plugin_id == exclude_channel:
                continue

            try:
                # Get default channel_id from plugin
                channel_id = None
                if hasattr(plugin, "get_default_channel_id"):
                    channel_id = plugin.get_default_channel_id()

                if not channel_id:
                    continue

                message = OutgoingMessage(
                    channel_type=plugin_id,
                    channel_id=channel_id,
                    content=content,
                )

                method = getattr(plugin, method_name)
                if method(message):
                    sent += 1

            except Exception as e:
                print(
                    f"[Session] Error broadcasting to {plugin_id}: {e}", file=sys.stderr
                )

        return sent

    def get_channels(self) -> list[str]:
        """Get list of registered channel types.

        Returns:
            List of channel plugin IDs
        """
        if not self._registry:
            return []

        return [
            plugin_id
            for plugin_id, _, _ in self._registry.get_implementations("session.receive")
        ]


def create_plugin() -> SessionPlugin:
    """Factory function for plugin discovery."""
    return SessionPlugin()
