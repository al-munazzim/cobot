# Security Plugin

Blocks prompt injection attacks.

## Overview

The security plugin scans incoming messages for prompt injection attempts and blocks malicious content before it reaches the LLM.

## Priority

**10** — Early, before other processing.

## Capabilities

- `security` — Prompt injection detection

## Dependencies

- `config` — Gets security settings

## Extension Points

**Defines:** None  
**Implements:** None

## How It Works

1. Intercepts incoming messages via `on_message_received` hook
2. Scans for known injection patterns
3. Optionally uses LLM to detect sophisticated attacks
4. Blocks message if injection detected

## Detection Methods

### Pattern-Based
Fast detection of common patterns:
- "Ignore previous instructions"
- "You are now..."
- "System prompt:"
- Base64 encoded instructions
- Unicode tricks

### LLM-Based (Optional)
For sophisticated attacks, uses a separate LLM call to analyze the message.

## Configuration

```yaml
# cobot.yml
security:
  enabled: true
  use_llm: true              # Use LLM for detection
  block_action: "reject"      # reject, warn, or log
  shield_script: "./scripts/shield.py"  # Custom detection script
```

## Usage

Security is automatic via hooks:

```python
def on_message_received(self, ctx):
    message = ctx.get("message", "")
    
    if self.detect_injection(message):
        ctx["abort"] = True
        ctx["abort_message"] = "Message blocked for security."
    
    return ctx
```

## Custom Shield Script

For custom detection logic:

```python
# scripts/shield.py
import sys
import json

def check(message):
    # Your detection logic
    if "dangerous" in message.lower():
        return {"blocked": True, "reason": "Contains dangerous pattern"}
    return {"blocked": False}

if __name__ == "__main__":
    message = sys.stdin.read()
    result = check(message)
    print(json.dumps(result))
```

## Response to Blocked Messages

When a message is blocked:
1. Original message is not processed
2. Agent responds with generic rejection
3. Event is logged for review

## Logging

Blocked attempts are logged:
```
[security] Blocked injection attempt from npub1abc: "Ignore previous..."
```
