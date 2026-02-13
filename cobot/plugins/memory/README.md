# Memory Plugin

Defines extension points for memory storage and retrieval.

## Overview

The memory plugin is an **extension point definer**. It defines the interface for memory operations (store, retrieve, search) that different backends can implement (files, vector DB, etc.).

## Priority

**12** — After workspace, before implementations.

## Capabilities

None.

## Dependencies

- `workspace` — Memory implementations store data in workspace

## Extension Points

**Defines:**
- `memory.store` — Store content: `store(key: str, content: str) -> None`
- `memory.retrieve` — Get by key: `retrieve(key: str) -> str`
- `memory.search` — Search: `search(query: str) -> list[dict]`

**Implements:** None

## Architecture

```
Memory Plugin (definer)
    │
    ├── memory.store
    │       │
    │       ├── memory-files → writes to .md files
    │       └── memory-vector → stores in vector DB (future)
    │
    ├── memory.retrieve
    │       │
    │       └── (first implementation that returns a result)
    │
    └── memory.search
            │
            └── (aggregates results from all implementations)
```

## Usage

```python
# Get memory plugin (aggregator)
memory = registry.get("memory")

# Store (calls all memory.store implementations)
memory.store("meeting-notes", "Discussed project Alpha...")

# Retrieve (returns first result found)
content = memory.retrieve("meeting-notes")

# Search (aggregates from all implementations)
results = memory.search("project Alpha")
# [{"source": "memory-files", "key": "meeting-notes", "content": "...", "score": 0.9}]
```

## CLI Commands

```bash
# Store a memory
cobot memory store meeting-notes "Discussed project Alpha..."

# Retrieve by key
cobot memory get meeting-notes

# Search memories
cobot memory search "project Alpha"

# List all keys
cobot memory list
```

## Implementing Memory Backend

```python
class MyMemoryBackend(Plugin):
    meta = PluginMeta(
        id="memory-vector",
        dependencies=["workspace", "memory"],
        implements={
            "memory.store": "store",
            "memory.retrieve": "retrieve", 
            "memory.search": "search",
        },
        priority=14,  # After memory plugin
    )
    
    def store(self, key: str, content: str) -> None:
        # Store in vector DB
        ...
    
    def retrieve(self, key: str) -> str:
        # Retrieve from vector DB
        ...
    
    def search(self, query: str) -> list[dict]:
        # Semantic search
        return [{"key": "...", "content": "...", "score": 0.9}]
```
