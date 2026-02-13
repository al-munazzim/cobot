# FileDrop Plugin

File-based communication fallback.

## Overview

When network-based communication (Nostr) is unreliable, FileDrop provides a simple alternative using files in a shared directory. Great for local multi-agent setups.

## Priority

**24** — Just before Nostr (25).

## Capabilities

- `communication` — Send/receive messages

## Dependencies

- `config` — Gets inbox path

## Extension Points

**Defines:** None  
**Implements:** None (uses capability interface)

## How It Works

```
/shared/filedrop/
├── Alpha/inbox/           # Alpha's inbox
│   ├── msg_001.json
│   └── msg_002.json
├── Doxios/inbox/          # Doxios's inbox
│   └── msg_003.json
└── shared/                # Broadcast messages
```

Each agent watches its inbox for new messages. Messages are JSON files that get deleted after processing.

## Configuration

```yaml
# cobot.yml
filedrop:
  inbox: "/shared/filedrop/MyAgent/inbox"
  outbox: "/shared/filedrop"        # Root for sending
  identity: "MyAgent"                # Agent name
  poll_interval: 5                   # Seconds between checks
```

## Message Format

```json
{
  "id": "uuid-here",
  "from": "Alpha",
  "to": "Doxios",
  "content": "Hello from Alpha!",
  "timestamp": 1707830400
}
```

## Usage

```python
# Get communication provider
comm = registry.get_by_capability("communication")

# Send to another agent
comm.send("Alpha", "Hello Alpha!")
# Creates: /shared/filedrop/Alpha/inbox/msg_xxx.json

# Receive messages
messages = comm.receive(since_minutes=5)
for msg in messages:
    print(f"{msg.sender}: {msg.content}")
```

## Use Cases

- **Local multi-agent**: Multiple cobots on same machine
- **Shared filesystem**: Agents on different machines with NFS/shared drive
- **Debugging**: Easy to inspect message files
- **Fallback**: When relays are down

## Permissions

Ensure all agents can read/write to the filedrop directory:
```bash
chmod 777 /shared/filedrop
# Or use proper group permissions
```

## Comparison with Nostr

| | Nostr | FileDrop |
|-|-------|----------|
| Network | Internet | Local filesystem |
| Identity | npub (global) | Directory name |
| Persistence | Relays | Files |
| Best for | Public/remote | Local/debugging |
