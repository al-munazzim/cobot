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
    extension_points: list[str] = field(
        default_factory=list
    )  # Extension points this plugin defines: ["context.system_prompt"]
    implements: dict[str, str] = field(
        default_factory=dict
    )  # Extension points this plugin implements: {"context.system_prompt": "get_soul"}

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

    # --- Setup Wizard Extension ---

    def wizard_section(self) -> dict | None:
        """Return wizard section info for this plugin.

        If the plugin wants to participate in the setup wizard, return
        a dict describing the section. Return None to skip.

        Returns:
            dict with keys:
                - key: Config key (e.g., "telegram")
                - name: Display name (e.g., "Telegram")
                - description: Short description
            or None to not participate in wizard

        Example:
            def wizard_section(self):
                return {
                    "key": "telegram",
                    "name": "Telegram",
                    "description": "Multi-group logging and archival"
                }
        """
        return None

    def wizard_configure(self, config: dict) -> dict:
        """Interactive configuration for the setup wizard.

        Called when user chooses to configure this plugin in the wizard.
        Use click.prompt/confirm/echo for user interaction.

        Args:
            config: Configuration dict built so far (identity, provider, etc.)

        Returns:
            Configuration dict for this plugin's section

        Example:
            def wizard_configure(self, config: dict) -> dict:
                import click

                agent_name = config.get("identity", {}).get("name", "Agent")
                click.echo(f"Setting up Telegram for {agent_name}")

                token = click.prompt("Bot token", default="${TELEGRAM_BOT_TOKEN}")

                groups = []
                while click.confirm("Add a group?", default=len(groups) == 0):
                    group_id = click.prompt("Group ID", type=int)
                    group_name = click.prompt("Group name")
                    groups.append({"id": group_id, "name": group_name})

                return {
                    "bot_token": token,
                    "groups": groups,
                }
        """
        return {}


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
