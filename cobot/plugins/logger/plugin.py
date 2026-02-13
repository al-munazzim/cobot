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
        messages = ctx.get("messages", [])
        
        # Log message count and system prompt preview
        sys_prompt = ""
        for m in messages:
            if m.get("role") == "system":
                sys_prompt = m.get("content", "")[:200]
                break
        
        self._log("debug", "llm_call", f"Calling {model} ({len(messages)} msgs)")
        if sys_prompt:
            self._log("debug", "llm_call", f"System: {sys_prompt}...")
        return ctx

    def on_after_llm_call(self, ctx: dict) -> dict:
        tokens_in = ctx.get("tokens_in", 0)
        tokens_out = ctx.get("tokens_out", 0)
        self._log("info", "llm_done", f"Tokens: {tokens_in}→{tokens_out}")
        return ctx

    def on_before_tool_exec(self, ctx: dict) -> dict:
        tool = ctx.get("tool", "")
        args = ctx.get("args", {})
        
        # Format args for readability
        if tool == "read_file":
            detail = args.get("path", "?")
        elif tool == "write_file":
            path = args.get("path", "?")
            content_len = len(args.get("content", ""))
            detail = f"{path} ({content_len} chars)"
        elif tool == "edit_file":
            path = args.get("path", "?")
            old_text = args.get("old_text", "")[:30]
            detail = f"{path} ('{old_text}...')"
        elif tool == "exec":
            cmd = args.get("command", "?")
            detail = cmd[:80] + ("..." if len(cmd) > 80 else "")
        else:
            # Generic: show first arg value
            detail = str(list(args.values())[0])[:60] if args else ""
        
        self._log("info", "tool", f"{tool}: {detail}")
        return ctx

    def on_after_tool_exec(self, ctx: dict) -> dict:
        tool = ctx.get("tool", "")
        result = ctx.get("result", "")
        
        # Truncate long results
        if len(result) > 100:
            result_preview = result[:100] + f"... ({len(result)} chars)"
        else:
            result_preview = result
        
        # Remove newlines for log readability
        result_preview = result_preview.replace("\n", "\\n")
        
        self._log("info", "tool_done", f"{tool} → {result_preview}")
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
