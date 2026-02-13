# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | ✅ Yes             |

## Reporting a Vulnerability

**Do not report security vulnerabilities through public GitHub issues.**

Instead, please report them privately:

1. **Email:** security@ultanio.com (or project maintainer)
2. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work with you to understand and address the issue.

## Security Considerations

### Agent Security

Cobot is designed to run with significant system access. Consider:

- **Sandboxing:** Run in a container or VM for untrusted operations
- **Tool restrictions:** Use `exec.blocklist` to prevent dangerous commands
- **Network isolation:** Limit outbound connections if possible

### Secrets Management

- Never commit secrets (API keys, nsec) to version control
- Use environment variables: `${PPQ_API_KEY}`
- Keep `.env` files out of git (see `.gitignore`)

### Nostr Identity

- Your `nsec` is your identity — protect it
- Consider separate identities for different agents
- Backup keys securely

### Known Limitations

Current version does **not** have:
- Container isolation for tool execution
- Sandboxed plugin execution
- Rate limiting on tool calls

These are planned for future releases.

## Security Best Practices

```yaml
# cobot.yml security settings
exec:
  enabled: true
  blocklist:
    - "rm -rf /"
    - "sudo"
    - "curl | bash"
  timeout: 30

# Restrict trusted senders
trusted:
  - npub: "npub1..."
    name: "Owner"
    role: "handler"
```

## Acknowledgments

We appreciate responsible disclosure and will acknowledge security researchers who help improve Cobot's security.
