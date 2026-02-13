#!/usr/bin/env python3
"""Cobot - Minimal self-sovereign AI agent.

Core agent loop using the plugin registry for all services.
"""

import sys
import time
import json
from pathlib import Path
from typing import Optional

from cobot.plugins import (
    init_plugins,
    run,
    LLMProvider,
    CommunicationProvider,  # Legacy, kept for compatibility
    ToolProvider,
    LLMError,
    CommunicationError,
)
from cobot.plugins.session import OutgoingMessage


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

    def _get_session(self):
        """Get session plugin for channel communication."""
        return self.registry.get("session")

    def _get_communication(self) -> Optional[CommunicationProvider]:
        """Get communication provider from registry (legacy)."""
        return self.registry.get_by_capability("communication")

    def _get_tools(self) -> Optional[ToolProvider]:
        """Get tools provider from registry."""
        return self.registry.get_by_capability("tools")

    def _do_restart(self):
        """Restart the agent process."""
        import os
        import subprocess

        run("on_shutdown", {"reason": "restart_requested"})
        self.registry.stop_all()

        try:
            subprocess.run(
                ["systemctl", "--user", "restart", "cobot"], check=True, timeout=5
            )
        except Exception:
            os.execv(sys.executable, [sys.executable] + sys.argv)

    def respond(self, message: str, sender: str = "unknown") -> str:
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
        ctx = run(
            "transform_system_prompt",
            {
                "prompt": self.soul,
                "peer": sender,
                "messages": messages,
            },
        )
        messages[0]["content"] = ctx.get("prompt", self.soul)

        # Hook: transform_history
        ctx = run(
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
                ctx = run(
                    "on_before_llm_call",
                    {
                        "messages": messages,
                        "model": self._config.provider if self._config else "unknown",
                        "tools": tool_defs,
                    },
                )
                if ctx.get("abort"):
                    return ctx.get("abort_message", "Request aborted.")

                response = llm.chat(messages, tools=tool_defs if tool_defs else None)

                # Hook: on_after_llm_call
                run(
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
                    ctx = run(
                        "on_before_tool_exec", {"tool": tool_name, "args": tool_args}
                    )
                    if ctx.get("abort"):
                        result = ctx.get("abort_message", "Blocked.")
                    elif tools:
                        result = tools.execute(tool_name, tool_args)
                    else:
                        result = "Error: Tools not available"

                    # Hook: on_after_tool_exec
                    run(
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
            ctx = run(
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
            run("on_error", {"error": e, "hook": "llm_call"})
            return f"Error: {e}"

    def handle_message(self, msg) -> None:
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
        ctx = run(
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
        session = self._get_session()
        if session:
            session.typing(msg.channel_type, msg.channel_id)

        message = ctx.get("message", msg.content)
        response_text = self.respond(message, sender=msg.sender_name)

        # Hook: on_before_send
        ctx = run("on_before_send", {"text": response_text, "recipient": msg.sender_name})
        if ctx.get("abort"):
            return
        response_text = ctx.get("text", response_text)

        # Send response via session
        if session:
            success = session.send(OutgoingMessage(
                channel_type=msg.channel_type,
                channel_id=msg.channel_id,
                content=response_text,
                reply_to=msg.id,
            ))
            if success:
                run(
                    "on_after_send",
                    {
                        "text": response_text,
                        "recipient": msg.sender_name,
                        "channel_type": msg.channel_type,
                        "channel_id": msg.channel_id,
                    },
                )
            else:
                run("on_error", {"error": "Send failed", "hook": "send"})

        # Check restart
        tools = self._get_tools()
        if tools and tools.restart_requested:
            self._do_restart()

    def poll(self) -> int:
        """Poll for new messages from all channels."""
        session = self._get_session()
        if not session:
            return 0

        try:
            messages = session.poll_all_channels()
            for msg in messages:
                self.handle_message(msg)
            return len(messages)
        except Exception as e:
            run("on_error", {"error": e, "hook": "poll"})
            return 0

    def run_loop(self):
        """Run the main agent loop."""
        session = self._get_session()
        if session:
            channels = session.get_channels()
            if channels:
                print(f"Channels: {', '.join(channels)}", file=sys.stderr)
            else:
                print("Warning: No channels registered", file=sys.stderr)

        interval = 30
        if self._config:
            interval = self._config.polling_interval

        try:
            while True:
                self.poll()
                time.sleep(interval)
        except KeyboardInterrupt:
            run("on_shutdown", {"reason": "keyboard_interrupt"})
            self.registry.stop_all()

    def run_stdin(self):
        """Run in stdin mode."""
        print("Cobot ready. Type a message (Ctrl+D to exit):", file=sys.stderr)

        try:
            for line in sys.stdin:
                message = line.strip()
                if not message:
                    continue

                ctx = run(
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

                response = self.respond(ctx.get("message", message), sender="stdin")
                print(response)
                print(file=sys.stderr)
        except KeyboardInterrupt:
            pass

        run("on_shutdown", {"reason": "stdin_eof"})
        self.registry.stop_all()


def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Cobot - Self-sovereign AI agent")
    parser.add_argument("--stdin", action="store_true", help="Run in stdin mode")
    parser.add_argument("--plugins", type=Path, default=Path("cobot/plugins"))
    args = parser.parse_args()

    # Load config file first to get full config
    import yaml

    config_data = {}
    for config_path in [Path("cobot.yml"), Path("config.yaml")]:
        if config_path.exists():
            with open(config_path) as f:
                config_data = yaml.safe_load(f) or {}
            break

    # Initialize plugins with config
    plugins_dir = args.plugins if args.plugins.exists() else Path("cobot/plugins")
    registry = init_plugins(plugins_dir, config_data)

    print(f"Loaded {len(registry.list_plugins())} plugin(s)", file=sys.stderr)

    # Get config and check provider requirements
    config_plugin = registry.get("config")
    if config_plugin:
        config = config_plugin.get_config()

        # Check for required credentials based on provider
        if config.provider == "ppq":
            import os

            if not config_data.get("ppq", {}).get("api_key") and not os.environ.get(
                "PPQ_API_KEY"
            ):
                print("Error: PPQ_API_KEY not set", file=sys.stderr)
                sys.exit(1)

    bot = Cobot(registry)

    if args.stdin:
        bot.run_stdin()
    else:
        bot.run_loop()


if __name__ == "__main__":
    main()
