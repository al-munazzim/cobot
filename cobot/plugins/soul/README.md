# Soul Plugin

Reads `SOUL.md` from workspace to define agent persona.


## Table of Contents

- [Overview](#overview)
- [Priority](#priority)
- [Capabilities](#capabilities)
- [Dependencies](#dependencies)
- [Extension Points](#extension-points)
- [SOUL.md Format](#soulmd-format)
- [Personality](#personality)
- [Guidelines](#guidelines)
- [Tone](#tone)
- [Usage](#usage)
- [How It Works](#how-it-works)
- [Integration with Context](#integration-with-context)

## Overview

The soul plugin provides the agent's personality and tone by reading a `SOUL.md` file from the workspace. This content is injected into the system prompt.

## Priority

**15** — After workspace, before context aggregation.

## Capabilities

None.

## Dependencies

- `workspace` — Gets workspace path for SOUL.md

## Extension Points

**Defines:** None  
**Implements:**
- `context.system_prompt` → `get_soul()` — Contributes SOUL.md content to system prompt

## SOUL.md Format

```markdown
# SOUL.md

You are **Cobot**, a helpful AI assistant.

## Personality
- Friendly and approachable
- Concise but thorough
- Technically competent

## Guidelines
- Always be honest
- Admit when you don't know something
- Ask clarifying questions when needed

## Tone
Warm, professional, with occasional humor.
```

## Usage

```python
# Get soul plugin
soul = registry.get("soul")

# Get soul content
content = soul.get_soul()
# Returns contents of SOUL.md or empty string if missing
```

## How It Works

1. Soul plugin reads `{workspace}/SOUL.md` on startup
2. Context plugin calls `context.system_prompt` extension point
3. Soul plugin returns SOUL.md content
4. Context plugin aggregates all contributions into system prompt

## Integration with Context

```
Context Plugin
    │
    ├── calls context.system_prompt
    │       │
    │       └── Soul Plugin → SOUL.md content
    │
    └── builds final system prompt
```
