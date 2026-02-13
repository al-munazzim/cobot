"""Plugin base class and metadata.

All plugins must inherit from Plugin and define a PluginMeta.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class PluginMeta:
    """Plugin metadata - defines identity and capabilities."""

    id: str  # Unique identifier: "ppq", "ollama", "nostr"
    version: str  # Semver: "1.0.0"
    capabilities: list[str] = field(default_factory=list)  # What it provides: ["llm"]
    dependencies: list[str] = field(
        default_factory=list
    )  # Required plugins: ["config"]
    priority: int = 50  # Load order (lower = earlier)

    def __post_init__(self):
        if not self.id:
            raise ValueError("Plugin id is required")
        if not self.version:
            raise ValueError("Plugin version is required")


class Plugin(ABC):
    """Base class for all plugins.

    Plugins must:
    1. Define a `meta` class attribute with PluginMeta
    2. Implement configure(), start(), stop()
    3. Optionally implement hook methods (on_message_received, etc.)
    4. Optionally implement capability interfaces (LLMProvider, etc.)

    Example:
        class MyPlugin(Plugin):
            meta = PluginMeta(
                id="myplugin",
                version="1.0.0",
                capabilities=["llm"],
                dependencies=["config"],
                priority=20,
            )

            def configure(self, config: dict) -> None:
                self._config = config

            def start(self) -> None:
                # Initialize resources
                pass

            def stop(self) -> None:
                # Clean up
                pass
    """

    meta: PluginMeta  # Must be defined by subclass

    @abstractmethod
    def configure(self, config: dict) -> None:
        """Receive plugin-specific configuration.

        Called before start(). Config is the plugin's section from cobot.yml.

        Args:
            config: Plugin-specific config dict (may be empty)
        """
        pass

    @abstractmethod
    def start(self) -> None:
        """Initialize the plugin.

        Called after all plugins are configured, in dependency order.
        Initialize clients, connections, etc. here.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Clean up plugin resources.

        Called on shutdown, in reverse dependency order.
        Close connections, release resources, etc.
        """
        pass

    # --- Optional Hook Methods ---
    # Override these to handle lifecycle events

    def on_message_received(self, ctx: dict) -> dict:
        """Called when a message is received."""
        return ctx

    def transform_system_prompt(self, ctx: dict) -> dict:
        """Called to transform the system prompt."""
        return ctx

    def transform_history(self, ctx: dict) -> dict:
        """Called to transform conversation history."""
        return ctx

    def on_before_llm_call(self, ctx: dict) -> dict:
        """Called before LLM inference."""
        return ctx

    def on_after_llm_call(self, ctx: dict) -> dict:
        """Called after LLM inference."""
        return ctx

    def on_before_tool_exec(self, ctx: dict) -> dict:
        """Called before tool execution."""
        return ctx

    def on_after_tool_exec(self, ctx: dict) -> dict:
        """Called after tool execution."""
        return ctx

    def transform_response(self, ctx: dict) -> dict:
        """Called to transform the response before sending."""
        return ctx

    def on_before_send(self, ctx: dict) -> dict:
        """Called before sending a message."""
        return ctx

    def on_after_send(self, ctx: dict) -> dict:
        """Called after sending a message."""
        return ctx

    def on_error(self, ctx: dict) -> dict:
        """Called when an error occurs."""
        return ctx

    # --- CLI Extension ---

    def register_commands(self, cli) -> None:
        """Register CLI commands.

        Called during CLI initialization. Plugins can add commands/groups
        to the main CLI.

        Args:
            cli: Click group (the main cobot CLI)

        Example:
            def register_commands(self, cli):
                @cli.command()
                def my_command():
                    '''My plugin command.'''
                    click.echo("Hello from plugin!")
        """
        pass


# List of all hook method names
HOOK_METHODS = [
    "on_message_received",
    "transform_system_prompt",
    "transform_history",
    "on_before_llm_call",
    "on_after_llm_call",
    "on_before_tool_exec",
    "on_after_tool_exec",
    "transform_response",
    "on_before_send",
    "on_after_send",
    "on_error",
]
