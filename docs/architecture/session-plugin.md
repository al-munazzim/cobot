# Session Plugin Architecture

## Overview

The **session plugin** is the orchestrator for all channel communication. It defines extension points that channel plugins (telegram, discord, slack, nostr) implement.

```
┌─────────────────────────────────────────────────────────────┐
│                        Agent                                │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ process_message() / send_response()
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Session Plugin                           │
│  - Defines: session.receive, session.send, session.typing   │
│  - Routes messages between channels and agent               │
│  - Manages conversation state                               │
└─────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │ Telegram │        │ Discord  │        │  Nostr   │
    │ Plugin   │        │ Plugin   │        │  Plugin  │
    │          │        │          │        │          │
    │implements│        │implements│        │implements│
    │session.* │        │session.* │        │session.* │
    └──────────┘        └──────────┘        └──────────┘
```

## Extension Points

```python
extension_points = [
    "session.receive",      # Poll/webhook for incoming messages
    "session.send",         # Send message to channel
    "session.typing",       # Show typing indicator
    "session.presence",     # Set online/offline status
    "session.edit",         # Edit existing message
    "session.delete",       # Delete message
    "session.react",        # Add reaction
    "session.media",        # Send media (images, files)
]
```

## Data Structures

### Incoming Message (from channel to session)

```python
@dataclass
class IncomingMessage:
    """Normalized message from any channel."""
    id: str                          # Unique message ID
    channel_type: str                # "telegram", "discord", etc.
    channel_id: str                  # Group/channel/room ID
    sender_id: str                   # User ID
    sender_name: str                 # Display name
    content: str                     # Message text
    timestamp: datetime              # When sent
    reply_to: Optional[str] = None   # ID of message being replied to
    media: list[Media] = None        # Attachments
    metadata: dict = None            # Channel-specific data
```

### Outgoing Message (from session to channel)

```python
@dataclass
class OutgoingMessage:
    """Message to send to a channel."""
    channel_type: str                # Target channel type
    channel_id: str                  # Target channel/group ID
    content: str                     # Message text
    reply_to: Optional[str] = None   # Message to reply to
    media: list[Media] = None        # Attachments
    metadata: dict = None            # Channel-specific options
```

## Session Plugin Implementation

```python
"""Session plugin - orchestrates channel communication."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import sys

from ..base import Plugin, PluginMeta


@dataclass
class IncomingMessage:
    id: str
    channel_type: str
    channel_id: str
    sender_id: str
    sender_name: str
    content: str
    timestamp: datetime
    reply_to: Optional[str] = None
    media: list = None
    metadata: dict = None


@dataclass  
class OutgoingMessage:
    channel_type: str
    channel_id: str
    content: str
    reply_to: Optional[str] = None
    media: list = None
    metadata: dict = None


class SessionPlugin(Plugin):
    """Session orchestrator - routes messages between channels and agent."""

    meta = PluginMeta(
        id="session",
        version="1.0.0",
        extension_points=[
            "session.receive",   # receive() -> list[IncomingMessage]
            "session.send",      # send(OutgoingMessage) -> bool
            "session.typing",    # typing(channel_id) -> None
            "session.presence",  # presence(status: str) -> None
        ],
        priority=10,  # Early - before channels
    )

    def __init__(self):
        self._registry = None
        self._channels = {}  # channel_type -> plugin

    def configure(self, config: dict) -> None:
        self._config = config

    def start(self) -> None:
        print("[Session] Starting session orchestrator", file=sys.stderr)
        self._discover_channels()

    def stop(self) -> None:
        pass

    def _discover_channels(self) -> None:
        """Discover all channel implementations."""
        if not self._registry:
            return

        for plugin_id, plugin, method_name in self._registry.get_implementations(
            "session.receive"
        ):
            # Use plugin_id as channel type
            self._channels[plugin_id] = plugin
            print(f"[Session] Registered channel: {plugin_id}", file=sys.stderr)

    def poll_all_channels(self) -> list[IncomingMessage]:
        """Poll all channels for new messages.
        
        Returns:
            List of normalized IncomingMessage objects
        """
        messages = []

        for plugin_id, plugin, method_name in self._registry.get_implementations(
            "session.receive"
        ):
            try:
                method = getattr(plugin, method_name)
                channel_messages = method()
                
                # Tag each message with its source channel
                for msg in channel_messages:
                    msg.channel_type = plugin_id
                    messages.append(msg)
                    
            except Exception as e:
                print(f"[Session] Error polling {plugin_id}: {e}", file=sys.stderr)

        # Sort by timestamp
        messages.sort(key=lambda m: m.timestamp)
        return messages

    def send(self, message: OutgoingMessage) -> bool:
        """Send message to the appropriate channel.
        
        Args:
            message: OutgoingMessage with channel_type set
            
        Returns:
            True if sent successfully
        """
        channel_type = message.channel_type

        for plugin_id, plugin, method_name in self._registry.get_implementations(
            "session.send"
        ):
            if plugin_id == channel_type:
                try:
                    method = getattr(plugin, method_name)
                    return method(message)
                except Exception as e:
                    print(f"[Session] Error sending via {plugin_id}: {e}", file=sys.stderr)
                    return False

        print(f"[Session] No channel found for type: {channel_type}", file=sys.stderr)
        return False

    def typing(self, channel_type: str, channel_id: str) -> None:
        """Show typing indicator on a channel."""
        for plugin_id, plugin, method_name in self._registry.get_implementations(
            "session.typing"
        ):
            if plugin_id == channel_type:
                try:
                    method = getattr(plugin, method_name)
                    method(channel_id)
                except Exception as e:
                    print(f"[Session] Error typing on {plugin_id}: {e}", file=sys.stderr)
                return

    def broadcast(self, content: str, exclude_channel: str = None) -> None:
        """Send message to all channels.
        
        Args:
            content: Message to broadcast
            exclude_channel: Optional channel to skip (avoid echo)
        """
        for plugin_id, plugin, method_name in self._registry.get_implementations(
            "session.send"
        ):
            if plugin_id == exclude_channel:
                continue
                
            try:
                # Get default channel_id from plugin config
                if hasattr(plugin, 'get_default_channel_id'):
                    channel_id = plugin.get_default_channel_id()
                    message = OutgoingMessage(
                        channel_type=plugin_id,
                        channel_id=channel_id,
                        content=content,
                    )
                    method = getattr(plugin, method_name)
                    method(message)
            except Exception as e:
                print(f"[Session] Error broadcasting to {plugin_id}: {e}", file=sys.stderr)


def create_plugin() -> SessionPlugin:
    return SessionPlugin()
```

## Channel Plugin Implementation (Telegram Example)

```python
"""Telegram channel plugin - implements session extension points."""

from datetime import datetime
from typing import Optional

from cobot.plugins.base import Plugin, PluginMeta
# Import from session plugin
from cobot.plugins.session.plugin import IncomingMessage, OutgoingMessage


class TelegramPlugin(Plugin):
    """Telegram channel implementation."""

    meta = PluginMeta(
        id="telegram",
        version="1.0.0",
        dependencies=["session"],  # Depends on session plugin
        implements={
            "session.receive": "poll_updates",
            "session.send": "send_message",
            "session.typing": "send_typing",
        },
        priority=30,  # After session
    )

    def __init__(self):
        self._bot = None
        self._last_update_id = 0

    def configure(self, config: dict) -> None:
        self._token = config.get("bot_token")
        self._groups = config.get("groups", [])

    def start(self) -> None:
        import httpx
        self._client = httpx.Client(
            base_url=f"https://api.telegram.org/bot{self._token}"
        )

    def stop(self) -> None:
        if hasattr(self, '_client'):
            self._client.close()

    # --- session.receive implementation ---
    
    def poll_updates(self) -> list[IncomingMessage]:
        """Poll Telegram for new messages."""
        messages = []
        
        resp = self._client.get(
            "/getUpdates",
            params={"offset": self._last_update_id + 1, "timeout": 1}
        )
        data = resp.json()
        
        for update in data.get("result", []):
            self._last_update_id = update["update_id"]
            
            if "message" in update:
                msg = update["message"]
                messages.append(IncomingMessage(
                    id=str(msg["message_id"]),
                    channel_type="telegram",  # Will be overwritten by session
                    channel_id=str(msg["chat"]["id"]),
                    sender_id=str(msg["from"]["id"]),
                    sender_name=msg["from"].get("first_name", "Unknown"),
                    content=msg.get("text", ""),
                    timestamp=datetime.fromtimestamp(msg["date"]),
                    reply_to=str(msg["reply_to_message"]["message_id"]) 
                             if msg.get("reply_to_message") else None,
                    metadata={"raw": msg},
                ))
        
        return messages

    # --- session.send implementation ---
    
    def send_message(self, message: OutgoingMessage) -> bool:
        """Send message to Telegram."""
        try:
            params = {
                "chat_id": message.channel_id,
                "text": message.content,
            }
            
            if message.reply_to:
                params["reply_to_message_id"] = message.reply_to
                
            resp = self._client.post("/sendMessage", json=params)
            return resp.status_code == 200
            
        except Exception as e:
            print(f"[Telegram] Send error: {e}")
            return False

    # --- session.typing implementation ---
    
    def send_typing(self, channel_id: str) -> None:
        """Send typing indicator."""
        self._client.post(
            "/sendChatAction",
            json={"chat_id": channel_id, "action": "typing"}
        )

    # --- Helper methods ---
    
    def get_default_channel_id(self) -> Optional[str]:
        """Get default channel for broadcasts."""
        if self._groups:
            return str(self._groups[0].get("id"))
        return None
```

## Agent Integration

```python
# In agent.py

class Agent:
    def __init__(self, registry):
        self._registry = registry
        self._session = registry.get_plugin("session")
    
    async def run_loop(self):
        """Main agent loop."""
        while True:
            # Poll all channels via session plugin
            messages = self._session.poll_all_channels()
            
            for msg in messages:
                # Show typing while processing
                self._session.typing(msg.channel_type, msg.channel_id)
                
                # Process message
                response = await self.process(msg)
                
                # Send response back to same channel
                self._session.send(OutgoingMessage(
                    channel_type=msg.channel_type,
                    channel_id=msg.channel_id,
                    content=response,
                    reply_to=msg.id,
                ))
            
            await asyncio.sleep(1)
```

## Benefits

1. **Channel-agnostic core** - Agent only talks to session plugin
2. **Multi-channel support** - Messages from any channel work the same
3. **Easy to add channels** - Just implement session.* extension points
4. **Testable** - Mock session plugin for testing agent logic
5. **Conversation routing** - Session knows where messages came from

## Configuration

```yaml
# cobot.yml
plugins:
  session:
    default_channel: telegram  # For broadcasts
    
  telegram:
    bot_token: ${TELEGRAM_BOT_TOKEN}
    groups:
      - id: -1001234567890
        name: "Main Group"
        
  discord:
    bot_token: ${DISCORD_BOT_TOKEN}
    guilds:
      - id: "123456789"
        channel: "general"
```

## Priority Order

```
10 - session     (defines extension points)
20 - workspace   (provides paths)
30 - telegram    (implements session.*)
30 - discord     (implements session.*)
30 - nostr       (implements session.*)
```

## Next Steps

1. Create session plugin with extension points
2. Refactor telegram plugin to implement session.*
3. Update agent to use session plugin
4. Add tests for session routing
