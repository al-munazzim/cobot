# Changelog

All notable changes to Cobot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release preparation

## [0.1.0] - 2026-02-13

### Added

#### Core
- Plugin registry with dependency resolution
- Extension point system (plugins define hooks, others implement)
- Hook chain for lifecycle events
- Multi-path plugin loading (system, user, project)
- Hot reload plugin for auto-restart on changes

#### Plugins
- `config` - Configuration management with env var expansion
- `ppq` - PPQ.ai LLM provider
- `ollama` - Local Ollama model support
- `nostr` - Nostr DMs (NIP-04 encrypted)
- `filedrop` - File-based communication
- `filedrop-nostr` - Schnorr signatures for FileDrop
- `wallet` - Lightning wallet via npub.cash
- `tools` - Shell execution, file operations
- `security` - Prompt injection shield
- `persistence` - Conversation memory
- `compaction` - Context window management
- `logger` - Logging plugin

#### CLI
- `cobot run` - Start agent
- `cobot run --stdin` - Interactive mode
- `cobot status` - Show agent status
- `cobot restart` - Restart running agent
- `cobot wallet balance` - Check balance
- `cobot wallet address` - Show Lightning address
- `cobot config show` - Display configuration

#### Documentation
- README with architecture overview
- CONTRIBUTING guide
- Example configurations
- Issue templates

### Architecture Decisions
- Plugin-first design
- Extension points for loose coupling
- Nostr for self-sovereign identity
- Lightning for autonomous payments
- Minimal core (~2K lines)

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 0.1.0 | 2026-02-13 | Initial release |

[Unreleased]: https://github.com/ultanio/cobot/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ultanio/cobot/releases/tag/v0.1.0
