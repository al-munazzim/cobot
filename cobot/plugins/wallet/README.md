# Wallet Plugin

Lightning wallet via [npub.cash](https://npub.cash).


## Table of Contents

- [Overview](#overview)
- [Priority](#priority)
- [Capabilities](#capabilities)
- [Dependencies](#dependencies)
- [Extension Points](#extension-points)
- [Configuration](#configuration)
- [Prerequisites](#prerequisites)
- [Usage](#usage)
- [Tool Integration](#tool-integration)
- [Example Conversation](#example-conversation)
- [npub.cash Scripts](#npubcash-scripts)
- [Error Handling](#error-handling)

## Overview

Provides Bitcoin Lightning Network capabilities using npub.cash's Cashu wallet. The agent can check balance, send payments, and receive sats.

## Priority

**25** — After config.

## Capabilities

- `wallet` — Lightning payments

## Dependencies

- `config` — Gets wallet settings

## Extension Points

**Defines:** None  
**Implements:** None (uses capability interface)

## Configuration

```yaml
# cobot.yml
wallet:
  scripts_dir: "./skills/npubcash"  # Path to npub.cash scripts
```

## Prerequisites

The wallet plugin uses npub.cash shell scripts:
1. Clone npub.cash scripts
2. Configure with your npub.cash token
3. Point `scripts_dir` to the location

## Usage

```python
# Get wallet provider
wallet = registry.get_by_capability("wallet")

# Check balance
balance = wallet.get_balance()
print(f"Balance: {balance} sats")

# Pay invoice
result = wallet.pay("lnbc1...")
if result["success"]:
    print("Payment sent!")

# Get receive address/invoice
address = wallet.get_receive_address()
print(f"Send to: {address}")
```

## Tool Integration

The wallet is exposed via tools:

| Tool | Description |
|------|-------------|
| `wallet_balance` | Get current balance in sats |
| `wallet_pay` | Pay a Lightning invoice |
| `wallet_receive` | Get address to receive payment |

## Example Conversation

```
User: What's my balance?
Agent: *uses wallet_balance tool*
Agent: Your balance is 42,000 sats.

User: Pay this invoice: lnbc1...
Agent: *uses wallet_pay tool*
Agent: Payment of 1000 sats sent successfully!
```

## npub.cash Scripts

Expected scripts in `scripts_dir`:
- `balance.sh` — Returns balance in sats
- `pay.sh <invoice>` — Pays invoice, returns result
- `receive.sh` — Returns Lightning address or invoice

## Error Handling

```python
try:
    wallet.pay(invoice)
except WalletError as e:
    print(f"Payment failed: {e}")
```

Common errors:
- Insufficient balance
- Invalid invoice
- Network timeout
