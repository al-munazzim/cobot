# Logger Plugin

Logs lifecycle events.


## Table of Contents

- [Overview](#overview)
- [Priority](#priority)
- [Capabilities](#capabilities)
- [Dependencies](#dependencies)
- [Extension Points](#extension-points)
- [Log Levels](#log-levels)
- [Configuration](#configuration)
- [Output Format](#output-format)
- [Hooks](#hooks)
- [Usage](#usage)
- [JSON Logging](#json-logging)

## Overview

Simple logging plugin that outputs lifecycle events to stderr. Useful for debugging and monitoring.

## Priority

**5** — Very early, logs everything.

## Capabilities

- `logging` — Event logging

## Dependencies

None.

## Extension Points

**Defines:** None  
**Implements:** None

## Log Levels

| Level | Description |
|-------|-------------|
| `debug` | Verbose debugging info |
| `info` | Normal operation events |
| `warn` | Warning conditions |
| `error` | Error conditions |

## Configuration

```yaml
# cobot.yml
logger:
  level: "info"    # debug, info, warn, error
```

## Output Format

```
[2026-02-13T17:00:00Z] [INFO] [logger] Plugin started
[2026-02-13T17:00:01Z] [INFO] [cobot] Message received from npub1...
[2026-02-13T17:00:02Z] [DEBUG] [ppq] Calling API with 3 messages
[2026-02-13T17:00:03Z] [WARN] [nostr] Relay connection slow
```

## Hooks

The logger plugin uses hooks to log events:

```python
def on_message_received(self, ctx):
    self.log("info", f"Message from {ctx.get('sender')}")
    return ctx

def on_before_llm_call(self, ctx):
    self.log("debug", f"LLM call with {len(ctx.get('messages', []))} messages")
    return ctx

def on_error(self, ctx):
    self.log("error", f"Error: {ctx.get('error')}")
    return ctx
```

## Usage

```python
# Get logger plugin
logger = registry.get("logger")

# Log manually
logger.log("info", "Something happened")
logger.log("error", "Something went wrong")
```

## JSON Logging

For structured logging (future):
```json
{"timestamp": "2026-02-13T17:00:00Z", "level": "info", "plugin": "logger", "message": "Plugin started"}
```
