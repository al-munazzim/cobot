# Nostr Plugin

Communication via the [Nostr](https://nostr.com) protocol.


## Table of Contents

- [Overview](#overview)
- [Priority](#priority)
- [Capabilities](#capabilities)
- [Dependencies](#dependencies)
- [Extension Points](#extension-points)
- [Installation](#installation)
- [Configuration](#configuration)
- [Environment Variables](#environment-variables)
- [Usage](#usage)
- [Message Format](#message-format)
- [Default Relays](#default-relays)
- [Identity Generation](#identity-generation)
- [Security](#security)

## Overview

Provides peer-to-peer communication using Nostr encrypted direct messages. Your agent gets a persistent identity (npub) that works across relays.

## Priority

**25** — After config.

## Capabilities

- `communication` — Send/receive messages

## Dependencies

- `config` — Gets nsec and relay list
- `pynostr` — Nostr protocol library (optional dependency)

## Extension Points

**Defines:** None  
**Implements:** None (uses capability interface)

## Installation

```bash
pip install cobot[nostr]
# or
pip install pynostr
```

## Configuration

```yaml
# cobot.yml
nostr:
  nsec: "${NOSTR_NSEC}"        # Private key (or env var)
  relays:                       # Relay list
    - "wss://relay.damus.io"
    - "wss://relay.primal.net"
    - "wss://nos.lol"
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `NOSTR_NSEC` | Nostr private key (nsec1...) |

## Usage

```python
# Get communication provider
comm = registry.get_by_capability("communication")

# Get identity
identity = comm.get_identity()
print(identity["npub"])  # npub1...

# Send DM
event_id = comm.send("npub1recipient...", "Hello!")

# Receive messages
messages = comm.receive(since_minutes=5)
for msg in messages:
    print(f"{msg.sender}: {msg.content}")
```

## Message Format

```python
Message(
    id="abc123...",             # Event ID
    sender="npub1...",          # Sender's npub
    content="Hello!",           # Decrypted message
    timestamp=1707830400        # Unix timestamp
)
```

## Default Relays

If no relays configured, uses:
- wss://relay.damus.io
- wss://relay.primal.net
- wss://nos.lol
- wss://relay.nostr.band
- wss://nostr.wine
- wss://nostr.mom

## Identity Generation

To generate a new identity:
```bash
# Using cobot
cobot identity generate

# Or using pynostr
python -c "from pynostr.key import PrivateKey; k=PrivateKey(); print(f'nsec: {k.bech32()}\nnpub: {k.public_key.bech32()}')"
```

## Security

- Private key (nsec) should be kept secret
- Use environment variable, not config file
- Messages are encrypted end-to-end (NIP-04)
