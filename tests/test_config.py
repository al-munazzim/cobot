"""Tests for config plugin."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from cobot.plugins.config.plugin import CobotConfig, ConfigPlugin, create_plugin


class TestCobotConfigDefaults:
    """Test default configuration values."""

    def test_default_config_creates(self):
        config = CobotConfig()
        assert config.identity_name == "Cobot"
        assert config.polling_interval == 30
        assert config.provider == "ppq"

    def test_default_exec_config(self):
        config = CobotConfig()
        assert config.exec_enabled is True
        assert config.exec_allowlist == []
        assert config.exec_blocklist == []
        assert config.exec_timeout == 30

    def test_default_paths(self):
        config = CobotConfig()
        assert config.plugins_path == Path("./cobot/plugins")
        assert config.soul_path == Path("./SOUL.md")


class TestCobotConfigFromDict:
    """Test CobotConfig.from_dict() method."""

    def test_from_empty_dict(self):
        config = CobotConfig.from_dict({})
        assert config.identity_name == "Cobot"

    def test_from_partial_dict(self):
        data = {
            "identity": {"name": "TestBot"},
            "polling": {"interval_seconds": 60},
        }
        config = CobotConfig.from_dict(data)
        assert config.identity_name == "TestBot"
        assert config.polling_interval == 60
        assert config.provider == "ppq"  # Default

    def test_exec_config_from_dict(self):
        data = {
            "exec": {
                "enabled": False,
                "blocklist": ["rm -rf", "sudo"],
                "timeout": 10,
            }
        }
        config = CobotConfig.from_dict(data)
        assert config.exec_enabled is False
        assert "rm -rf" in config.exec_blocklist
        assert config.exec_timeout == 10

    def test_provider_from_dict(self):
        data = {"provider": "ollama"}
        config = CobotConfig.from_dict(data)
        assert config.provider == "ollama"

    def test_env_var_expansion(self):
        os.environ["TEST_VAR"] = "test_value"
        try:
            data = {"identity": {"name": "${TEST_VAR}"}}
            config = CobotConfig.from_dict(data)
            assert config.identity_name == "test_value"
        finally:
            del os.environ["TEST_VAR"]

    def test_env_var_default(self):
        data = {"identity": {"name": "${NONEXISTENT_VAR:-DefaultName}"}}
        config = CobotConfig.from_dict(data)
        assert config.identity_name == "DefaultName"


class TestCobotConfigLoad:
    """Test loading config from YAML files."""

    def test_load_from_yaml_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(
                {
                    "identity": {"name": "FileBot"},
                    "polling": {"interval_seconds": 15},
                },
                f,
            )
            f.flush()

            try:
                config = CobotConfig.load(Path(f.name))
                assert config.identity_name == "FileBot"
                assert config.polling_interval == 15
            finally:
                os.unlink(f.name)

    def test_get_plugin_config(self):
        data = {
            "ppq": {"api_key": "test-key", "model": "gpt-5"},
            "nostr": {"relays": ["wss://relay.example.com"]},
        }
        config = CobotConfig.from_dict(data)

        ppq_config = config.get_plugin_config("ppq")
        assert ppq_config["api_key"] == "test-key"
        assert ppq_config["model"] == "gpt-5"

        nostr_config = config.get_plugin_config("nostr")
        assert "wss://relay.example.com" in nostr_config["relays"]


class TestConfigPlugin:
    """Test ConfigPlugin class."""

    def test_create_plugin(self):
        plugin = create_plugin()
        assert isinstance(plugin, ConfigPlugin)

    def test_plugin_meta(self):
        plugin = create_plugin()
        assert plugin.meta.id == "config"
        assert plugin.meta.priority == 1
        assert "config" in plugin.meta.capabilities

    def test_configure_and_get_config(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"identity": {"name": "TestBot"}}, f)
            f.flush()

            try:
                # Change to temp dir so plugin finds config
                old_cwd = os.getcwd()
                os.chdir(Path(f.name).parent)

                # Rename to cobot.yml
                temp_config = Path("cobot.yml")
                Path(f.name).rename(temp_config)

                plugin = create_plugin()
                plugin.configure({})

                config = plugin.get_config()
                assert config.identity_name == "TestBot"
            finally:
                if temp_config.exists():
                    temp_config.unlink()
                os.chdir(old_cwd)
