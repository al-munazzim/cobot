"""Config plugin exports for backward compatibility."""

from .plugin import (
    CobotConfig,
    ConfigPlugin,
    create_plugin,
    _expand_env_vars,
)

# Backward compatibility aliases
Config = CobotConfig


def load_config():
    """Load config using the plugin."""
    from pathlib import Path
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
