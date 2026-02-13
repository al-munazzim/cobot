# Workspace Plugin

Provides workspace directory paths for all plugins.


## Table of Contents

- [Overview](#overview)
- [Priority](#priority)
- [Capabilities](#capabilities)
- [Dependencies](#dependencies)
- [Extension Points](#extension-points)
- [Workspace Structure](#workspace-structure)
- [Path Resolution Priority](#path-resolution-priority)
- [Configuration](#configuration)
- [Usage](#usage)
- [Auto-Creation](#auto-creation)

## Overview

The workspace plugin manages the agent's working directory structure. Other plugins use it to store memory, logs, skills, and other data.

## Priority

**5** — Loaded early so other plugins can depend on it.

## Capabilities

- `workspace` — Provides directory paths

## Dependencies

- `config` — Reads workspace path from config

## Extension Points

**Defines:** None  
**Implements:** None

## Workspace Structure

```
~/.cobot/workspace/
├── memory/          # Memory plugin storage
│   └── files/       # File-based memories
├── skills/          # Custom skills
├── plugins/         # External plugins
├── logs/            # Log files
├── SOUL.md          # Agent persona
├── AGENTS.md        # Agent instructions
└── USER.md          # User profile
```

## Path Resolution Priority

1. CLI argument (`--workspace`)
2. `COBOT_WORKSPACE` environment variable
3. `workspace:` in config file
4. Default: `~/.cobot/workspace/`

## Configuration

```yaml
# cobot.yml
workspace: "/path/to/workspace"

# Or use environment variable
# COBOT_WORKSPACE=/path/to/workspace
```

## Usage

```python
# Get workspace plugin
workspace = registry.get("workspace")

# Get workspace root
root = workspace.get_path()  # Path("~/.cobot/workspace")

# Get subdirectory paths
memory_dir = workspace.get_path("memory")   # .../workspace/memory
skills_dir = workspace.get_path("skills")   # .../workspace/skills
logs_dir = workspace.get_path("logs")       # .../workspace/logs
```

## Auto-Creation

On startup, the workspace plugin creates the directory structure if it doesn't exist:
- Creates workspace root
- Creates subdirectories: `memory/`, `skills/`, `plugins/`, `logs/`
