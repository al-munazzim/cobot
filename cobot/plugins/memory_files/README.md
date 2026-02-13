# Memory-Files Plugin

File-based implementation of memory extension points.


## Table of Contents

- [Overview](#overview)
- [Priority](#priority)
- [Capabilities](#capabilities)
- [Dependencies](#dependencies)
- [Extension Points](#extension-points)
- [Storage Structure](#storage-structure)
- [Usage](#usage)
- [Search Results Format](#search-results-format)
- [Limitations](#limitations)
- [Future: memory-vector](#future-memory-vector)

## Overview

Implements memory operations using markdown files in `workspace/memory/files/`. Simple, human-readable storage without external dependencies.

## Priority

**14** — After memory plugin (extension point definer).

## Capabilities

None.

## Dependencies

- `workspace` — Gets path for memory storage
- `memory` — Implements its extension points

## Extension Points

**Defines:** None  
**Implements:**
- `memory.store` → `store()` — Writes content to `.md` file
- `memory.retrieve` → `retrieve()` — Reads content from `.md` file
- `memory.search` → `search()` — Searches file contents

## Storage Structure

```
workspace/memory/files/
├── meeting-notes.md
├── project-alpha.md
├── user-preferences.md
└── 2026-02-13.md
```

## Usage

```python
# Get plugin directly (or use through memory plugin)
memory_files = registry.get("memory-files")

# Store
memory_files.store("meeting-notes", "# Meeting Notes\n\nDiscussed...")
# Creates: workspace/memory/files/meeting-notes.md

# Retrieve
content = memory_files.retrieve("meeting-notes")
# Reads: workspace/memory/files/meeting-notes.md

# Search (simple substring match)
results = memory_files.search("project Alpha")
# Returns files containing "project Alpha"
```

## Search Results Format

```python
[
    {
        "key": "meeting-notes",        # Filename without .md
        "content": "# Meeting...",      # File content
        "score": 1.0                    # Match score (1.0 for exact match)
    }
]
```

## Limitations

- Simple substring search (no semantic/vector search)
- No indexing (scans all files)
- Best for small-medium amounts of data

## Future: memory-vector

For semantic search and larger datasets, a `memory-vector` plugin could implement the same extension points using a vector database.
