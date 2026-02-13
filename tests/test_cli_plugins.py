"""Tests for plugin CLI extension functionality."""

from unittest.mock import Mock, patch
from click.testing import CliRunner

from cobot.plugins.base import Plugin, PluginMeta


class TestRegisterCommands:
    """Test the register_commands hook."""

    def test_plugin_has_register_commands_method(self):
        """Test that Plugin base class has register_commands."""
        assert hasattr(Plugin, "register_commands")

    def test_register_commands_default_does_nothing(self):
        """Test that default register_commands is a no-op."""

        class TestPlugin(Plugin):
            meta = PluginMeta(id="test", version="1.0.0")

            def configure(self, config):
                pass

            def start(self):
                pass

            def stop(self):
                pass

        plugin = TestPlugin()
        # Should not raise
        plugin.register_commands(Mock())

    def test_plugin_can_add_command(self):
        """Test that a plugin can add a CLI command."""
        import click

        @click.group()
        def test_cli():
            pass

        class CommandPlugin(Plugin):
            meta = PluginMeta(id="cmd", version="1.0.0")

            def configure(self, config):
                pass

            def start(self):
                pass

            def stop(self):
                pass

            def register_commands(self, cli):
                @cli.command()
                def hello():
                    """Say hello."""
                    click.echo("Hello from plugin!")

        plugin = CommandPlugin()
        plugin.register_commands(test_cli)

        # Verify command was added
        assert "hello" in test_cli.commands

        # Test command execution
        runner = CliRunner()
        result = runner.invoke(test_cli, ["hello"])
        assert result.exit_code == 0
        assert "Hello from plugin!" in result.output

    def test_plugin_can_add_group(self):
        """Test that a plugin can add a command group."""
        import click

        @click.group()
        def test_cli():
            pass

        class GroupPlugin(Plugin):
            meta = PluginMeta(id="grp", version="1.0.0")

            def configure(self, config):
                pass

            def start(self):
                pass

            def stop(self):
                pass

            def register_commands(self, cli):
                @cli.group()
                def mygroup():
                    """My plugin group."""
                    pass

                @mygroup.command()
                def subcommand():
                    """A subcommand."""
                    click.echo("Subcommand executed!")

        plugin = GroupPlugin()
        plugin.register_commands(test_cli)

        assert "mygroup" in test_cli.commands

        runner = CliRunner()
        result = runner.invoke(test_cli, ["mygroup", "subcommand"])
        assert result.exit_code == 0
        assert "Subcommand executed!" in result.output

    def test_plugin_command_with_options(self):
        """Test that plugin commands can have options."""
        import click

        @click.group()
        def test_cli():
            pass

        class OptionPlugin(Plugin):
            meta = PluginMeta(id="opt", version="1.0.0")

            def configure(self, config):
                pass

            def start(self):
                pass

            def stop(self):
                pass

            def register_commands(self, cli):
                @cli.command()
                @click.option("--name", "-n", default="World")
                @click.option("--count", "-c", default=1, type=int)
                def greet(name, count):
                    """Greet someone."""
                    for _ in range(count):
                        click.echo(f"Hello, {name}!")

        plugin = OptionPlugin()
        plugin.register_commands(test_cli)

        runner = CliRunner()

        # Default options
        result = runner.invoke(test_cli, ["greet"])
        assert "Hello, World!" in result.output

        # Custom options
        result = runner.invoke(test_cli, ["greet", "-n", "Alice", "-c", "3"])
        assert result.output.count("Hello, Alice!") == 3

    def test_multiple_plugins_register_commands(self):
        """Test that multiple plugins can register commands."""
        import click

        @click.group()
        def test_cli():
            pass

        class PluginA(Plugin):
            meta = PluginMeta(id="a", version="1.0.0")

            def configure(self, config):
                pass

            def start(self):
                pass

            def stop(self):
                pass

            def register_commands(self, cli):
                @cli.command()
                def cmd_a():
                    click.echo("Command A")

        class PluginB(Plugin):
            meta = PluginMeta(id="b", version="1.0.0")

            def configure(self, config):
                pass

            def start(self):
                pass

            def stop(self):
                pass

            def register_commands(self, cli):
                @cli.command()
                def cmd_b():
                    click.echo("Command B")

        PluginA().register_commands(test_cli)
        PluginB().register_commands(test_cli)

        assert "cmd-a" in test_cli.commands
        assert "cmd-b" in test_cli.commands

        runner = CliRunner()
        assert "Command A" in runner.invoke(test_cli, ["cmd-a"]).output
        assert "Command B" in runner.invoke(test_cli, ["cmd-b"]).output


class TestWizardGroup:
    """Test the wizard command group."""

    def test_wizard_group_exists(self):
        """Test that wizard group is registered."""
        from cobot.cli import cli

        assert "wizard" in cli.commands

    def test_wizard_init_exists(self):
        """Test that wizard init subcommand exists."""
        from cobot.cli import cli

        assert "init" in cli.commands["wizard"].commands

    def test_wizard_plugins_exists(self):
        """Test that wizard plugins subcommand exists."""
        from cobot.cli import cli

        assert "plugins" in cli.commands["wizard"].commands


class TestInitCommand:
    """Test the wizard init command."""

    def test_init_non_interactive(self, tmp_path):
        """Test non-interactive init creates config."""
        from cobot.cli import cli
        import os

        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["wizard", "init", "-y"])

            assert result.exit_code == 0
            assert "Configuration written" in result.output
            assert os.path.exists("cobot.yml")

            # Check config content
            import yaml

            with open("cobot.yml") as f:
                config = yaml.safe_load(f)

            assert config["provider"] == "ppq"
            assert "identity" in config
            assert "ppq" in config
            assert "exec" in config

    def test_init_does_not_overwrite_without_confirm(self, tmp_path):
        """Test that init doesn't overwrite without confirmation."""
        from cobot.cli import cli

        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create existing config
            with open("cobot.yml", "w") as f:
                f.write("existing: config\n")

            # Run init without confirmation
            result = runner.invoke(cli, ["wizard", "init"], input="n\n")

            assert "Aborted" in result.output

            # Check original config preserved
            with open("cobot.yml") as f:
                assert "existing" in f.read()


class TestWizardExtensionPoints:
    """Test wizard extension points for plugins."""

    def test_plugin_has_wizard_section_method(self):
        """Test that Plugin base class has wizard_section."""
        assert hasattr(Plugin, "wizard_section")

    def test_plugin_has_wizard_configure_method(self):
        """Test that Plugin base class has wizard_configure."""
        assert hasattr(Plugin, "wizard_configure")

    def test_wizard_section_default_returns_none(self):
        """Test that default wizard_section returns None."""

        class TestPlugin(Plugin):
            meta = PluginMeta(id="test", version="1.0.0")

            def configure(self, config):
                pass

            def start(self):
                pass

            def stop(self):
                pass

        plugin = TestPlugin()
        assert plugin.wizard_section() is None

    def test_wizard_configure_default_returns_empty(self):
        """Test that default wizard_configure returns empty dict."""

        class TestPlugin(Plugin):
            meta = PluginMeta(id="test", version="1.0.0")

            def configure(self, config):
                pass

            def start(self):
                pass

            def stop(self):
                pass

        plugin = TestPlugin()
        assert plugin.wizard_configure({}) == {}

    def test_plugin_can_implement_wizard_section(self):
        """Test that a plugin can implement wizard_section."""

        class WizardPlugin(Plugin):
            meta = PluginMeta(id="myplugin", version="1.0.0")

            def configure(self, config):
                pass

            def start(self):
                pass

            def stop(self):
                pass

            def wizard_section(self):
                return {
                    "key": "myplugin",
                    "name": "My Plugin",
                    "description": "Does cool stuff",
                }

        plugin = WizardPlugin()
        section = plugin.wizard_section()

        assert section is not None
        assert section["key"] == "myplugin"
        assert section["name"] == "My Plugin"
        assert section["description"] == "Does cool stuff"

    def test_plugin_can_implement_wizard_configure(self):
        """Test that a plugin can implement wizard_configure."""

        class WizardPlugin(Plugin):
            meta = PluginMeta(id="myplugin", version="1.0.0")

            def configure(self, config):
                pass

            def start(self):
                pass

            def stop(self):
                pass

            def wizard_section(self):
                return {"key": "myplugin", "name": "My Plugin"}

            def wizard_configure(self, config):
                # Can access existing config
                agent_name = config.get("identity", {}).get("name", "Agent")
                return {
                    "agent_name": agent_name,
                    "setting": "value",
                }

        plugin = WizardPlugin()
        result = plugin.wizard_configure({"identity": {"name": "TestBot"}})

        assert result["agent_name"] == "TestBot"
        assert result["setting"] == "value"

    def test_wizard_configure_receives_config(self):
        """Test that wizard_configure receives the config built so far."""

        received_config = {}

        class InspectorPlugin(Plugin):
            meta = PluginMeta(id="inspector", version="1.0.0")

            def configure(self, config):
                pass

            def start(self):
                pass

            def stop(self):
                pass

            def wizard_configure(self, config):
                nonlocal received_config
                received_config = config.copy()
                return {"inspected": True}

        plugin = InspectorPlugin()
        test_config = {
            "identity": {"name": "MyAgent"},
            "provider": "ppq",
            "ppq": {"model": "gpt-4o"},
        }

        plugin.wizard_configure(test_config)

        assert received_config["identity"]["name"] == "MyAgent"
        assert received_config["provider"] == "ppq"
        assert received_config["ppq"]["model"] == "gpt-4o"


class TestRegisterPluginCommands:
    """Test the register_plugin_commands function."""

    def test_register_plugin_commands_handles_errors(self):
        """Test that plugin command registration errors don't crash CLI."""
        from cobot.cli import register_plugin_commands

        # Should not raise even if plugins aren't available
        register_plugin_commands()

    @patch("cobot.plugins.get_registry")
    @patch("cobot.plugins.init_plugins")
    def test_calls_register_commands_on_plugins(self, mock_init, mock_registry):
        """Test that register_commands is called on each plugin."""
        from cobot.cli import register_plugin_commands, cli

        mock_plugin = Mock()
        mock_plugin.meta.id = "test"
        mock_registry.return_value.all_plugins.return_value = [mock_plugin]

        register_plugin_commands()

        mock_plugin.register_commands.assert_called_once_with(cli)

    @patch("cobot.plugins.get_registry")
    @patch("cobot.plugins.init_plugins")
    def test_continues_on_plugin_error(self, mock_init, mock_registry, capsys):
        """Test that one plugin error doesn't stop others."""
        from cobot.cli import register_plugin_commands

        bad_plugin = Mock()
        bad_plugin.meta.id = "bad"
        bad_plugin.register_commands.side_effect = Exception("Plugin error")

        good_plugin = Mock()
        good_plugin.meta.id = "good"

        mock_registry.return_value.all_plugins.return_value = [bad_plugin, good_plugin]

        register_plugin_commands()

        # Both should be called
        bad_plugin.register_commands.assert_called_once()
        good_plugin.register_commands.assert_called_once()

        # Warning should be printed
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "bad" in captured.err
