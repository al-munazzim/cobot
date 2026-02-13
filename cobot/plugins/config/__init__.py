"""Config plugin exports for backward compatibility."""

from .plugin import (
    CobotConfig,
    ConfigPlugin,
    create_plugin,
)

__all__ = ["CobotConfig", "ConfigPlugin", "create_plugin", "Config", "load_config"]

# Backward compatibility aliases
Config = CobotConfig


def load_config():
    """Load config using the plugin."""
    plugin = create_plugin()
    plugin.configure({})
    return plugin.get_config()


def get_config():
    """Get config (alias for load_config)."""
    return load_config()


__all__ = [
    "CobotConfig",
    "Config",
    "ConfigPlugin",
    "create_plugin",
    "load_config",
    "get_config",
]
