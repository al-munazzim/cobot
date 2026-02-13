# Cobot Plugins

Cobot's functionality is provided by a modular plugin system. Each plugin is self-contained with its own code, tests, and documentation.

## Table of Contents

- [Architecture](#architecture)
- [Plugin List](#plugin-list)
- [Dependency Tree](#dependency-tree)
- [Extension Points](#extension-points)
- [Load Order](#load-order)
- [Creating a Plugin](#creating-a-plugin)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                           Agent                                 │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Plugin Registry                            │
│  - Discovers plugins                                            │
│  - Resolves dependencies                                        │
│  - Manages lifecycle (configure → start → stop)                 │
│  - Routes extension point calls                                 │
└─────────────────────────────────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
   ┌─────────┐           ┌─────────┐           ┌─────────┐
   │ Plugin  │           │ Plugin  │           │ Plugin  │
   └─────────┘           └─────────┘           └─────────┘
```

## Plugin List

| Plugin | Description | Capability |
|--------|-------------|------------|
| [config](config/) | Configuration loading | `config` |
| [workspace](workspace/) | Directory paths | `workspace` |
| [logger](logger/) | Event logging | `logging` |
| [security](security/) | Prompt injection detection | `security` |
| [communication](communication/) | Messaging interface | — |
| [session](session/) | Channel routing | — |
| [memory](memory/) | Memory interface | — |
| [memory_files](memory_files/) | File-based memory | — |
| [persistence](persistence/) | Conversation history | `persistence` |
| [soul](soul/) | Agent persona | — |
| [compaction](compaction/) | History summarization | `compaction` |
| [context](context/) | System prompt building | — |
| [ppq](ppq/) | PPQ.ai LLM | `llm` |
| [ollama](ollama/) | Local Ollama LLM | `llm` |
| [nostr](nostr/) | Nostr communication | `communication` |
| [filedrop](filedrop/) | File-based communication | `communication` |
| [wallet](wallet/) | Lightning wallet | `wallet` |
| [tools](tools/) | Agent tools | `tools` |

## Dependency Tree

```
config (1)
├── workspace (5)
│   ├── soul (15)
│   ├── memory (12)
│   │   └── memory_files (14)
│   └── context (18)
├── logger (5)
├── security (10)
├── communication (5)
│   └── session (10)
│       └── [channels: telegram, discord, nostr...]
├── persistence (15)
│   └── compaction (16)
├── ppq (20) ─────────┐
├── ollama (20) ──────┼── (one LLM provider selected)
├── nostr (25)
├── filedrop (24)
├── wallet (25)
└── tools (30)
```

**Reading the tree:**
- Number in parentheses = priority (lower loads first)
- Indented items depend on their parent
- `[channels]` = external plugins implementing `session.*`

## Extension Points

Extension points allow plugins to define interfaces that other plugins implement.

### Defined Extension Points

| Plugin | Extension Point | Signature |
|--------|-----------------|-----------|
| communication | `communication.receive` | `() -> list[IncomingMessage]` |
| communication | `communication.send` | `(OutgoingMessage) -> bool` |
| communication | `communication.typing` | `(channel_type, channel_id) -> None` |
| communication | `communication.channels` | `() -> list[str]` |
| session | `session.receive` | `() -> list[IncomingMessage]` |
| session | `session.send` | `(OutgoingMessage) -> bool` |
| session | `session.typing` | `(channel_id) -> None` |
| context | `context.system_prompt` | `() -> str` |
| context | `context.history` | `() -> list[dict]` |
| memory | `memory.store` | `(key, content) -> None` |
| memory | `memory.retrieve` | `(key) -> str` |
| memory | `memory.search` | `(query) -> list[dict]` |

### Implementations

| Plugin | Implements | Method |
|--------|------------|--------|
| session | `communication.receive` | `poll_all_channels` |
| session | `communication.send` | `send` |
| session | `communication.typing` | `typing` |
| session | `communication.channels` | `get_channels` |
| soul | `context.system_prompt` | `get_soul` |
| memory_files | `memory.store` | `store` |
| memory_files | `memory.retrieve` | `retrieve` |
| memory_files | `memory.search` | `search` |

### Extension Point Flow

```
Agent calls communication.poll()
         │
         ▼
Communication Plugin (definer)
         │
         │ calls all communication.receive implementations
         ▼
Session Plugin (implementer)
         │
         │ calls all session.receive implementations
         ▼
Telegram Plugin (implementer)
         │
         └── returns messages from Telegram
```

## Load Order

Plugins are loaded in priority order (lower = earlier):

| Priority | Plugins |
|----------|---------|
| 1 | config |
| 5 | workspace, logger, communication |
| 10 | security, session |
| 12 | memory |
| 14 | memory_files |
| 15 | persistence, soul |
| 16 | compaction |
| 18 | context |
| 20 | ppq, ollama |
| 24 | filedrop |
| 25 | nostr, wallet |
| 30 | tools, [channels] |

## Creating a Plugin

### Directory Structure

```
cobot/plugins/myplugin/
├── README.md           # Documentation
├── __init__.py         # Exports
├── plugin.py           # Implementation
└── tests/
    ├── __init__.py
    └── test_plugin.py  # Tests
```

### Minimal Plugin

```python
# plugin.py
from cobot.plugins.base import Plugin, PluginMeta

class MyPlugin(Plugin):
    meta = PluginMeta(
        id="myplugin",
        version="1.0.0",
        dependencies=["config"],
        priority=50,
    )

    def configure(self, config: dict) -> None:
        self._config = config.get("myplugin", {})

    def start(self) -> None:
        print("[myplugin] Started")

    def stop(self) -> None:
        print("[myplugin] Stopped")

def create_plugin() -> MyPlugin:
    return MyPlugin()
```

### With Extension Points

```python
# Defining extension points
meta = PluginMeta(
    id="myplugin",
    extension_points=["myplugin.hook"],
)

# Implementing extension points
meta = PluginMeta(
    id="myplugin-impl",
    dependencies=["myplugin"],
    implements={"myplugin.hook": "my_method"},
)
```

### With Capabilities

```python
from cobot.plugins.interfaces import LLMProvider

class MyLLMPlugin(Plugin, LLMProvider):
    meta = PluginMeta(
        id="myllm",
        capabilities=["llm"],
    )
    
    def chat(self, messages, tools=None, model=None, max_tokens=2048):
        # Implement LLMProvider interface
        ...
```
