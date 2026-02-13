# Context Plugin

Builds system prompts by aggregating from extension point implementers.

## Overview

The context plugin defines extension points for building the agent's context (system prompt, conversation history). Other plugins implement these points to contribute their parts.

## Priority

**18** — After soul, memory, and other contributors.

## Capabilities

None.

## Dependencies

- `config`

## Extension Points

**Defines:**
- `context.system_prompt` — Plugins contribute text to system prompt
- `context.history` — Plugins contribute conversation history

**Implements:** None

## How It Works

```
Context Plugin (definer)
    │
    ├── context.system_prompt
    │       │
    │       ├── Soul Plugin → SOUL.md content
    │       ├── Identity Plugin → identity info
    │       └── ... other plugins
    │
    └── context.history
            │
            ├── Memory Plugin → relevant memories
            ├── Persistence Plugin → recent messages
            └── ... other plugins
```

## Usage

```python
# Get context plugin
context = registry.get("context")

# Build system prompt from all contributors
system_prompt = context.build_system_prompt()
# Aggregates from all context.system_prompt implementers

# Build history (future)
history = context.build_history()
```

## Implementing context.system_prompt

```python
class MyPlugin(Plugin):
    meta = PluginMeta(
        id="my-plugin",
        implements={
            "context.system_prompt": "get_prompt",
        },
    )
    
    def get_prompt(self) -> str:
        return "Additional context from my plugin."
```

## Implementing context.history

```python
class MyPlugin(Plugin):
    meta = PluginMeta(
        id="my-plugin",
        implements={
            "context.history": "get_history",
        },
    )
    
    def get_history(self) -> list[dict]:
        return [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."},
        ]
```
