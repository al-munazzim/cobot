"""Tests for communication plugin."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from .. import create_plugin, CommunicationPlugin, IncomingMessage, OutgoingMessage


class TestCommunicationPlugin:
    """Test CommunicationPlugin class."""

    def test_create_plugin(self):
        plugin = create_plugin()
        assert isinstance(plugin, CommunicationPlugin)

    def test_plugin_meta(self):
        plugin = create_plugin()
        assert plugin.meta.id == "communication"
        assert plugin.meta.priority == 5  # Early

    def test_defines_extension_points(self):
        plugin = create_plugin()
        assert "communication.receive" in plugin.meta.extension_points
        assert "communication.send" in plugin.meta.extension_points
        assert "communication.typing" in plugin.meta.extension_points
        assert "communication.channels" in plugin.meta.extension_points


class TestCommunicationPoll:
    """Test poll() method."""

    def test_poll_returns_empty_without_registry(self):
        plugin = create_plugin()
        plugin.configure({})
        plugin.start()

        messages = plugin.poll()
        assert messages == []

    def test_poll_aggregates_from_implementations(self):
        plugin = create_plugin()

        class MockImpl:
            def receive(self):
                return [
                    IncomingMessage(
                        id="1",
                        channel_type="telegram",
                        channel_id="-100123",
                        sender_id="456",
                        sender_name="alice",
                        content="Hello",
                        timestamp=datetime.now(),
                    )
                ]

        class MockRegistry:
            def get_implementations(self, ext_point):
                if ext_point == "communication.receive":
                    return [("session", MockImpl(), "receive")]
                return []

        plugin._registry = MockRegistry()
        plugin.configure({})
        plugin.start()

        messages = plugin.poll()
        assert len(messages) == 1
        assert messages[0].content == "Hello"

    def test_poll_sorts_by_timestamp(self):
        plugin = create_plugin()

        class MockImpl:
            def receive(self):
                return [
                    IncomingMessage(
                        id="2",
                        channel_type="telegram",
                        channel_id="-100123",
                        sender_id="456",
                        sender_name="alice",
                        content="Second",
                        timestamp=datetime(2026, 2, 13, 12, 0, 0),
                    ),
                    IncomingMessage(
                        id="1",
                        channel_type="telegram",
                        channel_id="-100123",
                        sender_id="456",
                        sender_name="alice",
                        content="First",
                        timestamp=datetime(2026, 2, 13, 11, 0, 0),
                    ),
                ]

        class MockRegistry:
            def get_implementations(self, ext_point):
                if ext_point == "communication.receive":
                    return [("session", MockImpl(), "receive")]
                return []

        plugin._registry = MockRegistry()
        plugin.configure({})
        plugin.start()

        messages = plugin.poll()
        assert len(messages) == 2
        assert messages[0].content == "First"
        assert messages[1].content == "Second"


class TestCommunicationSend:
    """Test send() method."""

    def test_send_without_registry_returns_false(self):
        plugin = create_plugin()
        plugin.configure({})
        plugin.start()

        result = plugin.send(
            OutgoingMessage(
                channel_type="telegram",
                channel_id="-100123",
                content="Test",
            )
        )
        assert result is False

    def test_send_routes_to_implementation(self):
        plugin = create_plugin()

        sent_messages = []

        class MockImpl:
            def send(self, msg):
                sent_messages.append(msg)
                return True

        class MockRegistry:
            def get_implementations(self, ext_point):
                if ext_point == "communication.send":
                    return [("session", MockImpl(), "send")]
                return []

        plugin._registry = MockRegistry()
        plugin.configure({})
        plugin.start()

        msg = OutgoingMessage(
            channel_type="telegram",
            channel_id="-100123",
            content="Test",
        )
        result = plugin.send(msg)

        assert result is True
        assert len(sent_messages) == 1


class TestCommunicationGetChannels:
    """Test get_channels() method."""

    def test_get_channels_without_registry(self):
        plugin = create_plugin()
        plugin.configure({})
        plugin.start()

        channels = plugin.get_channels()
        assert channels == []

    def test_get_channels_aggregates_from_implementations(self):
        plugin = create_plugin()

        class MockImpl:
            def channels(self):
                return ["telegram", "discord"]

        class MockRegistry:
            def get_implementations(self, ext_point):
                if ext_point == "communication.channels":
                    return [("session", MockImpl(), "channels")]
                return []

        plugin._registry = MockRegistry()
        plugin.configure({})
        plugin.start()

        channels = plugin.get_channels()
        assert "telegram" in channels
        assert "discord" in channels


class TestMessageTypes:
    """Test message dataclasses."""

    def test_incoming_message_creation(self):
        msg = IncomingMessage(
            id="123",
            channel_type="telegram",
            channel_id="-100456",
            sender_id="789",
            sender_name="alice",
            content="Hello world",
            timestamp=datetime.now(),
        )
        assert msg.id == "123"
        assert msg.channel_type == "telegram"
        assert msg.content == "Hello world"

    def test_outgoing_message_creation(self):
        msg = OutgoingMessage(
            channel_type="telegram",
            channel_id="-100456",
            content="Reply",
            reply_to="123",
        )
        assert msg.channel_type == "telegram"
        assert msg.content == "Reply"
        assert msg.reply_to == "123"

    def test_incoming_message_defaults(self):
        msg = IncomingMessage(
            id="1",
            channel_type="telegram",
            channel_id="-100",
            sender_id="1",
            sender_name="test",
            content="test",
            timestamp=datetime.now(),
        )
        assert msg.reply_to is None
        assert msg.media == []
        assert msg.metadata == {}
