"""Lurker plugin - channel observation with pluggable sinks.

Lurker observes all messages (incoming AND outgoing) on configured channels.
It does NOT suppress bot responses — the bot can be active or silent
independently. Lurking just means observing.

It defines extension points so other plugins can decide what to do
with observed messages (log to JSONL, archive to markdown, index, etc.).

This is mechanism: lurker decides WHICH channels to observe and
provides the message stream. Sinks decide WHAT to do with messages.

Priority: 6 (very early for incoming; also hooks on_after_send for outgoing)
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..base import Plugin, PluginMeta


class LurkerPlugin(Plugin):
    """Passive channel observer.

    Hooks into on_message_received. For channels configured as "lurk",
    it captures the message, fires lurker.on_observe for sinks to handle,
    and sets ctx["abort"] = True to prevent the agent from responding.

    For channels NOT in the lurk list, it passes through untouched.

    Config:
        lurker:
          channels:
            - id: "-100123456789"     # Channel/group ID (string)
              name: "dev-chat"        # Human label (optional)
            - id: "-100987654321"
              name: "announcements"
          sink: "jsonl"               # Default sink: jsonl | markdown | none
          base_dir: "./lurker"        # Where file sinks write

    Extension points defined:
        lurker.on_observe  — called for every message (incoming or outgoing)
                             on a lurked channel.
                             ctx: {message, channel_id, channel_type,
                                   channel_name, sender_id, sender_name,
                                   timestamp, direction, raw_ctx}
        lurker.on_edit     — called when an edit is observed
        lurker.on_media    — called when media is observed
    """

    meta = PluginMeta(
        id="lurker",
        version="0.1.0",
        capabilities=["lurker"],
        dependencies=[],
        priority=6,  # Before logger (5 is taken), before session routing
        extension_points=[
            "lurker.on_observe",
            "lurker.on_edit",
            "lurker.on_media",
        ],
    )

    def __init__(self):
        self._channels: dict[str, str] = {}  # channel_id -> name
        self._sink: str = "jsonl"
        self._base_dir: Path = Path("./lurker")
        self._registry = None
        self._counts: dict[str, int] = {}  # channel_id -> message count

    def configure(self, config: dict) -> None:
        """Configure lurker channels and default sink."""
        lurker_config = config.get("lurker", {})

        for ch in lurker_config.get("channels", []):
            ch_id = str(ch.get("id", ""))
            ch_name = ch.get("name", ch_id)
            if ch_id:
                self._channels[ch_id] = ch_name

        self._sink = lurker_config.get("sink", "jsonl")
        self._base_dir = Path(lurker_config.get("base_dir", "./lurker"))

    async def start(self) -> None:
        """Start lurker."""
        from ..registry import get_registry

        self._registry = get_registry()

        if self._channels:
            names = [f"{v} ({k})" for k, v in self._channels.items()]
            print(
                f"[Lurker] Observing {len(self._channels)} channels: "
                + ", ".join(names),
                file=sys.stderr,
            )
        else:
            print("[Lurker] No channels configured — lurking disabled", file=sys.stderr)

        if self._sink != "none":
            self._base_dir.mkdir(parents=True, exist_ok=True)
            print(
                f"[Lurker] Sink: {self._sink} → {self._base_dir}", file=sys.stderr
            )

    async def stop(self) -> None:
        """Report stats on shutdown."""
        if self._counts:
            total = sum(self._counts.values())
            print(f"[Lurker] Observed {total} messages total", file=sys.stderr)
            for ch_id, count in self._counts.items():
                name = self._channels.get(ch_id, ch_id)
                print(f"[Lurker]   {name}: {count}", file=sys.stderr)

    def is_lurked(self, channel_id: str) -> bool:
        """Check if a channel is in lurk mode."""
        return str(channel_id) in self._channels

    def _channel_name(self, channel_id: str) -> str:
        """Get human name for a channel."""
        return self._channels.get(str(channel_id), str(channel_id))

    # --- Hooks ---

    async def on_message_received(self, ctx: dict) -> dict:
        """Observe incoming messages on lurked channels.

        Does NOT abort — the bot can still respond. Lurking is observation only.
        """
        channel_id = str(ctx.get("channel_id", ""))

        if not self.is_lurked(channel_id):
            return ctx

        obs = self._build_observation(
            channel_id=channel_id,
            channel_type=ctx.get("channel_type", ""),
            sender_id=ctx.get("sender_id", ""),
            sender_name=ctx.get("sender", ""),
            message=ctx.get("message", ""),
            event_id=ctx.get("event_id", ""),
            direction="incoming",
            raw_ctx=ctx,
        )

        await self._observe(obs)
        return ctx

    async def on_after_send(self, ctx: dict) -> dict:
        """Observe outgoing messages (bot responses) on lurked channels."""
        channel_id = str(ctx.get("channel_id", ""))

        if not self.is_lurked(channel_id):
            return ctx

        obs = self._build_observation(
            channel_id=channel_id,
            channel_type=ctx.get("channel_type", ""),
            sender_id="self",
            sender_name="bot",
            message=ctx.get("text", ""),
            event_id="",
            direction="outgoing",
            raw_ctx=ctx,
        )

        await self._observe(obs)
        return ctx

    def _build_observation(self, *, channel_id, channel_type, sender_id,
                           sender_name, message, event_id, direction,
                           raw_ctx) -> dict:
        """Build a normalized observation dict."""
        return {
            "message": message,
            "channel_id": channel_id,
            "channel_type": channel_type,
            "channel_name": self._channel_name(channel_id),
            "sender_id": sender_id,
            "sender_name": sender_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_id": event_id,
            "direction": direction,
            "raw_ctx": raw_ctx,
        }

    async def _observe(self, obs: dict) -> None:
        """Process an observation: count, fire extension points, write sink."""
        channel_id = obs["channel_id"]
        self._counts[channel_id] = self._counts.get(channel_id, 0) + 1

        # Fire extension point for other plugins (sinks, indexers, etc.)
        if self._registry:
            for _, plugin, method_name in self._registry.get_implementations(
                "lurker.on_observe"
            ):
                try:
                    method = getattr(plugin, method_name)
                    if asyncio.iscoroutinefunction(method):
                        await method(obs)
                    else:
                        method(obs)
                except Exception as e:
                    print(f"[Lurker] Sink error: {e}", file=sys.stderr)

        # Built-in sink (if configured)
        if self._sink != "none":
            self._write_sink(obs)

    # --- Built-in sinks ---

    def _write_sink(self, obs: dict) -> None:
        """Write observation to built-in sink."""
        if self._sink == "jsonl":
            self._write_jsonl(obs)
        elif self._sink == "markdown":
            self._write_markdown(obs)

    def _day_dir(self, channel_id: str) -> Path:
        """Get date-based directory for a channel."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self._base_dir / date_str

    def _write_jsonl(self, obs: dict) -> None:
        """Write one JSONL line per message."""
        day_dir = self._day_dir(obs["channel_id"])
        day_dir.mkdir(parents=True, exist_ok=True)

        filepath = day_dir / f"{obs['channel_id']}.jsonl"
        record = {
            "ts": obs["timestamp"],
            "direction": obs["direction"],
            "channel": obs["channel_id"],
            "channel_name": obs["channel_name"],
            "sender_id": obs["sender_id"],
            "sender": obs["sender_name"],
            "text": obs["message"],
            "event_id": obs["event_id"],
        }

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _write_markdown(self, obs: dict) -> None:
        """Write markdown-formatted log."""
        day_dir = self._day_dir(obs["channel_id"])
        day_dir.mkdir(parents=True, exist_ok=True)

        filepath = day_dir / f"{obs['channel_id']}.md"
        ts = obs["timestamp"][:19].replace("T", " ")
        sender = obs["sender_name"] or obs["sender_id"]
        text = obs["message"]

        # Write header if new file
        if not filepath.exists():
            header = (
                f"# {obs['channel_name']} — "
                f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n"
            )
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(header)

        direction = obs.get("direction", "incoming")
        prefix = "→" if direction == "outgoing" else ""

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"{prefix}**{sender}** ({ts}):\n{text}\n\n")

    # --- Setup Wizard ---

    def wizard_section(self) -> dict | None:
        return {
            "key": "lurker",
            "name": "Lurker",
            "description": "Passively observe channels without responding",
        }

    def wizard_configure(self, config: dict) -> dict:
        import click

        click.echo("\nLurker — passive channel observation")
        click.echo("Messages in lurked channels are logged, not responded to.\n")

        channels = []
        while True:
            if not click.confirm(
                "Add a channel to lurk?" if not channels else "Add another?",
                default=len(channels) == 0,
            ):
                break
            ch_id = click.prompt("Channel ID")
            ch_name = click.prompt("Channel name", default=ch_id)
            channels.append({"id": ch_id, "name": ch_name})

        sink = click.prompt(
            "Default sink",
            type=click.Choice(["jsonl", "markdown", "none"]),
            default="jsonl",
        )

        base_dir = click.prompt("Log directory", default="./lurker")

        return {
            "channels": channels,
            "sink": sink,
            "base_dir": base_dir,
        }


# Need asyncio for checking coroutine functions
import asyncio


def create_plugin() -> LurkerPlugin:
    """Factory function for plugin discovery."""
    return LurkerPlugin()
