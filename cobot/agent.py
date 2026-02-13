#!/usr/bin/env python3
"""Cobot - Minimal self-sovereign AI agent.

Core agent loop using the plugin registry for all services.
All I/O operations are async for non-blocking concurrency.
"""

import asyncio
import sys
import time
import json
from pathlib import Path
from typing import Optional

from cobot.plugins import (
    run,
    LLMProvider,
    ToolProvider,
    LLMError,
)
from cobot.plugins.communication import OutgoingMessage


class Cobot:
    """Main agent class."""

    def __init__(self, registry):
        self.registry = registry
        self._config = self._get_config()
        self.soul = self._load_soul()
        self._processed_events: set[str] = set()

    def _get_config(self):
        """Get config from config plugin."""
        config_plugin = self.registry.get("config")
        if config_plugin:
            return config_plugin.get_config()
        return None

    def _load_soul(self) -> str:
        """Load system prompt from SOUL.md."""
        if self._config:
            soul_path = Path(self._config.soul_path)
            if soul_path.exists():
                return soul_path.read_text()
        return "You are Cobot, a helpful AI assistant."

    def _get_llm(self) -> Optional[LLMProvider]:
        """Get LLM provider from registry."""
        return self.registry.get_by_capability("llm")

    def _get_comm(self):
        """Get communication plugin for channel messaging."""
        return self.registry.get("communication")

    def _get_tools(self) -> Optional[ToolProvider]:
        """Get tools provider from registry."""
        return self.registry.get_by_capability("tools")

    async def _do_restart(self):
        """Restart the agent process."""
        import os
        import subprocess

        await run("on_shutdown", {"reason": "restart_requested"})
        await self.registry.stop_all()

        try:
            subprocess.run(
                ["systemctl", "--user", "restart", "cobot"], check=True, timeout=5
            )
        except Exception:
            os.execv(sys.executable, [sys.executable] + sys.argv)

    async def respond(self, message: str, sender: str = "unknown") -> str:
        """Generate a response to a message."""
        llm = self._get_llm()
        tools = self._get_tools()

        if not llm:
            return "Error: No LLM configured"

        messages = [
            {"role": "system", "content": self.soul},
            {"role": "user", "content": message},
        ]

        # Hook: transform_system_prompt
        ctx = await run(
            "transform_system_prompt",
            {
                "prompt": self.soul,
                "peer": sender,
                "messages": messages,
            },
        )
        messages[0]["content"] = ctx.get("prompt", self.soul)

        # Hook: transform_history
        ctx = await run(
            "transform_history",
            {
                "messages": messages,
                "peer": sender,
            },
        )
        messages = ctx.get("messages", messages)

        tool_defs = tools.get_definitions() if tools else []
        max_rounds = 10

        try:
            for _ in range(max_rounds):
                # Hook: on_before_llm_call
                ctx = await run(
                    "on_before_llm_call",
                    {
                        "messages": messages,
                        "model": self._config.provider if self._config else "unknown",
                        "tools": tool_defs,
                    },
                )
                if ctx.get("abort"):
                    return ctx.get("abort_message", "Request aborted.")

                # LLM call - currently sync, could be made async later
                response = llm.chat(messages, tools=tool_defs if tool_defs else None)

                # Hook: on_after_llm_call
                await run(
                    "on_after_llm_call",
                    {
                        "response": response.content,
                        "model": response.model,
                        "tokens_in": response.tokens_in,
                        "tokens_out": response.tokens_out,
                        "has_tool_calls": response.has_tool_calls,
                    },
                )

                if not response.has_tool_calls:
                    break

                # Process tool calls
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.content,
                        "tool_calls": response.tool_calls,
                    }
                )

                for tool_call in response.tool_calls:
                    tool_name = tool_call["function"]["name"]
                    raw_args = tool_call["function"]["arguments"]
                    tool_args = (
                        json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    )
                    tool_id = tool_call["id"]

                    # Hook: on_before_tool_exec
                    ctx = await run(
                        "on_before_tool_exec", {"tool": tool_name, "args": tool_args}
                    )
                    if ctx.get("abort"):
                        result = ctx.get("abort_message", "Blocked.")
                    elif tools:
                        # Tool execution - currently sync, could be made async
                        result = tools.execute(tool_name, tool_args)
                    else:
                        result = "Error: Tools not available"

                    # Hook: on_after_tool_exec
                    await run(
                        "on_after_tool_exec",
                        {
                            "tool": tool_name,
                            "args": tool_args,
                            "result": result,
                        },
                    )

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": result,
                        }
                    )

            # Hook: transform_response
            ctx = await run(
                "transform_response",
                {
                    "text": response.content or "",
                    "recipient": sender,
                },
            )

            final_text = ctx.get("text", response.content or "")
            if not final_text.strip():
                final_text = "(No response generated - model may have hit token limit)"
            return final_text

        except LLMError as e:
            await run("on_error", {"error": e, "hook": "llm_call"})
            return f"Error: {e}"

    async def handle_message(self, msg) -> None:
        """Handle an incoming message.

        Args:
            msg: IncomingMessage from session plugin
        """
        # Deduplicate by message ID
        msg_key = f"{msg.channel_type}:{msg.channel_id}:{msg.id}"
        if msg_key in self._processed_events:
            return

        self._processed_events.add(msg_key)
        if len(self._processed_events) > 1000:
            self._processed_events = set(list(self._processed_events)[500:])

        # Hook: on_message_received
        ctx = await run(
            "on_message_received",
            {
                "message": msg.content,
                "sender": msg.sender_name,
                "sender_id": msg.sender_id,
                "channel_type": msg.channel_type,
                "channel_id": msg.channel_id,
                "event_id": msg.id,
            },
        )
        if ctx.get("abort"):
            return

        # Show typing indicator
        comm = self._get_comm()
        if comm:
            comm.typing(msg.channel_type, msg.channel_id)

        message = ctx.get("message", msg.content)
        response_text = await self.respond(message, sender=msg.sender_name)

        # Hook: on_before_send
        ctx = await run(
            "on_before_send", {"text": response_text, "recipient": msg.sender_name}
        )
        if ctx.get("abort"):
            return
        response_text = ctx.get("text", response_text)

        # Send response via communication plugin
        if comm:
            success = comm.send(
                OutgoingMessage(
                    channel_type=msg.channel_type,
                    channel_id=msg.channel_id,
                    content=response_text,
                    reply_to=msg.id,
                )
            )
            if success:
                await run(
                    "on_after_send",
                    {
                        "text": response_text,
                        "recipient": msg.sender_name,
                        "channel_type": msg.channel_type,
                        "channel_id": msg.channel_id,
                    },
                )
            else:
                await run("on_error", {"error": "Send failed", "hook": "send"})

        # Check restart
        tools = self._get_tools()
        if tools and tools.restart_requested:
            await self._do_restart()

    async def poll(self) -> int:
        """Poll for new messages from all channels.

        Messages are processed concurrently for better multi-user performance.
        """
        comm = self._get_comm()
        if not comm:
            return 0

        try:
            messages = comm.poll()
            if messages:
                # Process all messages concurrently
                await asyncio.gather(
                    *[self.handle_message(msg) for msg in messages],
                    return_exceptions=True,  # Don't fail all if one fails
                )
            return len(messages)
        except Exception as e:
            await run("on_error", {"error": e, "hook": "poll"})
            return 0

    async def run_loop(self):
        """Run the main agent loop."""
        comm = self._get_comm()
        if comm:
            channels = comm.get_channels()
            if channels:
                print(f"Channels: {', '.join(channels)}", file=sys.stderr)
            else:
                print("Warning: No channels registered", file=sys.stderr)

        interval = 30
        if self._config:
            interval = self._config.polling_interval

        try:
            while True:
                await self.poll()
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            await run("on_shutdown", {"reason": "cancelled"})
            await self.registry.stop_all()
        except KeyboardInterrupt:
            await run("on_shutdown", {"reason": "keyboard_interrupt"})
            await self.registry.stop_all()

    async def run_stdin(self):
        """Run in stdin mode (async readline)."""
        print("Cobot ready. Type a message (Ctrl+D to exit):", file=sys.stderr)

        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        try:
            while True:
                line = await reader.readline()
                if not line:
                    break

                message = line.decode().strip()
                if not message:
                    continue

                ctx = await run(
                    "on_message_received",
                    {
                        "message": message,
                        "sender": "stdin",
                        "event_id": f"stdin-{time.time()}",
                    },
                )
                if ctx.get("abort"):
                    print("[blocked]", file=sys.stderr)
                    continue

                response = await self.respond(
                    ctx.get("message", message), sender="stdin"
                )

                # Hook: on_before_send
                ctx = await run(
                    "on_before_send", {"text": response, "recipient": "stdin"}
                )
                if ctx.get("abort"):
                    continue

                print(ctx.get("text", response))
                await run("on_after_send", {"text": response, "recipient": "stdin"})

                # Check restart
                tools = self._get_tools()
                if tools and tools.restart_requested:
                    await self._do_restart()

        except asyncio.CancelledError:
            pass
        finally:
            await run("on_shutdown", {"reason": "stdin_eof"})
            await self.registry.stop_all()

    # Sync wrappers for CLI compatibility
    def run_loop_sync(self):
        """Synchronous wrapper for run_loop."""
        asyncio.run(self.run_loop())

    def run_stdin_sync(self):
        """Synchronous wrapper for run_stdin."""
        asyncio.run(self.run_stdin())
