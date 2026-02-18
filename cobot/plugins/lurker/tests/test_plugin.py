"""Tests for lurker plugin."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from cobot.plugins.lurker.plugin import LurkerPlugin


@pytest.fixture
def lurker(tmp_path):
    """Create a configured lurker plugin."""
    plugin = LurkerPlugin()
    plugin.configure({
        "lurker": {
            "channels": [
                {"id": "-100111", "name": "dev-chat"},
                {"id": "-100222", "name": "announcements"},
            ],
            "sink": "jsonl",
            "base_dir": str(tmp_path / "lurker"),
        }
    })
    return plugin


@pytest.fixture
def lurker_md(tmp_path):
    """Lurker with markdown sink."""
    plugin = LurkerPlugin()
    plugin.configure({
        "lurker": {
            "channels": [{"id": "-100111", "name": "dev-chat"}],
            "sink": "markdown",
            "base_dir": str(tmp_path / "lurker"),
        }
    })
    return plugin


@pytest.fixture
def lurker_nosink(tmp_path):
    """Lurker with no sink (extension points only)."""
    plugin = LurkerPlugin()
    plugin.configure({
        "lurker": {
            "channels": [{"id": "-100111", "name": "dev-chat"}],
            "sink": "none",
            "base_dir": str(tmp_path / "lurker"),
        }
    })
    return plugin


def make_ctx(channel_id="-100111", message="hello world", sender="alice",
             sender_id="42", channel_type="telegram", event_id="msg_1"):
    """Build a message context dict."""
    return {
        "message": message,
        "sender": sender,
        "sender_id": sender_id,
        "channel_id": channel_id,
        "channel_type": channel_type,
        "event_id": event_id,
    }


class TestLurkerConfig:
    def test_channels_parsed(self, lurker):
        assert lurker.is_lurked("-100111")
        assert lurker.is_lurked("-100222")
        assert not lurker.is_lurked("-100999")

    def test_channel_names(self, lurker):
        assert lurker._channel_name("-100111") == "dev-chat"
        assert lurker._channel_name("-100999") == "-100999"

    def test_empty_config(self):
        plugin = LurkerPlugin()
        plugin.configure({})
        assert not plugin.is_lurked("anything")

    def test_sink_default(self):
        plugin = LurkerPlugin()
        plugin.configure({"lurker": {"channels": [{"id": "1"}]}})
        assert plugin._sink == "jsonl"


class TestLurkerHook:
    @pytest.mark.asyncio
    async def test_lurked_channel_aborts(self, lurker):
        ctx = make_ctx(channel_id="-100111")
        result = await lurker.on_message_received(ctx)
        assert result["abort"] is True

    @pytest.mark.asyncio
    async def test_non_lurked_channel_passes_through(self, lurker):
        ctx = make_ctx(channel_id="-100999")
        result = await lurker.on_message_received(ctx)
        assert result.get("abort") is not True

    @pytest.mark.asyncio
    async def test_counts_messages(self, lurker):
        for _ in range(3):
            await lurker.on_message_received(make_ctx(channel_id="-100111"))
        await lurker.on_message_received(make_ctx(channel_id="-100222"))

        assert lurker._counts["-100111"] == 3
        assert lurker._counts["-100222"] == 1


class TestJsonlSink:
    @pytest.mark.asyncio
    async def test_writes_jsonl(self, lurker, tmp_path):
        await lurker.on_message_received(make_ctx(message="test msg"))

        # Find the JSONL file
        lurker_dir = tmp_path / "lurker"
        jsonl_files = list(lurker_dir.rglob("*.jsonl"))
        assert len(jsonl_files) == 1

        lines = jsonl_files[0].read_text().strip().split("\n")
        assert len(lines) == 1

        record = json.loads(lines[0])
        assert record["text"] == "test msg"
        assert record["sender"] == "alice"
        assert record["channel"] == "-100111"
        assert record["channel_name"] == "dev-chat"

    @pytest.mark.asyncio
    async def test_appends_multiple(self, lurker, tmp_path):
        await lurker.on_message_received(make_ctx(message="msg 1"))
        await lurker.on_message_received(make_ctx(message="msg 2"))
        await lurker.on_message_received(make_ctx(message="msg 3"))

        jsonl_files = list((tmp_path / "lurker").rglob("*.jsonl"))
        lines = jsonl_files[0].read_text().strip().split("\n")
        assert len(lines) == 3

    @pytest.mark.asyncio
    async def test_separate_files_per_channel(self, lurker, tmp_path):
        await lurker.on_message_received(make_ctx(channel_id="-100111"))
        await lurker.on_message_received(make_ctx(channel_id="-100222"))

        jsonl_files = list((tmp_path / "lurker").rglob("*.jsonl"))
        assert len(jsonl_files) == 2

        names = {f.stem for f in jsonl_files}
        assert "-100111" in names
        assert "-100222" in names


class TestMarkdownSink:
    @pytest.mark.asyncio
    async def test_writes_markdown(self, lurker_md, tmp_path):
        await lurker_md.on_message_received(make_ctx(message="hello"))

        md_files = list((tmp_path / "lurker").rglob("*.md"))
        assert len(md_files) == 1

        content = md_files[0].read_text()
        assert "# dev-chat" in content
        assert "**alice**" in content
        assert "hello" in content

    @pytest.mark.asyncio
    async def test_appends_markdown(self, lurker_md, tmp_path):
        await lurker_md.on_message_received(make_ctx(message="first"))
        await lurker_md.on_message_received(
            make_ctx(message="second", sender="bob")
        )

        md_files = list((tmp_path / "lurker").rglob("*.md"))
        content = md_files[0].read_text()
        assert "**alice**" in content
        assert "**bob**" in content
        assert "first" in content
        assert "second" in content


class TestNoSink:
    @pytest.mark.asyncio
    async def test_no_files_written(self, lurker_nosink, tmp_path):
        await lurker_nosink.on_message_received(make_ctx())

        lurker_dir = tmp_path / "lurker"
        if lurker_dir.exists():
            assert list(lurker_dir.rglob("*.*")) == []

    @pytest.mark.asyncio
    async def test_still_aborts(self, lurker_nosink):
        ctx = make_ctx()
        result = await lurker_nosink.on_message_received(ctx)
        assert result["abort"] is True


class TestWizard:
    def test_wizard_section(self):
        plugin = LurkerPlugin()
        section = plugin.wizard_section()
        assert section is not None
        assert section["key"] == "lurker"
