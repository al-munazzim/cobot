"""Telegram plugin - multi-group message logging and archival.

Priority: 25 (after config)
Capability: communication
Extension Points:
  - telegram.on_message: Called when a new message is received
  - telegram.on_edit: Called when a message is edited
  - telegram.on_delete: Called when a message is deleted
  - telegram.on_media: Called when media is downloaded (with local path)
"""

import os
import sys
import time
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from telegram import Update, Bot
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
)

from ..base import Plugin, PluginMeta
from ..interfaces import CommunicationProvider, Message, CommunicationError


@dataclass
class GroupConfig:
    """Configuration for a single group."""

    id: int
    name: str = ""
    enabled: bool = True


@dataclass
class TelegramMessage:
    """Extended message with Telegram-specific fields."""

    group_id: int
    group_name: str
    message_id: int
    from_user: dict
    timestamp: str
    text: str
    reply_to: Optional[int] = None
    edit_date: Optional[str] = None
    media: Optional[dict] = None
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for extension points."""
        return {
            "group_id": self.group_id,
            "group_name": self.group_name,
            "message_id": self.message_id,
            "from_user": self.from_user,
            "timestamp": self.timestamp,
            "text": self.text,
            "reply_to": self.reply_to,
            "edit_date": self.edit_date,
            "media": self.media,
            "raw": self.raw,
        }


class TelegramPlugin(Plugin, CommunicationProvider):
    """Telegram multi-group logging plugin.

    Monitors multiple Telegram groups and exposes messages via extension points
    for other plugins to process (archival, git sync, etc.).

    Does NOT use LLM - purely for logging and message routing.
    """

    meta = PluginMeta(
        id="telegram",
        version="0.1.0",
        capabilities=["communication"],
        dependencies=["config"],
        priority=25,
        extension_points=[
            "telegram.on_message",
            "telegram.on_edit",
            "telegram.on_delete",
            "telegram.on_media",
        ],
    )

    def __init__(self):
        self._bot_token: Optional[str] = None
        self._groups: dict[int, GroupConfig] = {}
        self._media_dir: Path = Path("./media")
        self._app: Optional[Application] = None
        self._bot: Optional[Bot] = None
        self._running = False
        self._message_buffer: list[TelegramMessage] = []
        self._registry = None

    def configure(self, config: dict) -> None:
        """Configure the Telegram plugin.

        Config format:
            telegram:
              bot_token: "${TELEGRAM_BOT_TOKEN}"
              groups:
                - id: -100123456789
                  name: "dev-chat"
                - id: -100987654321
                  name: "announcements"
              media_dir: "./media"
        """
        self._bot_token = config.get("bot_token") or os.environ.get(
            "TELEGRAM_BOT_TOKEN"
        )

        if not self._bot_token:
            print("[telegram] Warning: No bot_token configured", file=sys.stderr)
            return

        # Parse groups
        groups_config = config.get("groups", [])
        for g in groups_config:
            if isinstance(g, dict) and "id" in g:
                group_id = int(g["id"])
                self._groups[group_id] = GroupConfig(
                    id=group_id,
                    name=g.get("name", str(group_id)),
                    enabled=g.get("enabled", True),
                )

        # Media directory
        media_dir = config.get("media_dir", "./media")
        self._media_dir = Path(media_dir)
        self._media_dir.mkdir(parents=True, exist_ok=True)

        print(f"[telegram] Configured with {len(self._groups)} groups", file=sys.stderr)

    def set_registry(self, registry) -> None:
        """Set registry reference for calling extension points."""
        self._registry = registry

    def start(self) -> None:
        """Start the Telegram bot."""
        if not self._bot_token:
            print("[telegram] Cannot start: no bot token", file=sys.stderr)
            return

        self._bot = Bot(token=self._bot_token)
        self._app = Application.builder().token(self._bot_token).build()

        # Register handlers
        self._app.add_handler(
            MessageHandler(filters.ALL & ~filters.COMMAND, self._handle_message)
        )

        self._running = True
        print("[telegram] Bot started", file=sys.stderr)

    def stop(self) -> None:
        """Stop the Telegram bot."""
        self._running = False
        if self._app:
            # Graceful shutdown
            pass
        print("[telegram] Bot stopped", file=sys.stderr)

    async def _handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle incoming message from any group."""
        if not update.message and not update.edited_message:
            return

        msg = update.edited_message or update.message
        is_edit = update.edited_message is not None

        # Check if from a monitored group
        chat_id = msg.chat_id
        if chat_id not in self._groups:
            # Auto-add unknown groups with numeric name
            self._groups[chat_id] = GroupConfig(id=chat_id, name=str(chat_id))

        group = self._groups[chat_id]
        if not group.enabled:
            return

        # Build user info
        from_user = {}
        if msg.from_user:
            from_user = {
                "id": msg.from_user.id,
                "username": msg.from_user.username or "",
                "first_name": msg.from_user.first_name or "",
                "last_name": msg.from_user.last_name or "",
            }

        # Build message object
        telegram_msg = TelegramMessage(
            group_id=chat_id,
            group_name=group.name,
            message_id=msg.message_id,
            from_user=from_user,
            timestamp=msg.date.isoformat()
            if msg.date
            else datetime.utcnow().isoformat(),
            text=msg.text or msg.caption or "",
            reply_to=msg.reply_to_message.message_id if msg.reply_to_message else None,
            edit_date=msg.edit_date.isoformat() if msg.edit_date else None,
            raw=msg.to_dict() if hasattr(msg, "to_dict") else {},
        )

        # Handle media
        media_info = await self._process_media(msg, context)
        if media_info:
            telegram_msg.media = media_info

        # Buffer message
        self._message_buffer.append(telegram_msg)

        # Call extension points
        ctx = {"message": telegram_msg.to_dict()}

        if is_edit:
            self._call_extension("telegram.on_edit", ctx)
        else:
            self._call_extension("telegram.on_message", ctx)

        if media_info:
            self._call_extension("telegram.on_media", ctx)

    async def _process_media(
        self, msg, context: ContextTypes.DEFAULT_TYPE
    ) -> Optional[dict]:
        """Download and process media attachments."""
        media_info = None
        file_obj = None
        media_type = None

        # Determine media type and get file
        if msg.photo:
            media_type = "photo"
            file_obj = msg.photo[-1]  # Largest size
        elif msg.document:
            media_type = "document"
            file_obj = msg.document
        elif msg.video:
            media_type = "video"
            file_obj = msg.video
        elif msg.voice:
            media_type = "voice"
            file_obj = msg.voice
        elif msg.audio:
            media_type = "audio"
            file_obj = msg.audio
        elif msg.sticker:
            media_type = "sticker"
            file_obj = msg.sticker

        if file_obj and hasattr(file_obj, "file_id"):
            try:
                # Create date-based directory
                date_str = datetime.utcnow().strftime("%Y-%m-%d")
                day_dir = self._media_dir / date_str
                day_dir.mkdir(parents=True, exist_ok=True)

                # Download file
                file = await context.bot.get_file(file_obj.file_id)

                # Determine extension
                ext = ""
                if hasattr(file_obj, "file_name") and file_obj.file_name:
                    ext = Path(file_obj.file_name).suffix
                elif media_type == "photo":
                    ext = ".jpg"
                elif media_type == "voice":
                    ext = ".ogg"
                elif media_type == "video":
                    ext = ".mp4"
                elif media_type == "sticker":
                    ext = ".webp"

                # Build local path
                filename = f"{media_type}_{msg.message_id}{ext}"
                local_path = day_dir / filename

                # Download
                await file.download_to_drive(str(local_path))

                media_info = {
                    "type": media_type,
                    "file_id": file_obj.file_id,
                    "local_path": str(local_path),
                    "file_size": getattr(file_obj, "file_size", None),
                    "mime_type": getattr(file_obj, "mime_type", None),
                }

                print(
                    f"[telegram] Downloaded {media_type}: {local_path}",
                    file=sys.stderr,
                )

            except Exception as e:
                print(f"[telegram] Media download failed: {e}", file=sys.stderr)

        return media_info

    def _call_extension(self, point: str, ctx: dict) -> dict:
        """Call an extension point if registry is available."""
        if self._registry:
            return self._registry.call_extension(point, ctx)
        return ctx

    # --- CommunicationProvider Interface ---

    def get_identity(self) -> dict:
        """Get bot identity."""
        if self._bot:
            return {
                "type": "telegram_bot",
                "token_prefix": self._bot_token[:10] + "..." if self._bot_token else "",
                "groups": list(self._groups.keys()),
            }
        return {"type": "telegram_bot", "status": "not_configured"}

    def receive(self, since_minutes: int = 5) -> list[Message]:
        """Get buffered messages from the last N minutes.

        Note: This returns the buffer and clears it. For continuous
        monitoring, use the extension points instead.
        """
        cutoff = time.time() - (since_minutes * 60)
        messages = []

        for tm in self._message_buffer:
            try:
                msg_time = datetime.fromisoformat(tm.timestamp).timestamp()
                if msg_time >= cutoff:
                    messages.append(
                        Message(
                            id=str(tm.message_id),
                            sender=tm.from_user.get(
                                "username", str(tm.from_user.get("id", "unknown"))
                            ),
                            content=tm.text,
                            timestamp=int(msg_time),
                        )
                    )
            except Exception:
                pass

        # Clear buffer
        self._message_buffer = [
            m
            for m in self._message_buffer
            if datetime.fromisoformat(m.timestamp).timestamp() >= cutoff
        ]

        return messages

    def send(self, recipient: str, message: str) -> str:
        """Send a message to a group or user.

        Args:
            recipient: Group ID (negative number) or user ID
            message: Message text

        Returns:
            Message ID
        """
        if not self._bot:
            raise CommunicationError("Bot not initialized")

        try:
            chat_id = int(recipient)

            # Run async send in sync context
            async def _send():
                result = await self._bot.send_message(chat_id=chat_id, text=message)
                return str(result.message_id)

            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, create task
                asyncio.ensure_future(_send())
                return "pending"
            else:
                return loop.run_until_complete(_send())

        except Exception as e:
            raise CommunicationError(f"Failed to send: {e}")

    def run_polling(self) -> None:
        """Start polling for messages (blocking).

        Call this from the main agent loop or in a separate thread.
        """
        if not self._app:
            print("[telegram] Cannot poll: app not initialized", file=sys.stderr)
            return

        print("[telegram] Starting polling...", file=sys.stderr)
        self._app.run_polling(allowed_updates=Update.ALL_TYPES)


def create_plugin() -> TelegramPlugin:
    """Factory function to create the plugin."""
    return TelegramPlugin()
