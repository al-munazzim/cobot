# Quick Start Guide

Get Cobot running in 5 minutes.

## Prerequisites

- Python 3.11 or higher
- An LLM API key (PPQ, OpenRouter, or local Ollama)

## Step 1: Install

```bash
# Clone the repository
git clone https://github.com/ultanio/cobot
cd cobot

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install
pip install -e .
```

## Step 2: Configure

```bash
# Copy example config
cp cobot.yml.example cobot.yml
```

Edit `cobot.yml`:

```yaml
provider: ppq

identity:
  name: "MyCobot"

ppq:
  api_key: "${PPQ_API_KEY}"
  model: "gpt-4o"

exec:
  enabled: true
  timeout: 30
```

Set your API key:

```bash
export PPQ_API_KEY="your-api-key-here"
```

## Step 3: Set Up User Authorization (Optional)

If you're exposing your bot on Telegram or other channels, configure pairing to control who can interact:

```yaml
# In cobot.yml
pairing:
  enabled: true
  owner_ids:
    telegram: ["your-telegram-user-id"]
  # skip_channels: ["nostr"]  # Optional: skip auth for specific channels
```

Unknown users will receive a pairing code. Approve them with:

```bash
cobot pairing approve <code>
```

See all pending/approved users:

```bash
cobot pairing list
```

## Step 4: Run

```bash
# Interactive mode (recommended for first run)
cobot run --stdin
```

You should see:

```
[Config] Provider: ppq
[Registry] Started 'config'
[Registry] Started 'ppq'
[Registry] Started 'tools'
Loaded plugins
Identity: MyCobot

> 
```

Try sending a message:

```
> Hello! What can you do?
```

## Step 5: Explore

### Check Status

```bash
cobot status
```

### Run as Daemon

```bash
# Start in background
cobot run &

# Or use the PID file
cobot status  # Shows PID if running
cobot restart # Restart running instance
```

### Add Plugins

Create a plugin directory:

```bash
mkdir -p plugins/hello
```

Create `plugins/hello/plugin.py`:

```python
from cobot.plugins.base import Plugin, PluginMeta

class HelloPlugin(Plugin):
    meta = PluginMeta(
        id="hello",
        version="1.0.0",
        capabilities=[],
        dependencies=[],
        priority=50,
    )
    
    def configure(self, config: dict) -> None:
        pass
    
    def start(self) -> None:
        print("[Hello] World!")
    
    def stop(self) -> None:
        pass

def create_plugin():
    return HelloPlugin()
```

Restart Cobot — your plugin will be loaded automatically.

## Next Steps

1. **Add Nostr identity** — See [Nostr Setup](nostr.md)
2. **Add Lightning wallet** — See [Wallet Setup](wallet.md)
3. **Create custom plugins** — See [Plugin Development](../CONTRIBUTING.md#plugin-development)
4. **Understand architecture** — See [Architecture](architecture.md)

## Common Issues

### "No LLM configured"

Make sure your API key is set:

```bash
echo $PPQ_API_KEY  # Should show your key
```

### Plugin not loading

Check the plugin path:

```bash
ls -la plugins/  # Should show your plugin directory
```

### Permission denied

Check file permissions:

```bash
chmod +x cobot/cli.py
```

## Getting Help

- [GitHub Issues](https://github.com/ultanio/cobot/issues)
- [Architecture Docs](architecture.md)
- [Contributing Guide](../CONTRIBUTING.md)
