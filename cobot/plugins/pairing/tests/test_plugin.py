"""Tests for PairingPlugin."""

import asyncio

import pytest

from ..plugin import PairingPlugin, create_plugin
from ..storage import PairingStorage, generate_code


# === Storage Tests ===


class TestGenerateCode:
    """Test code generation."""

    def test_code_length(self):
        """Test default code length is 8."""
        code = generate_code()
        assert len(code) == 8

    def test_custom_length(self):
        """Test custom code length."""
        code = generate_code(12)
        assert len(code) == 12

    def test_code_is_uppercase(self):
        """Test code is uppercase alphanumeric."""
        code = generate_code()
        assert (
            code.isupper()
            or code.isdigit()
            or all(c.isupper() or c.isdigit() for c in code)
        )

    def test_no_ambiguous_chars(self):
        """Test code doesn't contain ambiguous characters."""
        for _ in range(100):
            code = generate_code()
            assert "O" not in code
            assert "0" not in code
            assert "I" not in code
            assert "1" not in code


class TestPairingStorage:
    """Test PairingStorage."""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create storage with temp file."""
        return PairingStorage(tmp_path / "pairing.yml")

    def test_empty_storage(self, storage):
        """Test fresh storage is empty."""
        assert storage.get_authorized() == []
        assert storage.get_pending() == []

    def test_is_authorized_empty(self, storage):
        """Test is_authorized on empty storage."""
        assert not storage.is_authorized("telegram", "123")

    def test_add_pending(self, storage):
        """Test adding a pending request."""
        req = storage.add_pending("telegram", "123", "alice")
        assert req.channel == "telegram"
        assert req.user_id == "123"
        assert req.name == "alice"
        assert len(req.code) == 8

    def test_add_pending_returns_existing(self, storage):
        """Test add_pending returns existing request for same user."""
        req1 = storage.add_pending("telegram", "123", "alice")
        req2 = storage.add_pending("telegram", "123", "alice")
        assert req1.code == req2.code

    def test_get_pending_by_code(self, storage):
        """Test getting pending request by code."""
        req = storage.add_pending("telegram", "123", "alice")
        found = storage.get_pending_by_code(req.code)
        assert found is not None
        assert found.user_id == "123"

    def test_get_pending_by_code_case_insensitive(self, storage):
        """Test code lookup is case insensitive."""
        req = storage.add_pending("telegram", "123", "alice")
        found = storage.get_pending_by_code(req.code.lower())
        assert found is not None

    def test_approve(self, storage):
        """Test approving a pending request."""
        req = storage.add_pending("telegram", "123", "alice")
        user = storage.approve(req.code)

        assert user is not None
        assert user.user_id == "123"
        assert storage.is_authorized("telegram", "123")
        assert storage.get_pending_by_code(req.code) is None

    def test_approve_invalid_code(self, storage):
        """Test approving with invalid code."""
        user = storage.approve("INVALID")
        assert user is None

    def test_reject(self, storage):
        """Test rejecting a pending request."""
        req = storage.add_pending("telegram", "123", "alice")
        assert storage.reject(req.code)
        assert storage.get_pending_by_code(req.code) is None

    def test_reject_invalid_code(self, storage):
        """Test rejecting with invalid code."""
        assert not storage.reject("INVALID")

    def test_revoke(self, storage):
        """Test revoking authorization."""
        req = storage.add_pending("telegram", "123", "alice")
        storage.approve(req.code)

        assert storage.is_authorized("telegram", "123")
        assert storage.revoke("telegram", "123")
        assert not storage.is_authorized("telegram", "123")

    def test_revoke_invalid_user(self, storage):
        """Test revoking non-existent user."""
        assert not storage.revoke("telegram", "999")

    def test_add_authorized_directly(self, storage):
        """Test directly adding authorized user (for owner_ids)."""
        user = storage.add_authorized("telegram", "123", "owner")
        assert storage.is_authorized("telegram", "123")
        assert user.name == "owner"

    def test_persistence(self, tmp_path):
        """Test data persists across instances."""
        path = tmp_path / "pairing.yml"

        # Create and add data
        storage1 = PairingStorage(path)
        storage1.add_pending("telegram", "123", "alice")
        storage1.add_authorized("telegram", "456", "bob")

        # Load in new instance
        storage2 = PairingStorage(path)
        assert storage2.get_pending_for_user("telegram", "123") is not None
        assert storage2.is_authorized("telegram", "456")


# === Plugin Tests ===


class TestPluginCreation:
    """Test plugin instantiation."""

    def test_create_plugin(self):
        """Test factory function."""
        plugin = create_plugin()
        assert isinstance(plugin, PairingPlugin)

    def test_plugin_meta(self):
        """Test plugin metadata."""
        plugin = PairingPlugin()
        assert plugin.meta.id == "pairing"
        assert plugin.meta.priority == 5


class TestPluginConfiguration:
    """Test plugin configuration."""

    def test_configure_defaults(self):
        """Test default configuration."""
        plugin = PairingPlugin()
        plugin.configure({})

        assert plugin._enabled is True
        assert plugin._owner_ids == {}

    def test_configure_disabled(self):
        """Test disabling pairing."""
        plugin = PairingPlugin()
        plugin.configure({"pairing": {"enabled": False}})

        assert plugin._enabled is False

    def test_configure_owner_ids(self):
        """Test owner_ids configuration."""
        plugin = PairingPlugin()
        plugin.configure(
            {
                "pairing": {
                    "owner_ids": {
                        "telegram": ["123", "456"],
                        "discord": ["789"],
                    }
                }
            }
        )

        assert plugin._owner_ids == {
            "telegram": ["123", "456"],
            "discord": ["789"],
        }


class TestPluginStart:
    """Test plugin startup."""

    def test_start_disabled(self, tmp_path, capsys):
        """Test start when disabled."""
        plugin = PairingPlugin()
        plugin.configure({"pairing": {"enabled": False}})
        asyncio.run(plugin.start())

        captured = capsys.readouterr()
        assert "Disabled" in captured.err

    def test_start_bootstraps_owners(self, tmp_path):
        """Test owner_ids are bootstrapped on start."""
        plugin = PairingPlugin()
        plugin._storage_path = tmp_path / "pairing.yml"
        plugin.configure(
            {
                "pairing": {
                    "owner_ids": {"telegram": ["123"]},
                }
            }
        )
        asyncio.run(plugin.start())

        assert plugin._storage.is_authorized("telegram", "123")


class TestOnMessageReceived:
    """Test message authorization."""

    @pytest.fixture
    def plugin(self, tmp_path):
        """Create configured plugin."""
        plugin = PairingPlugin()
        plugin._storage_path = tmp_path / "pairing.yml"
        plugin.configure(
            {
                "pairing": {
                    "owner_ids": {"telegram": ["owner123"]},
                }
            }
        )
        asyncio.run(plugin.start())
        return plugin

    def test_authorized_user_passes(self, plugin):
        """Test authorized user is not blocked."""
        ctx = {
            "channel_type": "telegram",
            "sender_id": "owner123",
            "sender": "owner",
            "channel_id": "-100123",
            "message": "hello",
        }

        result = asyncio.run(plugin.on_message_received(ctx))
        assert "abort" not in result or not result["abort"]

    def test_unauthorized_user_blocked(self, plugin):
        """Test unauthorized user is blocked."""
        ctx = {
            "channel_type": "telegram",
            "sender_id": "unknown999",
            "sender": "stranger",
            "channel_id": "-100123",
            "message": "hello",
        }

        result = asyncio.run(plugin.on_message_received(ctx))
        assert result.get("abort") is True

    def test_unauthorized_creates_pending(self, plugin):
        """Test unauthorized user gets pending request."""
        ctx = {
            "channel_type": "telegram",
            "sender_id": "unknown999",
            "sender": "stranger",
            "channel_id": "-100123",
            "message": "hello",
        }

        asyncio.run(plugin.on_message_received(ctx))

        req = plugin._storage.get_pending_for_user("telegram", "unknown999")
        assert req is not None
        assert req.name == "stranger"

    def test_disabled_allows_all(self, tmp_path):
        """Test disabled plugin allows all users."""
        plugin = PairingPlugin()
        plugin.configure({"pairing": {"enabled": False}})
        asyncio.run(plugin.start())

        ctx = {
            "channel_type": "telegram",
            "sender_id": "anyone",
            "message": "hello",
        }

        result = asyncio.run(plugin.on_message_received(ctx))
        assert "abort" not in result or not result["abort"]
