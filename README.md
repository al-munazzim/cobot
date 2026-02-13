# 🤖 Cobot

**Minimal self-sovereign AI agent with Nostr identity and Lightning wallet.**

Cobot is a lightweight personal AI agent that runs on your hardware, identifies via Nostr, and transacts via Lightning Network. Unlike cloud-hosted assistants or complex frameworks, Cobot gives you true ownership: *your keys, your identity, your agent*.

## ✨ Features

- **🪶 Minimal** — ~2K lines of Python, no bloat
- **🔌 Plugin Architecture** — Extensible via plugins with extension points
- **⚡ Lightning Wallet** — Send and receive sats autonomously
- **🔑 Nostr Identity** — Cryptographic identity via npub/nsec
- **🔥 Hot Reload** — Auto-restart on plugin changes
- **🤖 Multi-LLM** — PPQ, Ollama, OpenRouter, and more
- **📁 FileDrop** — File-based communication with Schnorr signatures

## 🚀 Quick Start

```bash
# Install
pip install cobot

# Or from source
git clone https://forgejo.tail593e12.ts.net/Zeus/cobot
cd cobot
pip install -e .

# Configure
cp cobot.yml.example cobot.yml
# Edit cobot.yml with your settings

# Run
cobot run
```

## 📋 Requirements

- Python 3.11+
- LLM API key (PPQ, OpenRouter, or local Ollama)

## ⚙️ Configuration

Create `cobot.yml`:

```yaml
# LLM Provider (ppq, ollama)
provider: ppq

identity:
  name: "MyAgent"

ppq:
  api_key: "${PPQ_API_KEY}"
  model: "gpt-4o"

# Optional: Nostr identity
nostr:
  relays:
    - "wss://relay.damus.io"
    - "wss://nos.lol"

# Optional: FileDrop for file-based comms
filedrop:
  base_dir: "/tmp/filedrop"
  identity: "MyAgent"

# Tools
exec:
  enabled: true
  timeout: 30
```

## 🔌 Plugin System

Cobot uses a plugin architecture with **extension points** — plugins can define hooks that other plugins implement.

### Built-in Plugins

| Plugin | Capability | Description |
|--------|------------|-------------|
| `config` | — | Configuration management |
| `ppq` | llm | PPQ.ai LLM provider |
| `ollama` | llm | Local Ollama models |
| `nostr` | communication | Nostr DMs (NIP-04) |
| `filedrop` | communication | File-based messaging |
| `wallet` | wallet | Lightning via npub.cash |
| `tools` | tools | Shell, file, restart tools |
| `hotreload` | — | Auto-restart on changes |

### Extension Points

Plugins can define extension points that other plugins implement:

```python
# filedrop/plugin.py defines:
meta = PluginMeta(
    id="filedrop",
    extension_points=["filedrop.before_write", "filedrop.after_read"],
)

# filedrop-nostr/plugin.py implements:
meta = PluginMeta(
    id="filedrop-nostr",
    implements={
        "filedrop.before_write": "sign_message",
        "filedrop.after_read": "verify_message",
    },
)
```

### Adding Plugins

1. **System-wide:** `/opt/cobot/plugins/`
2. **User:** `~/.cobot/plugins/`
3. **Project:** `./plugins/`

Each plugin directory needs a `plugin.py` with a `create_plugin()` factory function.

## 🔐 Self-Sovereign Stack

```
┌─────────────────────────────────────┐
│           Your Hardware             │  ← Physical control
├─────────────────────────────────────┤
│          Cobot Runtime              │  ← Self-hosted
├─────────────────────────────────────┤
│    Nostr Identity (npub/nsec)       │  ← Self-sovereign ID
├─────────────────────────────────────┤
│   Lightning Wallet (npub.cash)      │  ← Self-sovereign money
├─────────────────────────────────────┤
│      LLM (local or cloud)           │  ← Flexible inference
└─────────────────────────────────────┘
```

## 🛠️ CLI Commands

```bash
cobot run              # Start the agent
cobot run --stdin      # Interactive mode
cobot status           # Show status
cobot restart          # Restart running agent
cobot wallet balance   # Check wallet balance
cobot wallet address   # Show Lightning address
cobot config show      # Show configuration
```

## 🧪 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with verbose output
cobot run --verbose
```

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PLUGIN REGISTRY                           │
│  Registration │ Dependency resolution │ Extension points    │
├─────────────────────────────────────────────────────────────┤
│                      PLUGINS                                 │
│  config │ ppq/ollama │ nostr │ filedrop │ wallet │ tools   │
├─────────────────────────────────────────────────────────────┤
│                  EXTENSION POINTS                            │
│  Plugins define hooks → Other plugins implement them         │
├─────────────────────────────────────────────────────────────┤
│                   HOOK CHAIN                                 │
│  on_message_received → transform → llm_call → tool_exec    │
├─────────────────────────────────────────────────────────────┤
│                   CORE AGENT                                 │
│  Message loop │ LLM integration │ Tool execution            │
└─────────────────────────────────────────────────────────────┘
```

## 🆚 Why Cobot?

| Feature | Cobot | OpenClaw | Other Agents |
|---------|-------|----------|--------------|
| Minimal | ✅ ~2K lines | ❌ 430K lines | Varies |
| Self-sovereign | ✅ Your hardware | ⚠️ Self-hosted | ❌ Cloud |
| Nostr identity | ✅ Native | ❌ | ❌ |
| Lightning wallet | ✅ Native | ❌ | ❌ |
| Extension points | ✅ Unique | ❌ | ❌ |
| Hot reload | ✅ | ❌ | ❌ |

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions welcome! Please read the architecture docs first.

## 🔗 Links

- [Documentation](https://forgejo.tail593e12.ts.net/Zeus/cobot#readme)
- [Issues](https://forgejo.tail593e12.ts.net/Zeus/cobot/issues)
- [Nostr](https://nostr.com) — Decentralized social protocol
- [Lightning](https://lightning.network) — Bitcoin payment layer
