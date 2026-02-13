# Pairing Plugin

User authorization via pairing codes.

## Overview

Controls who can interact with your bot. Unknown users receive a pairing code
that the bot owner can approve via CLI.

**Priority:** 5 (runs before all other plugins)

## Flow

```
User sends message
    ↓
Is user authorized?
    ├─ YES → continue to other plugins
    └─ NO  → send pairing instructions
            → abort message processing
```

## Configuration

```yaml
pairing:
  enabled: true                    # Enable/disable (default: true)
  owner_ids:                       # Always-authorized users (bootstrap)
    telegram: ["769134210"]
    discord: ["123456789"]
  skip_channels: ["nostr"]         # No auth required for these channels
  storage_path: ~/.cobot/pairing.yml  # Optional: custom path
```

## CLI Commands

```bash
# List all requests and authorized users
cobot pairing list

# List only pending requests
cobot pairing list --pending

# List only authorized users
cobot pairing list --approved

# Approve a pairing request
cobot pairing approve ABCD1234

# Reject a pairing request
cobot pairing reject ABCD1234

# Revoke a user's authorization
cobot pairing revoke telegram 123456789
```

## Message to Unauthorized Users

When an unauthorized user messages the bot:

```
Access not configured.
Your Telegram user id: 123456789
Pairing code: MXVA2RWY

Ask the bot owner to approve with:
  cobot pairing approve MXVA2RWY
```

## Storage Format

Data is stored in `~/.cobot/pairing.yml`:

```yaml
authorized:
  - channel: telegram
    user_id: "769134210"
    name: "k9ert"
    approved_at: "2026-02-13T21:50:00+00:00"

pending:
  - channel: telegram
    user_id: "123456789"
    name: "stranger"
    code: "MXVA2RWY"
    requested_at: "2026-02-13T21:45:00+00:00"
```

## Dependencies

- `config` - for configuration loading
