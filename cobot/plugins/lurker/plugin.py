"""Lurker plugin - passive channel observation with pluggable sinks.

Lurker sits in channels and observes messages without responding.
It defines extension points so other plugins can decide what to do
with observed messages (log to JSONL, archive to markdown, index, etc.).

This is mechanism: lurker decides WHICH channels to observe and
provides the message stream. Sinks decide WHAT to do with messages.

Priority: 6 (very early — must run before agent decides to respond)
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
        lurker.on_observe  — called for every message in a lurked channel
                             ctx: {message, channel_id, channel_type,
                                   channel_name, sender_id, sender_name,
                                   timestamp, raw_ctx}
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

    # --- Hook: on_message_received ---

    async def on_message_received(self, ctx: dict) -> dict:
        """Intercept messages from lurked channels.

        For lurked channels: observe, fire extension points, abort response.
        For other channels: pass through untouched.
        """
        channel_id = str(ctx.get("channel_id", ""))

        if not self.is_lurked(channel_id):
            return ctx

        channel_name = self._channel_name(channel_id)

        # Build observation context
        obs = {
            "message": ctx.get("message", ""),
            "channel_id": channel_id,
            "channel_type": ctx.get("channel_type", ""),
            "channel_name": channel_name,
            "sender_id": ctx.get("sender_id", ""),
            "sender_name": ctx.get("sender", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_id": ctx.get("event_id", ""),
            "raw_ctx": ctx,
        }

        # Count
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
                    print(
                        f"[Lurker] Sink error: {e}", file=sys.stderr
                    )

        # Built-in sink (if configured)
        if self._sink != "none":
            self._write_sink(obs)

        # Abort — don't let the agent respond
        ctx["abort"] = True
        return ctx

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

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"**{sender}** ({ts}):\n{text}\n\n")

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
