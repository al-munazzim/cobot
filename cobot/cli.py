"""Cobot CLI - command line interface for the agent."""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click


# --- Config Utilities ---


def get_config_paths() -> tuple[Path, Path]:
    """Get home and local config paths."""
    home_config = Path.home() / ".cobot" / "config.yaml"
    local_config = Path("config.yaml")
    return home_config, local_config


def load_merged_config():
    """Load config with local overriding home."""
    from cobot.plugins.config import load_config

    return load_config()


# --- PID File ---


def get_pid_file() -> Path:
    """Get path to PID file."""
    return Path.home() / ".cobot" / "cobot.pid"


def read_pid() -> Optional[int]:
    """Read PID from file, return None if not found or stale."""
    pid_file = get_pid_file()
    if not pid_file.exists():
        return None

    try:
        pid = int(pid_file.read_text().strip())
        # Check if process exists
        os.kill(pid, 0)
        return pid
    except (ValueError, ProcessLookupError, PermissionError):
        return None


def write_pid(pid: int) -> None:
    """Write PID to file."""
    pid_file = get_pid_file()
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(pid))


def remove_pid() -> None:
    """Remove PID file."""
    pid_file = get_pid_file()
    if pid_file.exists():
        pid_file.unlink()


# --- CLI Groups ---


@click.group()
@click.version_option(version="0.1.0", prog_name="cobot")
def cli():
    """Cobot - Minimal self-sovereign AI agent."""
    pass


# --- Core Commands ---


@cli.command()
@click.option("--config", "-c", type=click.Path(exists=True), help="Config file path")
@click.option("--stdin", is_flag=True, help="Run in stdin mode (no Nostr)")
@click.option("--plugins", "-p", type=click.Path(exists=True), help="Plugins directory")
def run(config: Optional[str], stdin: bool, plugins: Optional[str]):
    """Start the cobot agent."""
    # Check if already running
    existing_pid = read_pid()
    if existing_pid:
        click.echo(f"Cobot already running (PID {existing_pid})", err=True)
        click.echo("Use 'nano restart' to restart or kill the process first.", err=True)
        sys.exit(1)

    # Write our PID
    write_pid(os.getpid())

    try:
        from cobot import plugins as plugin_system
        from cobot.agent import Cobot
        import yaml

        # Load config file first (for plugin filtering)
        config_path = Path(config) if config else Path("cobot.yml")
        raw_config = {}
        if config_path.exists():
            with open(config_path) as f:
                raw_config = yaml.safe_load(f) or {}

        # Load plugins with config
        plugins_dir = Path(plugins) if plugins else Path("cobot/plugins")
        if plugins_dir.exists():
            registry = plugin_system.init_plugins(plugins_dir, config=raw_config)
            click.echo(f"Loaded {registry} plugin(s)", err=True)
        else:
            registry = plugin_system.get_registry()

        # Get config from plugin
        from cobot.plugins.config import get_config

        cfg = get_config()

        # Check API key from env or config
        ppq_config = cfg._raw.get("ppq", {})
        api_key = ppq_config.get("api_key") or os.environ.get("PPQ_API_KEY")
        if cfg.provider == "ppq" and not api_key:
            click.echo("Error: PPQ_API_KEY not set", err=True)
            sys.exit(1)

        bot = Cobot(registry)

        # Set up restart signal handler
        def handle_restart(signum, frame):
            click.echo("\nRestart signal received, restarting...", err=True)
            remove_pid()
            os.execv(sys.executable, [sys.executable] + sys.argv)

        signal.signal(signal.SIGUSR1, handle_restart)

        if stdin:
            bot.run_stdin()
        else:
            bot.run_loop()
    finally:
        remove_pid()


@cli.command()
def restart():
    """Restart the running cobot agent."""
    pid = read_pid()
    if not pid:
        click.echo("Cobot is not running.", err=True)
        sys.exit(1)

    try:
        os.kill(pid, signal.SIGUSR1)
        click.echo(f"Restart signal sent to PID {pid}")
    except ProcessLookupError:
        click.echo("Process not found, removing stale PID file.", err=True)
        remove_pid()
        sys.exit(1)


@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def status(as_json: bool):
    """Show cobot status."""
    pid = read_pid()

    status_data = {
        "running": pid is not None,
        "pid": pid,
    }

    if pid:
        # Get process info
        try:
            import time

            stat_file = Path(f"/proc/{pid}/stat")
            if stat_file.exists():
                # Get start time from /proc
                stat = stat_file.read_text().split()
                # Field 22 is starttime in clock ticks
                starttime_ticks = int(stat[21])
                clock_ticks = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
                uptime_file = Path("/proc/uptime")
                system_uptime = float(uptime_file.read_text().split()[0])
                process_start = system_uptime - (starttime_ticks / clock_ticks)
                status_data["uptime_seconds"] = int(
                    time.time() - (time.time() - process_start)
                )
        except Exception:
            status_data["uptime_seconds"] = None

        # Try to get wallet balance
        try:
            from cobot.plugins.config import load_config
            from cobot.plugins.wallet import Wallet

            config = load_config()
            wallet = Wallet(Path(config.paths.skills))
            status_data["wallet_balance"] = wallet.get_balance()
        except Exception:
            status_data["wallet_balance"] = None

    if as_json:
        click.echo(json.dumps(status_data, indent=2))
    else:
        click.echo("Cobot Status")
        click.echo("──────────────")
        if status_data["running"]:
            click.echo(f"State:    Running (PID {status_data['pid']})")
            if status_data.get("uptime_seconds"):
                hours, rem = divmod(status_data["uptime_seconds"], 3600)
                mins, secs = divmod(rem, 60)
                click.echo(f"Uptime:   {hours}h {mins}m")
            if status_data.get("wallet_balance") is not None:
                click.echo(f"Wallet:   {status_data['wallet_balance']:,} sats")
        else:
            click.echo("State:    Not running")


# --- Wallet Commands ---


@cli.group()
def wallet():
    """Wallet commands."""
    pass


@wallet.command("balance")
def wallet_balance():
    """Check wallet balance."""
    try:
        from cobot.plugins.config import load_config
        from cobot.plugins.wallet import Wallet

        config = load_config()
        w = Wallet(Path(config.paths.skills))
        balance = w.get_balance()
        click.echo(f"Balance: {balance:,} sats")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@wallet.command("address")
def wallet_address():
    """Show Lightning address."""
    try:
        from cobot.plugins.config import load_config
        from cobot.plugins.wallet import Wallet

        config = load_config()
        w = Wallet(Path(config.paths.skills))
        address = w.get_lightning_address()
        click.echo(f"Lightning address: {address}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@wallet.command("pay")
@click.argument("invoice")
def wallet_pay(invoice: str):
    """Pay a Lightning invoice."""
    try:
        from cobot.plugins.config import load_config
        from cobot.plugins.wallet import Wallet

        config = load_config()
        w = Wallet(Path(config.paths.skills))
        result = w.pay_invoice(invoice)
        if result.get("success"):
            click.echo("Payment successful!")
        else:
            click.echo(f"Payment failed: {result.get('error')}", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# --- DM Commands ---


@cli.command("dm")
@click.argument("npub")
@click.argument("message")
def send_dm(npub: str, message: str):
    """Send a DM to an npub."""
    try:
        from cobot.plugins.config import load_config
        from cobot.plugins.nostr import NostrClient

        config = load_config()
        client = NostrClient(Path(config.paths.skills))
        event_id = client.send_dm(npub, message)
        click.echo(f"Sent! Event ID: {event_id}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("dms")
@click.option("--since", default="1h", help="Time window (e.g., 1h, 30m, 1d)")
def list_dms(since: str):
    """List recent DMs."""
    # Parse time
    minutes = 60  # default 1h
    if since.endswith("m"):
        minutes = int(since[:-1])
    elif since.endswith("h"):
        minutes = int(since[:-1]) * 60
    elif since.endswith("d"):
        minutes = int(since[:-1]) * 1440

    try:
        from cobot.plugins.config import load_config
        from cobot.plugins.nostr import NostrClient

        config = load_config()
        client = NostrClient(Path(config.paths.skills))
        client.get_identity()  # Populate own pubkey
        messages = client.check_dms(since_minutes=minutes)

        if not messages:
            click.echo("No messages.")
            return

        for msg in messages:
            sender_short = msg.sender[:16] + "..."
            content_short = msg.content[:50] + ("..." if len(msg.content) > 50 else "")
            click.echo(f"[{sender_short}] {content_short}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# --- Config Commands ---


@cli.group()
def config():
    """Configuration commands."""
    pass


@config.command("show")
def config_show():
    """Show current configuration."""
    cfg = load_merged_config()

    click.echo("Identity:")
    click.echo(f"  name: {cfg.identity_name}")
    click.echo("\nPolling:")
    click.echo(f"  interval: {cfg.polling_interval}s")
    click.echo("\nProvider:")
    click.echo(f"  provider: {cfg.provider}")
    click.echo("\nPaths:")
    click.echo(f"  skills: {cfg.skills_path}")
    click.echo(f"  plugins: {cfg.plugins_path}")
    click.echo(f"  memory: {cfg.memory_path}")
    click.echo("\nExec:")
    click.echo(f"  enabled: {cfg.exec_enabled}")


@config.command("edit")
def config_edit():
    """Edit local config in $EDITOR."""
    editor = os.environ.get("EDITOR", "nano")
    config_path = Path("config.yaml")

    if not config_path.exists():
        # Create default config
        config_path.write_text("""# Cobot Configuration

identity:
  name: "Cobot"

polling:
  interval_seconds: 30

inference:
  model: "gpt-5-nano"
""")

    subprocess.run([editor, str(config_path)])


@config.command("validate")
def config_validate():
    """Validate configuration."""
    try:
        cfg = load_merged_config()
        errors = []

        # Check provider-specific requirements
        if cfg.provider == "ppq":
            import os

            ppq_config = cfg.get_plugin_config("ppq")
            if not ppq_config.get("api_key") and not os.environ.get("PPQ_API_KEY"):
                errors.append("PPQ_API_KEY not set (required when provider=ppq)")

        if cfg.polling_interval < 5:
            errors.append("Polling interval too short (min 5s)")

        if errors:
            click.echo("Configuration errors:", err=True)
            for err in errors:
                click.echo(f"  - {err}", err=True)
            sys.exit(1)
        else:
            click.echo("Configuration is valid ✓")
    except Exception as e:
        click.echo(f"Error loading config: {e}", err=True)
        sys.exit(1)


# --- Dev Commands ---


@cli.command("test")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def run_tests(verbose: bool):
    """Run test suite."""
    cmd = [sys.executable, "-m", "pytest", "tests/"]
    if verbose:
        cmd.append("-v")
    subprocess.run(cmd)


def register_plugin_commands():
    """Load plugins and let them register CLI commands."""
    try:
        from cobot.plugins import init_plugins, get_registry

        # Try to initialize plugins (may fail if no config)
        try:
            init_plugins()
        except Exception:
            pass  # Config may not exist yet

        registry = get_registry()
        if registry:
            for plugin in registry.all_plugins():
                try:
                    plugin.register_commands(cli)
                except Exception as e:
                    # Don't fail CLI if plugin command registration fails
                    click.echo(
                        f"Warning: Plugin {plugin.meta.id} command registration failed: {e}",
                        err=True,
                    )
    except Exception:
        pass  # Plugins not available


# --- Setup Wizard (Core) ---


@cli.group()
def wizard():
    """Setup wizard and plugin configuration."""
    pass


@wizard.command()
@click.option(
    "--non-interactive", "-y", is_flag=True, help="Use defaults, don't prompt"
)
def init(non_interactive: bool):
    """Initialize cobot configuration.

    Interactive wizard to set up cobot.yml with plugins and credentials.
    Plugins can extend the wizard via wizard_section() and wizard_configure().
    """
    import yaml

    config_path = Path("cobot.yml")

    if config_path.exists() and not non_interactive:
        if not click.confirm("cobot.yml already exists. Overwrite?"):
            click.echo("Aborted.")
            return

    click.echo("\n🤖 Cobot Setup Wizard\n")

    # --- Core Configuration (always present) ---

    config = {
        "provider": "ppq",
        "identity": {"name": "MyAgent"},
    }

    if non_interactive:
        # Use defaults for core config
        config["ppq"] = {
            "api_base": "https://api.ppq.ai/v1",
            # api_key from PPQ_API_KEY env var
            "model": "openai/gpt-4o",
        }
        config["exec"] = {"enabled": True, "timeout": 30}
    else:
        # Interactive core setup

        # Identity
        click.echo("📛 Identity\n")
        name = click.prompt("Agent name", default="MyAgent")
        config["identity"]["name"] = name

        # Provider
        click.echo("\n🧠 LLM Provider\n")
        provider = click.prompt(
            "Provider", type=click.Choice(["ppq", "ollama"]), default="ppq"
        )
        config["provider"] = provider

        if provider == "ppq":
            click.echo("\n  PPQ Configuration (api.ppq.ai)")
            api_key = click.prompt(
                "  API key (or use env var)",
                default="${PPQ_API_KEY}",
                show_default=True,
            )
            model = click.prompt("  Model", default="openai/gpt-4o")
            config["ppq"] = {
                "api_base": "https://api.ppq.ai/v1",
                # Note: ${VAR} doesn't expand in YAML - use env var directly or set value
                "model": model,
            }
            if api_key != "${PPQ_API_KEY}":
                config["ppq"]["api_key"] = api_key
        else:
            click.echo("\n  Ollama Configuration (local)")
            base_url = click.prompt("  URL", default="http://localhost:11434")
            model = click.prompt("  Model", default="qwen2.5:7b")
            config["ollama"] = {
                "base_url": base_url,
                "model": model,
            }

        # Tool execution
        click.echo("\n🔧 Tool Execution\n")
        exec_enabled = click.confirm("Enable shell command execution?", default=True)
        config["exec"] = {
            "enabled": exec_enabled,
            "timeout": 30,
        }

    # --- Plugin Configuration (via extension points) ---

    if not non_interactive:
        try:
            from cobot.plugins import get_registry

            registry = get_registry()
            if registry:
                wizard_plugins = []

                # Discover plugins that participate in wizard
                for plugin in registry.all_plugins():
                    try:
                        section = plugin.wizard_section()
                        if section:
                            wizard_plugins.append((plugin, section))
                    except Exception:
                        pass

                if wizard_plugins:
                    click.echo("\n🔌 Plugins\n")

                    for plugin, section in wizard_plugins:
                        key = section.get("key", plugin.meta.id)
                        name = section.get("name", plugin.meta.id)
                        desc = section.get("description", "")

                        prompt_text = f"Configure {name}?"
                        if desc:
                            prompt_text = f"Configure {name} ({desc})?"

                        if click.confirm(prompt_text, default=False):
                            try:
                                plugin_config = plugin.wizard_configure(config)
                                if plugin_config:
                                    config[key] = plugin_config
                                    click.echo(f"  ✓ {name} configured\n")
                            except Exception as e:
                                click.echo(
                                    f"  ✗ Error configuring {name}: {e}\n", err=True
                                )

        except Exception:
            # Plugins not available, skip plugin configuration
            pass

    # --- Write Configuration ---

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    click.echo(f"\n✅ Configuration written to {config_path}")
    click.echo("\nNext steps:")
    click.echo("  1. Review and edit cobot.yml")
    click.echo("  2. Set environment variables (PPQ_API_KEY, etc.)")
    click.echo("  3. Run: cobot run")


@wizard.command()
def plugins():
    """List available plugins and their wizard sections."""
    try:
        from cobot.plugins import init_plugins, get_registry
        from pathlib import Path

        try:
            plugins_dir = Path(__file__).parent / "plugins"
            init_plugins(plugins_dir)
        except Exception as e:
            click.echo(f"Note: Could not fully initialize plugins: {e}", err=True)

        registry = get_registry()
        if not registry:
            click.echo("No plugin registry available.")
            return

        click.echo("\n📦 Plugins:\n")

        for plugin in registry.all_plugins():
            meta = plugin.meta
            caps = ", ".join(meta.capabilities) if meta.capabilities else "none"
            click.echo(f"  {meta.id} v{meta.version}")
            click.echo(f"    Capabilities: {caps}")
            if meta.extension_points:
                click.echo(f"    Extension points: {', '.join(meta.extension_points)}")

            # Show wizard section if available
            try:
                section = plugin.wizard_section()
                if section:
                    name = section.get("name", meta.id)
                    desc = section.get("description", "")
                    click.echo(f"    Wizard: {name}" + (f" - {desc}" if desc else ""))
            except Exception:
                pass

            click.echo()

    except Exception as e:
        click.echo(f"Error listing plugins: {e}", err=True)


def main():
    """Entry point."""
    # Let plugins register their commands
    register_plugin_commands()

    # Run CLI
    cli()


if __name__ == "__main__":
    main()
