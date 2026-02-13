# Ollama Plugin

Local LLM inference via [Ollama](https://ollama.ai).


## Table of Contents

- [Overview](#overview)
- [Priority](#priority)
- [Capabilities](#capabilities)
- [Dependencies](#dependencies)
- [Extension Points](#extension-points)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Usage](#usage)
- [Response Format](#response-format)
- [Supported Models](#supported-models)
- [Tool Support](#tool-support)
- [Comparison with PPQ](#comparison-with-ppq)

## Overview

Provides LLM capabilities using locally-running Ollama. No API keys needed, runs entirely on your hardware.

## Priority

**20** — After config.

## Capabilities

- `llm` — Provides chat completion

## Dependencies

- `config` — Gets host and model settings

## Extension Points

**Defines:** None  
**Implements:** None (uses capability interface)

## Prerequisites

1. Install Ollama: https://ollama.ai/download
2. Pull a model: `ollama pull llama3.2`
3. Ensure Ollama is running: `ollama serve`

## Configuration

```yaml
# cobot.yml
provider: ollama  # Select this provider

ollama:
  host: "http://localhost:11434"  # Ollama API endpoint
  model: "llama3.2"               # Default model
```

## Usage

```python
# Get LLM provider
llm = registry.get_by_capability("llm")

# Simple chat
response = llm.chat([
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "Hello!"}
])
print(response.content)
```

## Response Format

```python
LLMResponse(
    content="Hello!",           # Response text
    tool_calls=None,            # Tool support varies by model
    model="llama3.2",           # Model used
    usage={...}                 # Token usage (if available)
)
```

## Supported Models

Run `ollama list` to see installed models. Popular options:
- `llama3.2` — Meta's Llama 3.2
- `mistral` — Mistral 7B
- `codellama` — Code-focused
- `phi3` — Microsoft Phi-3

## Tool Support

Tool/function calling support depends on the model. Not all Ollama models support tools.

## Comparison with PPQ

| | PPQ | Ollama |
|-|-----|--------|
| Runs | Cloud | Local |
| Cost | Per-query | Free (hardware) |
| Privacy | Data sent to API | Fully local |
| Models | Latest GPT/Claude | Open models |
| Tool support | Full | Model-dependent |
