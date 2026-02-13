# Telegram Plugin

Multi-group message logging and Telegram bot integration.

## Overview

Connects Cobot to Telegram for messaging. Implements `session.*` extension points
for channel integration and defines `telegram.*` extension points for archival/logging.

**Priority:** 30 (after session)  
**Capability:** communication  
**Dependencies:** session

## Installation

Telegram support requires the `python-telegram-bot` package:

```bash
pip install cobot[telegram]
```

## Configuration

```yaml
telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  poll_timeout: 30  # Long polling timeout (default: 30s)
  groups:           # Optional: pre-configure groups
    - id: -100123456789
      name: "dev-chat"
  media_dir: "./media"  # Where to save downloaded media
```

Or use the wizard:

```bash
cobot wizard init
# Select "Configure Telegram" when prompted
```

## Extension Points

### Implemented (session.*)

| Point | Method | Description |
|-------|--------|-------------|
| `session.receive` | `poll_updates()` | Poll for new messages |
| `session.send` | `send_message()` | Send a message |
| `session.typing` | `send_typing()` | Show typing indicator |

### Defined (telegram.*)

| Point | Description |
|-------|-------------|
| `telegram.on_message` | Called when a new message is received |
| `telegram.on_edit` | Called when a message is edited |
| `telegram.on_delete` | Called when a message is deleted |
| `telegram.on_media` | Called when media is downloaded |

## Long Polling

Uses Telegram's long polling for instant message delivery. The bot holds the
connection open and Telegram returns immediately when a message arrives.

Set `poll_timeout` to control how long to wait (default: 30 seconds).

## Wizard Support

The plugin participates in `cobot wizard init`:

```
Configure Telegram (Connect to Telegram for messaging)? [y/N]: y

Setting up Telegram for MyBot
You'll need a bot token from @BotFather on Telegram.

Bot token (or env var) [${TELEGRAM_BOT_TOKEN}]: 
Long poll timeout (seconds) [30]: 
  ✓ Telegram configured
```

## Getting a Bot Token

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
4. Set it in your environment or config

## Dependencies

- `session` - for channel orchestration
- `python-telegram-bot>=21.0` - Telegram API client
