# CodeGuard - Coding Agent Harness

A coding agent harness with governance-first architecture. Built as part of the AI4SE final project.

**Live Demo:** https://你的域名.up.railway.app

## Architecture

CodeGuard implements a six-dimension agent harness:
- **Decision**: Agent main loop with context assembly, action parsing, and execution dispatch
- **Tools**: File I/O, shell execution, test running, code search
- **Memory**: Conversation history with token budget management, project-level convention persistence
- **Governance (Deep Dimension)**: Three-tier guardrail system (SAFE/HITL/BLOCK), HITL state machine, sandbox execution
- **Feedback**: Deterministic test/lint output parsers with structured feedback injection
- **Configuration**: YAML-based configuration with custom guardrail rules

## Quick Start

### Prerequisites

- Python 3.12+
- Docker (optional, for containerized deployment)

### Installation

```bash
pip install -e ".[dev]"
```

### API Key Setup

```bash
codeguard key set
# Enter your DeepSeek API key when prompted (hidden input)
```

Check status (never reveals full key):
```bash
codeguard key status
```

### Run Agent (CLI)

```bash
codeguard start /path/to/project
```

### Run WebUI

```bash
codeguard serve
# Open http://localhost:8080
```

## Docker

```bash
docker build -t codeguard .
docker run -p 8080:8080 -v $(pwd):/workspace codeguard
```

### API Key in Docker

**Recommended**: Configure key on host machine before running Docker:
```bash
codeguard key set  # on host
```

**Alternative**: Mount `.env` file (note: `.env` is plaintext):
```bash
docker run -p 8080:8080 -v $(pwd):/workspace -v .env:/app/.env codeguard
```

**Never**: Pass key via `-e` flag (enters shell history) or hardcode in Dockerfile.

## Security

### Credential Storage

- API keys stored in system keyring (Windows Credential Manager / macOS Keychain / Linux Secret Service)
- Never hardcoded in source code
- Never committed to git
- Log output sanitized (keys masked to first 4 + last 4 characters)

### Guardrails

- **BLOCK**: Auto-rejected dangerous actions (`rm -rf /`, `sudo`, `format`, `git push --force main`)
- **HITL_REQUIRED**: Pauses for human approval (package installation, writes outside project, git push)
- **SAFE**: Auto-executed (read files, run tests, search code)

## Testing

```bash
pytest -v
```

All core mechanisms are tested with MockLLM (no network, no real LLM required).

## Project Structure

```
CodeGuard/
├── codeguard/
│   ├── config.py       # YAML configuration loader
│   ├── llm.py          # LLM abstraction (DeepSeek + MockLLM)
│   ├── memory.py       # Conversation history + context builder
│   ├── tools.py        # Tool registry + 5 tool executors
│   ├── governance.py   # Guardrails, HITL state machine
│   ├── feedback.py     # Test/lint output parsers
│   ├── loop.py         # Agent main loop
│   ├── cli.py          # CLI entry point
│   └── web.py          # FastAPI WebUI + WebSocket
├── static/
│   └── index.html      # WebUI frontend
├── tests/              # Unit tests (all mock-LLM compatible)
├── Dockerfile
└── .github/workflows/ci.yml
```

## Known Limitations

- Docker image ~200MB (Python slim + dependencies)
- x86_64 architecture only
- Requires Docker Engine 20.10+
- Sandbox isolation depends on host filesystem permissions (not full container isolation)
- Guardrails are pattern-based, not behavioral (novel attack patterns may bypass)
- `.env` file fallback is plaintext on disk

## License

MIT