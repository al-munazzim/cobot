"""Tests for wallet plugin."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from cobot.plugins.wallet.plugin import WalletPlugin, create_plugin
from cobot.plugins.interfaces import WalletError


class TestWalletPlugin:
    """Test WalletPlugin with mocked subprocess."""

    @pytest.fixture
    def plugin(self):
        p = create_plugin()
        p.configure({"skills_path": "/fake/skills"})
        return p

    def test_create_plugin(self):
        plugin = create_plugin()
        assert isinstance(plugin, WalletPlugin)

    def test_plugin_meta(self):
        plugin = create_plugin()
        assert plugin.meta.id == "wallet"
        assert "wallet" in plugin.meta.capabilities

    def test_get_balance(self, plugin):
        balance_output = """Checking balance for npub1abc...

💰 Pending balance: 1234 sats"""

        with (
            patch("subprocess.run") as mock_run,
            patch.object(Path, "exists", return_value=True),
        ):
            mock_run.return_value = Mock(returncode=0, stdout=balance_output, stderr="")

            balance = plugin.get_balance()
            assert balance == 1234

    def test_get_balance_zero(self, plugin):
        balance_output = "💰 Pending balance: 0 sats"

        with (
            patch("subprocess.run") as mock_run,
            patch.object(Path, "exists", return_value=True),
        ):
            mock_run.return_value = Mock(returncode=0, stdout=balance_output, stderr="")

            balance = plugin.get_balance()
            assert balance == 0

    def test_pay_success(self, plugin):
        with (
            patch("subprocess.run") as mock_run,
            patch.object(Path, "exists", return_value=True),
        ):
            mock_run.return_value = Mock(
                returncode=0, stdout="Payment successful", stderr=""
            )

            result = plugin.pay("lnbc1...")
            assert result["success"] is True

    def test_pay_failure(self, plugin):
        with (
            patch("subprocess.run") as mock_run,
            patch.object(Path, "exists", return_value=True),
        ):
            mock_run.return_value = Mock(
                returncode=1, stdout="", stderr="Insufficient balance"
            )

            result = plugin.pay("lnbc1...")
            assert result["success"] is False
            assert "error" in result

    def test_get_receive_address(self, plugin):
        info_output = """Wallet Info:
Lightning address: npub1abc@npub.cash
"""

        with (
            patch("subprocess.run") as mock_run,
            patch.object(Path, "exists", return_value=True),
        ):
            mock_run.return_value = Mock(returncode=0, stdout=info_output, stderr="")

            address = plugin.get_receive_address()
            assert address == "npub1abc@npub.cash"

    def test_script_not_found(self, plugin):
        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(WalletError) as exc_info:
                plugin.get_balance()
            assert "not found" in str(exc_info.value).lower()

    def test_script_timeout(self, plugin):
        import subprocess

        with (
            patch("subprocess.run") as mock_run,
            patch.object(Path, "exists", return_value=True),
        ):
            mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)

            with pytest.raises(WalletError) as exc_info:
                plugin.get_balance()
            assert "timed out" in str(exc_info.value).lower()


class TestWalletPluginConfigure:
    """Test WalletPlugin configuration."""

    def test_configure_sets_scripts_dir(self):
        plugin = create_plugin()
        plugin.configure({"paths": {"skills": "/custom/skills"}})

        assert plugin._scripts_dir == Path("/custom/skills/npubcash/scripts")

    def test_default_scripts_path(self):
        plugin = create_plugin()
        plugin.configure({"paths": {}})

        # Default path when not configured
        assert "npubcash/scripts" in str(plugin._scripts_dir)
