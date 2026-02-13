"""Logger plugin - logs lifecycle events.

Priority: 5 (very early, logs everything)
"""

import json
import sys
from datetime import datetime, timezone

from ..base import Plugin, PluginMeta


class LoggerPlugin(Plugin):
    """Logging plugin for lifecycle events."""
    
    meta = PluginMeta(
        id="logger",
        version="1.0.0",
        capabilities=["logging"],
        dependencies=[],
        priority=5,
    )
    
    def __init__(self):
        self._level: str = "info"
        self._levels = {"debug": 0, "info": 1, "warn": 2, "error": 3}
    
    def configure(self, config: dict) -> None:
        logger_config = config.get("logger", {})
        self._level = logger_config.get("level", "info")
    
    def start(self) -> None:
        pass
    
    def stop(self) -> None:
        pass
    
    def _should_log(self, level: str) -> bool:
        return self._levels.get(level, 1) >= self._levels.get(self._level, 1)
    
    def _log(self, level: str, hook: str, msg: str, **extra):
        if not self._should_log(level):
            return
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        parts = [f"[{ts}]", f"[{level[0].upper()}]", f"[{hook}]", msg]
        if extra:
            parts.append(json.dumps(extra, default=str))
        print(" ".join(parts), file=sys.stderr, flush=True)
    
    # --- Hook Methods ---
    
    def on_message_received(self, ctx: dict) -> dict:
        msg = ctx.get("message", "")[:50]
        sender = ctx.get("sender", "")[:16]
        self._log("info", "msg_recv", f"From {sender}...", content=msg)
        return ctx
    
    def on_before_llm_call(self, ctx: dict) -> dict:
        model = ctx.get("model", "")
        self._log("debug", "llm_call", f"Calling {model}")
        return ctx
    
    def on_after_llm_call(self, ctx: dict) -> dict:
        tokens_in = ctx.get("tokens_in", 0)
        tokens_out = ctx.get("tokens_out", 0)
        self._log("info", "llm_done", f"Tokens: {tokens_in}→{tokens_out}")
        return ctx
    
    def on_before_tool_exec(self, ctx: dict) -> dict:
        tool = ctx.get("tool", "")
        self._log("info", "tool", f"Executing: {tool}")
        return ctx
    
    def on_after_send(self, ctx: dict) -> dict:
        recipient = ctx.get("recipient", "")[:16]
        self._log("info", "send", f"Sent to {recipient}...")
        return ctx
    
    def on_error(self, ctx: dict) -> dict:
        error = ctx.get("error", "")
        hook = ctx.get("hook", "")
        self._log("error", "error", f"In {hook}: {error}")
        return ctx


def create_plugin() -> LoggerPlugin:
    return LoggerPlugin()
