# Nexus AI

Ultra-minimal multi-provider AI CLI framework.

## Features

- **Unified Interface**: Single CLI for OpenAI, Anthropic, Ollama, and OpenRouter
- **Session Management**: Persistent conversations with search and export
- **Prompt Library**: Save and reuse system prompts
- **Smart Defaults**: Interactive model selection and fuzzy search
- **Streaming Output**: Real-time response streaming

## Installation

```bash
pip install -e .
```

## Environment Setup

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Required environment variables (set at least one provider):

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OPENROUTER_API_KEY` | OpenRouter API key |

For local Ollama, no API key is needed - just ensure the server is running at `http://localhost:11434`.

## Quick Start

```bash
# Use default model
nexus "your prompt"

# Specify model
nexus -m gpt-4o "your prompt"

# Include file contents
nexus -f file.txt "explain this"

# Pipe content
cat file.txt | nexus "summarize"

# Interactive chat
nexus chat --session myproject
```

## Commands

| Command | Description |
|---------|-------------|
| `nexus "prompt"` | Send a prompt |
| `nexus chat` | Interactive REPL |
| `nexus models` | List available models |
| `nexus providers` | Show configured providers |
| `nexus config` | Display configuration |
| `nexus -d [model]` | Set default model |
| `nexus sessions` | Manage conversations |
| `nexus prompts` | Manage prompt library |
| `nexus completion` | Setup shell completion |

## Configuration

Config stored at `~/.nexus/config.yaml`:

```yaml
providers:
  openai:
    api_key: ${OPENAI_API_KEY}
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
  ollama:
    base_url: http://localhost:11434
  openrouter:
    api_key: ${OPENROUTER_API_KEY}

defaults:
  provider: openai
  model: gpt-4o
  temperature: 0.7
  max_tokens: 2000
  stream: true
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with Ollama integration
NEXUS_OLLAMA_URL=http://localhost:11434 pytest

# Linting
ruff check .
ruff format .
```

## Architecture

```
nexus/
├── cli/           # Click CLI commands
├── core/          # App, ProviderManager, CompletionHandler
├── providers/     # AI provider implementations
├── config/        # ConfigManager and models
├── session/       # Session persistence
├── prompts/       # Prompt library
└── utils/         # Cache, logging, errors
```
