"""Plugin system for Cobot.

This module provides:
- Plugin base class and metadata (base.py)
- Capability interfaces (interfaces.py)
- Plugin registry (registry.py)

Plugins are discovered from plugin directories. Each plugin directory
must contain a plugin.py with a create_plugin() factory function.
"""

import importlib.util
import sys
from pathlib import Path

from .base import Plugin, PluginMeta, HOOK_METHODS
from .interfaces import (
    LLMProvider, LLMResponse, LLMError,
    CommunicationProvider, Message, CommunicationError,
    WalletProvider, WalletError,
    ToolProvider, ToolResult,
)
from .registry import PluginRegistry, PluginError, get_registry, reset_registry


def discover_plugins(plugins_dir: Path) -> list[type[Plugin]]:
    """Discover plugin classes from a directory.
    
    Each subdirectory with a plugin.py containing create_plugin() is loaded.
    
    Args:
        plugins_dir: Directory containing plugin subdirectories
    
    Returns:
        List of plugin classes
    """
    plugin_classes = []
    
    if not plugins_dir.exists():
        return plugin_classes
    
    for path in sorted(plugins_dir.iterdir()):
        if not path.is_dir():
            continue
        if path.name.startswith("_"):
            continue
        
        plugin_file = path / "plugin.py"
        if not plugin_file.exists():
            continue
        
        try:
            # Load the module
            module_name = f"cobot.plugins.{path.name}.plugin"
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if spec is None or spec.loader is None:
                continue
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Get the plugin class via factory
            create_plugin = getattr(module, "create_plugin", None)
            if create_plugin is None:
                print(f"[Plugins] Warning: {path.name}/plugin.py has no create_plugin()", file=sys.stderr)
                continue
            
            # Create instance to get class
            instance = create_plugin()
            plugin_classes.append(type(instance))
            
        except Exception as e:
            print(f"[Plugins] Failed to load {path.name}: {e}", file=sys.stderr)
    
    return plugin_classes


def init_plugins(plugins_dir: Path, config: dict = None) -> PluginRegistry:
    """Initialize the plugin system.
    
    1. Discover plugins from directory
    2. Filter based on config (provider selection, enabled/disabled)
    3. Register plugins
    4. Configure all plugins
    5. Start all plugins
    
    Args:
        plugins_dir: Directory containing plugin subdirectories
        config: Full configuration dict (from cobot.yml)
    
    Returns:
        Configured and started PluginRegistry
    """
    config = config or {}
    
    # Get provider selection
    provider = config.get("provider", "ppq")
    
    # Get explicit enable/disable lists
    plugins_config = config.get("plugins", {})
    enabled_list = plugins_config.get("enabled", [])
    disabled_list = plugins_config.get("disabled", [])
    
    # Get or create registry
    registry = get_registry()
    
    # Discover plugins
    plugin_classes = discover_plugins(plugins_dir)
    
    # Filter and register plugins
    for plugin_class in plugin_classes:
        plugin_id = plugin_class.meta.id
        
        # Skip if explicitly disabled
        if plugin_id in disabled_list:
            print(f"[Plugins] Skipping disabled plugin: {plugin_id}", file=sys.stderr)
            continue
        
        # Handle LLM provider selection - only load the configured one
        if "llm" in plugin_class.meta.capabilities:
            if plugin_id != provider:
                print(f"[Plugins] Skipping LLM provider: {plugin_id} (using {provider})", file=sys.stderr)
                continue
        
        # If enabled_list is specified, only load those plugins
        if enabled_list and plugin_id not in enabled_list:
            # But always load core plugins
            core_plugins = ["config", "logger", provider]
            if plugin_id not in core_plugins:
                print(f"[Plugins] Skipping non-enabled plugin: {plugin_id}", file=sys.stderr)
                continue
        
        try:
            registry.register(plugin_class)
        except PluginError as e:
            print(f"[Plugins] Failed to register: {e}", file=sys.stderr)
    
    # Configure all plugins
    registry.configure_all(config)
    
    # Start all plugins
    registry.start_all()
    
    # Give tools and compaction access to registry
    tools = registry.get("tools")
    if tools and hasattr(tools, "set_registry"):
        tools.set_registry(registry)
    
    compaction = registry.get("compaction")
    if compaction and hasattr(compaction, "set_registry"):
        compaction.set_registry(registry)
    
    return registry


# Convenience functions for hook execution
def run(hook_name: str, ctx: dict) -> dict:
    """Run a hook on all plugins."""
    return get_registry().run_hook(hook_name, ctx)


__all__ = [
    # Base
    "Plugin",
    "PluginMeta",
    "HOOK_METHODS",
    # Interfaces
    "LLMProvider",
    "LLMResponse", 
    "LLMError",
    "CommunicationProvider",
    "Message",
    "CommunicationError",
    "WalletProvider",
    "WalletError",
    "ToolProvider",
    "ToolResult",
    # Registry
    "PluginRegistry",
    "PluginError",
    "get_registry",
    "reset_registry",
    # Functions
    "discover_plugins",
    "init_plugins",
    "run",
]
