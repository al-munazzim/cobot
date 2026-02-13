"""Tests for main Cobot agent class."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from cobot.agent import Cobot
from cobot.plugins import (
    PluginRegistry,
    reset_registry,
    LLMResponse,
    LLMError,
    Message,
    CommunicationError,
)


@pytest.fixture(autouse=True)
def reset_plugins():
    """Reset plugin registry before each test."""
    reset_registry()
    yield
    reset_registry()


@pytest.fixture
def mock_registry():
    """Create a mock registry with basic plugins."""
    registry = Mock(spec=PluginRegistry)

    # Mock config plugin
    config_plugin = Mock()
    config_plugin.get_config.return_value = Mock(
        soul_path=Path("/nonexistent/SOUL.md"),
        polling_interval=30,
        provider="ppq",
    )

    # Mock LLM plugin
    llm_plugin = Mock()
    llm_plugin.chat.return_value = LLMResponse(content="Hello human!", model="test")

    # Mock communication plugin
    comm_plugin = Mock()
    comm_plugin.receive.return_value = []
    comm_plugin.send.return_value = "event123"
    comm_plugin.get_identity.return_value = {"npub": "npub1test", "hex": "abc123"}

    # Mock tools plugin
    tools_plugin = Mock()
    tools_plugin.get_definitions.return_value = []
    tools_plugin.restart_requested = False

    def get_plugin(name):
        plugins = {"config": config_plugin}
        return plugins.get(name)

    def get_by_capability(cap):
        caps = {
            "llm": llm_plugin,
            "communication": comm_plugin,
            "tools": tools_plugin,
        }
        return caps.get(cap)

    registry.get = get_plugin
    registry.get_by_capability = get_by_capability
    registry.list_plugins.return_value = []

    return registry


class TestCobot:
    """Test Cobot class."""

    def test_init(self, mock_registry):
        """Should initialize with registry."""
        bot = Cobot(mock_registry)

        assert bot.registry == mock_registry
        assert "Cobot" in bot.soul  # Default soul

    def test_load_soul_exists(self, mock_registry):
        """Should load SOUL.md if it exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            soul_path = Path(tmpdir) / "SOUL.md"
            soul_path.write_text("I am TestBot!")

            config_plugin = mock_registry.get("config")
            config_plugin.get_config.return_value.soul_path = soul_path

            bot = Cobot(mock_registry)

            assert bot.soul == "I am TestBot!"

    def test_load_soul_missing(self, mock_registry):
        """Should use default soul if file missing."""
        bot = Cobot(mock_registry)

        assert "Cobot" in bot.soul

    def test_respond_success(self, mock_registry):
        """Should return LLM response."""
        bot = Cobot(mock_registry)

        response = bot.respond("Hi there")

        assert response == "Hello human!"
        mock_registry.get_by_capability("llm").chat.assert_called_once()

    def test_respond_no_llm(self, mock_registry):
        """Should return error if no LLM configured."""
        mock_registry.get_by_capability = Mock(return_value=None)

        bot = Cobot(mock_registry)
        response = bot.respond("Hi")

        assert "Error" in response
        assert "No LLM" in response

    def test_respond_llm_error(self, mock_registry):
        """Should return error message on LLM failure."""
        llm_plugin = mock_registry.get_by_capability("llm")
        llm_plugin.chat.side_effect = LLMError("API failed")

        bot = Cobot(mock_registry)
        response = bot.respond("Hi")

        assert "Error" in response
        assert "API failed" in response


class TestNostrIntegration:
    """Test communication message handling."""

    def test_handle_message(self, mock_registry):
        """Should respond to incoming message."""
        bot = Cobot(mock_registry)

        msg = Message(
            id="event1",
            sender="npub1sender",
            content="Hello bot!",
            timestamp=1000,
        )

        bot.handle_message(msg)

        # Should have called LLM
        mock_registry.get_by_capability("llm").chat.assert_called_once()

        # Should have sent response
        comm = mock_registry.get_by_capability("communication")
        comm.send.assert_called_once()
        call_args = comm.send.call_args
        assert call_args[0][0] == "npub1sender"
        assert call_args[0][1] == "Hello human!"

    def test_handle_message_dedup(self, mock_registry):
        """Should not process same message twice."""
        bot = Cobot(mock_registry)

        msg = Message(
            id="event1",
            sender="npub1sender",
            content="Hello!",
            timestamp=1000,
        )

        # Process same message twice
        bot.handle_message(msg)
        bot.handle_message(msg)

        # LLM should only be called once
        assert mock_registry.get_by_capability("llm").chat.call_count == 1

    def test_poll_messages(self, mock_registry):
        """Should poll and handle messages."""
        comm_plugin = mock_registry.get_by_capability("communication")
        comm_plugin.receive.return_value = [
            Message("e1", "npub1a", "Hi", 1000),
            Message("e2", "npub1b", "Hello", 2000),
        ]

        bot = Cobot(mock_registry)
        count = bot.poll()

        assert count == 2
        assert mock_registry.get_by_capability("llm").chat.call_count == 2

    def test_poll_error(self, mock_registry):
        """Should handle poll errors gracefully."""
        comm_plugin = mock_registry.get_by_capability("communication")
        comm_plugin.receive.side_effect = CommunicationError("Connection failed")

        bot = Cobot(mock_registry)
        count = bot.poll()

        assert count == 0  # No crash, returns 0

    def test_poll_no_communication(self, mock_registry):
        """Should handle missing communication plugin."""
        mock_registry.get_by_capability = Mock(return_value=None)

        bot = Cobot(mock_registry)
        count = bot.poll()

        assert count == 0


class TestToolCalls:
    """Test tool call handling."""

    def test_respond_with_tool_call(self, mock_registry):
        """Should execute tool calls and continue."""
        llm_plugin = mock_registry.get_by_capability("llm")
        tools_plugin = mock_registry.get_by_capability("tools")

        # First call returns tool call, second returns final response
        llm_plugin.chat.side_effect = [
            LLMResponse(
                content="",
                tool_calls=[
                    {
                        "id": "call1",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "test.txt"}',
                        },
                    }
                ],
                model="test",
            ),
            LLMResponse(content="File contents: hello", model="test"),
        ]

        tools_plugin.execute.return_value = "hello"
        tools_plugin.get_definitions.return_value = [
            {"type": "function", "function": {"name": "read_file"}}
        ]

        bot = Cobot(mock_registry)
        response = bot.respond("Read test.txt")

        assert response == "File contents: hello"
        assert llm_plugin.chat.call_count == 2
        tools_plugin.execute.assert_called_once_with("read_file", {"path": "test.txt"})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
