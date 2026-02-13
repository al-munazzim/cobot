# Config Plugin

Loads and provides configuration from `cobot.yml`.


## Table of Contents

- [Overview](#overview)
- [Priority](#priority)
- [Capabilities](#capabilities)
- [Dependencies](#dependencies)
- [Extension Points](#extension-points)
- [Features](#features)
- [Configuration](#configuration)
- [Usage](#usage)
- [Environment Variables](#environment-variables)

## Overview

The config plugin is loaded first (priority 1) and provides configuration to all other plugins. It reads YAML configuration files and expands environment variables.

## Priority

**1** — Loaded first, before all other plugins.

## Capabilities

- `config` — Provides configuration access

## Dependencies

None.

## Extension Points

**Defines:** None  
**Implements:** None

## Features

- Loads config from `cobot.yml` or `config.yaml`
- Environment variable expansion: `${VAR}` and `${VAR:-default}`
- Provides typed config via `CobotConfig` dataclass
- Plugin-specific config via `get_plugin_config(plugin_id)`

## Configuration

```yaml
# cobot.yml
identity:
  name: "MyBot"

polling:
  interval_seconds: 30

provider: ppq  # or ollama

exec:
  enabled: true
  blocklist: ["rm -rf", "sudo"]
  timeout: 30

# Plugin-specific config
ppq:
  api_key: "${PPQ_API_KEY}"
  model: "gpt-4o"

workspace: "~/.cobot/workspace"
```

## Usage

```python
# Get config plugin
config_plugin = registry.get("config")
config = config_plugin.get_config()

# Access config values
print(config.identity_name)      # "MyBot"
print(config.polling_interval)   # 30
print(config.provider)           # "ppq"

# Get plugin-specific config
ppq_config = config.get_plugin_config("ppq")
print(ppq_config["model"])       # "gpt-4o"
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `PPQ_API_KEY` | API key for PPQ provider |
| `NOSTR_NSEC` | Nostr private key |
| `COBOT_WORKSPACE` | Override workspace location |
