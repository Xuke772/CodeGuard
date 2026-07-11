# CodeGuard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a coding agent harness with a six-dimension architecture (decision/tools/memory/governance/feedback/configuration), with governance (guardrails/HITL/sandbox) as the deep contribution dimension.

**Architecture:** Python monolith with clearly separated core modules. Each module is a single file with a single responsibility. The agent loop orchestrates all modules. FastAPI serves the WebUI with WebSocket for real-time logs. Mock LLM enables deterministic unit testing of all mechanisms.

**Tech Stack:** Python 3.12, FastAPI, pytest, DeepSeek API (OpenAI-compatible), keyring, Docker

## File Structure

```
CodeGuard/
├── codeguard/
│   ├── __init__.py
│   ├── config.py           # YAML config loader
│   ├── llm.py              # LLM abstraction (DeepSeek + MockLLM)
│   ├── memory.py           # Conversation history + project rules
│   ├── tools.py            # Tool registry + execution
│   ├── governance.py       # Guardrails, HITL state machine, sandbox
│   ├── feedback.py         # Test/lint output parser
│   ├── loop.py             # Agent main loop
│   ├── cli.py              # CLI entry point
│   └── web.py              # FastAPI app + WebSocket
├── static/
│   └── index.html          # WebUI frontend
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_llm.py
│   ├── test_memory.py
│   ├── test_tools.py
│   ├── test_governance.py
│   ├── test_feedback.py
│   ├── test_loop.py
│   └── test_mechanisms.py  # Mechanism demonstrations
├── Dockerfile
├── requirements.txt
├── pyproject.toml
├── .gitignore
└── .github/workflows/ci.yml
```

## Global Constraints

- Python 3.12+
- All dependencies declared in requirements.txt with pinned versions
- Must use pytest for all tests
- All core mechanisms must be testable with MockLLM (no network, no real LLM)
- Must not hardcode any API keys or credentials
- Must follow TDD: write failing test first, then implementation
- Commit after each task with descriptive message

## Task Dependency Graph

```
Task 1 (scaffolding) ─────────────────────────────────────┐
Task 2 (config) ──────────────────────────────────────────┤
Task 3 (llm) ─────────────────────────────────────────────┤
Task 4 (memory) ──────────────────────────────────────────┤
Task 5 (tools) ───────────────────────────────────────────┤
Task 6 (governance) ──────────────────────────────────────┤
Task 7 (feedback) ────────────────────────────────────────┤
                                                          ▼
                                              Task 8 (loop) ──┬── Task 9 (cli)
                                                              ├── Task 10 (web)
                                                              └── Task 12 (mechanisms)
                                              Task 11 (webui) ── depends on Task 10
                                              Task 13 (docker+ci) ── depends on all
                                              Task 14 (readme) ── depends on all
```

Tasks 2-7 can be done in parallel (no cross-dependencies).

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`, `requirements.txt`, `.gitignore`, `codeguard/__init__.py`, `tests/__init__.py`, `tests/conftest.py`

**Interfaces:**
- Produces: project directory structure for all subsequent tasks

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[project]
name = "codeguard"
version = "0.1.0"
description = "A coding agent harness with governance-first architecture"
requires-python = ">=3.12"
dependencies = [
    "openai>=1.30.0",
    "pyyaml>=6.0",
    "keyring>=25.0.0",
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.30.0",
    "python-dotenv>=1.0.0",
    "tiktoken>=0.7.0",
]

[project.scripts]
codeguard = "codeguard.cli:main"

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23.0",
    "pytest-mock>=3.12.0",
]
```

- [ ] **Step 2: Create requirements.txt**

```
openai>=1.30.0
pyyaml>=6.0
keyring>=25.0.0
fastapi>=0.111.0
uvicorn[standard]>=0.30.0
python-dotenv>=1.0.0
tiktoken>=0.7.0
pytest>=8.0
pytest-asyncio>=0.23.0
pytest-mock>=3.12.0
```

- [ ] **Step 3: Create .gitignore**

```
__pycache__/
*.pyc
*.pyo
.env
.codeguard/rules.md
*.egg-info/
dist/
build/
.venv/
venv/
.pytest_cache/
```

- [ ] **Step 4: Create empty __init__.py files**

```python
# codeguard/__init__.py
```

```python
# tests/__init__.py
```

- [ ] **Step 5: Create tests/conftest.py**

```python
import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_project():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir) / "test_project"
        project_root.mkdir()
        yield project_root


@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
```

- [ ] **Step 6: Install dependencies and verify**

```bash
pip install -e ".[dev]"
```

- [ ] **Step 7: Run pytest to verify scaffolding works**

```bash
pytest -v
```

Expected: 0 tests collected (no tests yet, but runs without errors)

- [ ] **Step 8: Commit**

```bash
git init
git add -A
git commit -m "chore: project scaffolding"
```

---

### Task 2: Config Module

**Files:**
- Create: `codeguard/config.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Produces: `Config` dataclass, `load_config(path) -> Config`, `DEFAULT_CONFIG: Config`

- [ ] **Step 1: Write the failing test**

Create `tests/test_config.py`:

```python
import pytest
from codeguard.config import Config, LLMConfig, AgentConfig, GuardrailConfig, load_config


class TestConfigDefaults:
    def test_default_config_has_expected_values(self):
        config = Config()
        assert config.llm.provider == "deepseek"
        assert config.llm.model == "deepseek-chat"
        assert config.llm.temperature == 0.1
        assert config.agent.max_turns == 20
        assert config.agent.max_fix_attempts == 3
        assert config.agent.hitl_timeout == 60

    def test_default_config_guardrails_empty(self):
        config = Config()
        assert config.guardrails.custom_rules == []
        assert config.guardrails.blocked_patterns == []


class TestLoadConfig:
    def test_load_from_yaml_file(self, temp_workspace):
        yaml_content = """
llm:
  provider: openai
  model: gpt-4
  temperature: 0.5
agent:
  max_turns: 10
  max_fix_attempts: 2
  hitl_timeout: 30
guardrails:
  custom_rules:
    - pattern: "echo"
      risk_level: "BLOCK"
      description: "block echo"
  blocked_patterns:
    - "rm -rf"
"""
        config_path = temp_workspace / "config.yaml"
        config_path.write_text(yaml_content)
        config = load_config(config_path)
        assert config.llm.provider == "openai"
        assert config.llm.model == "gpt-4"
        assert config.agent.max_turns == 10
        assert len(config.guardrails.custom_rules) == 1
        assert config.guardrails.custom_rules[0].pattern == "echo"

    def test_load_nonexistent_file_returns_default(self):
        config = load_config("nonexistent.yaml")
        assert config.llm.provider == "deepseek"

    def test_partial_yaml_merges_with_defaults(self, temp_workspace):
        yaml_content = """
llm:
  model: custom-model
"""
        config_path = temp_workspace / "partial.yaml"
        config_path.write_text(yaml_content)
        config = load_config(config_path)
        assert config.llm.model == "custom-model"
        assert config.llm.provider == "deepseek"  # default preserved
        assert config.agent.max_turns == 20  # default preserved
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_config.py -v
```

Expected: FAIL, `ModuleNotFoundError: No module named 'codeguard.config'`

- [ ] **Step 3: Write minimal implementation**

Create `codeguard/config.py`:

```python
import yaml
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LLMConfig:
    provider: str = "deepseek"
    model: str = "deepseek-chat"
    api_base: str = "https://api.deepseek.com/v1"
    temperature: float = 0.1
    max_tokens: int = 4096


@dataclass
class AgentConfig:
    max_turns: int = 20
    max_fix_attempts: int = 3
    hitl_timeout: int = 60


@dataclass
class GuardrailRule:
    pattern: str = ""
    risk_level: str = "BLOCK"
    description: str = ""


@dataclass
class GuardrailConfig:
    custom_rules: list[GuardrailRule] = field(default_factory=list)
    blocked_patterns: list[str] = field(default_factory=list)


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    guardrails: GuardrailConfig = field(default_factory=GuardrailConfig)


def load_config(path: str | Path | None = None) -> Config:
    config = Config()
    if path is None:
        path = Path(".codeguard") / "config.yaml"
    path = Path(path)
    if not path.exists():
        return config
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}
    if "llm" in data:
        for key, value in data["llm"].items():
            if hasattr(config.llm, key):
                setattr(config.llm, key, value)
    if "agent" in data:
        for key, value in data["agent"].items():
            if hasattr(config.agent, key):
                setattr(config.agent, key, value)
    if "guardrails" in data:
        g = data["guardrails"]
        if "custom_rules" in g:
            config.guardrails.custom_rules = [
                GuardrailRule(**r) for r in g["custom_rules"]
            ]
        if "blocked_patterns" in g:
            config.guardrails.blocked_patterns = g["blocked_patterns"]
    return config
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_config.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add codeguard/config.py tests/test_config.py
git commit -m "feat: add config module with YAML loading"
```

---

### Task 3: LLM Abstraction Layer

**Files:**
- Create: `codeguard/llm.py`
- Create: `tests/test_llm.py`

**Interfaces:**
- Consumes: `Config` from Task 2
- Produces: `LLMAdapter` abstract base, `DeepSeekAdapter(LLMAdapter)`, `MockLLM(LLMAdapter)`, `LLMResponse` dataclass

- [ ] **Step 1: Write the failing test**

Create `tests/test_llm.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from codeguard.llm import LLMResponse, MockLLM, DeepSeekAdapter, Message
from codeguard.config import Config


class TestLLMResponse:
    def test_response_creation(self):
        resp = LLMResponse(content="Hello", finish_reason="stop")
        assert resp.content == "Hello"
        assert resp.finish_reason == "stop"

    def test_response_defaults(self):
        resp = LLMResponse(content="test")
        assert resp.content == "test"
        assert resp.finish_reason == "stop"


class TestMockLLM:
    def test_mock_returns_configured_response(self):
        mock = MockLLM(responses=["action: write_file"])
        resp = mock.chat([Message(role="user", content="create a file")])
        assert resp.content == "action: write_file"
        assert resp.finish_reason == "stop"

    def test_mock_cycles_through_responses(self):
        mock = MockLLM(responses=["first", "second", "third"])
        assert mock.chat([Message(role="user", content="hi")]).content == "first"
        assert mock.chat([Message(role="user", content="hi")]).content == "second"
        assert mock.chat([Message(role="user", content="hi")]).content == "third"

    def test_mock_repeats_last_response(self):
        mock = MockLLM(responses=["only"])
        assert mock.chat([Message(role="user", content="q1")]).content == "only"
        assert mock.chat([Message(role="user", content="q2")]).content == "only"

    def test_mock_call_history(self):
        mock = MockLLM(responses=["a", "b"])
        mock.chat([Message(role="user", content="q1")])
        mock.chat([Message(role="user", content="q2")])
        assert len(mock.call_history) == 2
        assert mock.call_history[0][0].content == "q1"
        assert mock.call_history[1][0].content == "q2"

    def test_mock_empty_responses(self):
        mock = MockLLM()
        resp = mock.chat([Message(role="user", content="test")])
        assert resp.content == "FINISH"
        assert resp.finish_reason == "stop"


class TestMessage:
    def test_message_to_dict(self):
        msg = Message(role="user", content="hello")
        d = msg.to_dict()
        assert d == {"role": "user", "content": "hello"}

    def test_message_creation(self):
        msg = Message(role="assistant", content="response")
        assert msg.role == "assistant"
        assert msg.content == "response"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_llm.py -v
```

Expected: FAIL, `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

Create `codeguard/llm.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMResponse:
    content: str
    finish_reason: str = "stop"


@dataclass
class Message:
    role: str
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


class LLMAdapter(ABC):
    @abstractmethod
    def chat(self, messages: list[Message]) -> LLMResponse:
        ...


class MockLLM(LLMAdapter):
    def __init__(self, responses: list[str] | None = None):
        self.responses = responses or []
        self._index = 0
        self.call_history: list[list[Message]] = []

    def chat(self, messages: list[Message]) -> LLMResponse:
        self.call_history.append(messages)
        if not self.responses:
            return LLMResponse(content="FINISH", finish_reason="stop")
        response = self.responses[self._index]
        if self._index < len(self.responses) - 1:
            self._index += 1
        return LLMResponse(content=response, finish_reason="stop")


class DeepSeekAdapter(LLMAdapter):
    def __init__(self, config):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.llm.api_base,
        )
        self.model = config.llm.model
        self.temperature = config.llm.temperature
        self.max_tokens = config.llm.max_tokens

    def chat(self, messages: list[Message]) -> LLMResponse:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            finish_reason=choice.finish_reason or "stop",
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_llm.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add codeguard/llm.py tests/test_llm.py
git commit -m "feat: add LLM abstraction with MockLLM and DeepSeekAdapter"
```

---

### Task 4: Memory Module

**Files:**
- Create: `codeguard/memory.py`
- Create: `tests/test_memory.py`

**Interfaces:**
- Produces: `Message` dataclass (relocated), `Memory` class, `ContextBuilder` class

- [ ] **Step 1: Write the failing test**

Create `tests/test_memory.py`:

```python
import pytest
from codeguard.memory import Memory, ContextBuilder, Message


class TestMemory:
    def test_add_and_get_messages(self):
        mem = Memory()
        mem.add(Message(role="user", content="hello"))
        mem.add(Message(role="assistant", content="hi"))
        messages = mem.get_messages()
        assert len(messages) == 2
        assert messages[0].content == "hello"
        assert messages[1].content == "hi"

    def test_clear_messages(self):
        mem = Memory()
        mem.add(Message(role="user", content="test"))
        mem.clear()
        assert len(mem.get_messages()) == 0

    def test_token_count_estimation(self):
        mem = Memory()
        assert mem.estimate_tokens() == 0
        mem.add(Message(role="user", content="hello world"))
        assert mem.estimate_tokens() > 0

    def test_trim_excess_messages(self):
        mem = Memory(max_tokens=100)
        for i in range(50):
            mem.add(Message(role="user", content=f"message number {i} with some extra text"))
        mem.trim()
        assert len(mem.get_messages()) < 50

    def test_load_project_rules(self, temp_project):
        rules_file = temp_project / ".codeguard" / "rules.md"
        rules_file.parent.mkdir(parents=True)
        rules_file.write_text("# Project Rules\n- Use tabs\n- No semicolons")
        mem = Memory(project_root=temp_project)
        assert "Use tabs" in mem.project_rules

    def test_no_rules_file_returns_empty(self, temp_project):
        mem = Memory(project_root=temp_project)
        assert mem.project_rules == ""


class TestContextBuilder:
    def test_build_system_prompt(self):
        memory = Memory()
        memory.project_rules = "Use tabs"
        builder = ContextBuilder(memory)
        prompt = builder.build_system_prompt()
        assert "Use tabs" in prompt
        assert "coding agent" in prompt.lower()

    def test_build_context_includes_task(self):
        memory = Memory()
        memory.add(Message(role="user", content="previous question"))
        memory.add(Message(role="assistant", content="previous answer"))
        builder = ContextBuilder(memory)
        messages = builder.build_context("new task")
        assert len(messages) >= 3  # system + history + task
        assert messages[-1].content == "new task"
        assert messages[0].role == "system"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_memory.py -v
```

Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Create `codeguard/memory.py`:

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Message:
    role: str
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


class Memory:
    def __init__(self, project_root: Path | None = None, max_tokens: int = 8000):
        self._messages: list[Message] = []
        self.max_tokens = max_tokens
        self.project_root = project_root
        self.project_rules = self._load_project_rules()

    def add(self, message: Message) -> None:
        self._messages.append(message)

    def get_messages(self) -> list[Message]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    def estimate_tokens(self) -> int:
        total = 0
        for msg in self._messages:
            total += len(msg.content) // 4
        return total

    def trim(self) -> None:
        while self.estimate_tokens() > self.max_tokens and len(self._messages) > 2:
            self._messages.pop(1)

    def _load_project_rules(self) -> str:
        if self.project_root is None:
            return ""
        rules_path = Path(self.project_root) / ".codeguard" / "rules.md"
        if not rules_path.exists():
            return ""
        return rules_path.read_text(encoding="utf-8")


class ContextBuilder:
    def __init__(self, memory: Memory):
        self.memory = memory

    def build_system_prompt(self) -> str:
        prompt = """You are a coding agent. You can perform actions to help the user with software engineering tasks.

Available actions:
- read_file(path): Read a file's contents
- write_file(path, content): Write content to a file
- execute_shell(command): Execute a shell command
- run_tests(): Run the test suite
- search_code(pattern): Search code with ripgrep

Respond with ONE action per turn in this format:
ACTION: <action_name>
PARAMS: <json_params>

When the task is complete, respond with:
ACTION: FINISH
PARAMS: {"summary": "what was done"}
"""
        if self.memory.project_rules:
            prompt += f"\n\nProject Rules:\n{self.memory.project_rules}"
        return prompt

    def build_context(self, task: str) -> list[Message]:
        messages: list[Message] = []
        messages.append(Message(role="system", content=self.build_system_prompt()))
        for msg in self.memory.get_messages():
            messages.append(msg)
        messages.append(Message(role="user", content=task))
        return messages
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_memory.py -v
```

Expected: PASS

- [ ] **Step 5: Update llm.py to remove duplicate Message**

Remove the `Message` class from `codeguard/llm.py` and import it from `codeguard/memory.py` instead.

- [ ] **Step 6: Commit**

```bash
git add codeguard/memory.py codeguard/llm.py tests/test_memory.py
git commit -m "feat: add memory module with context builder"
```

---

### Task 5: Tools Module

**Files:**
- Create: `codeguard/tools.py`
- Create: `tests/test_tools.py`

**Interfaces:**
- Produces: `ToolDef` dataclass, `ToolRegistry` class, `ToolResult` dataclass, `execute_read_file`, `execute_write_file`, `execute_shell`, `execute_run_tests`, `execute_search_code`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tools.py`:

```python
import pytest
import subprocess
from unittest.mock import patch, MagicMock
from codeguard.tools import (
    ToolDef, ToolRegistry, ToolResult, RiskLevel,
    execute_read_file, execute_write_file, execute_shell,
    execute_run_tests, execute_search_code,
)


class TestToolDef:
    def test_tool_def_creation(self):
        tool = ToolDef(
            name="read_file",
            description="Read a file",
            parameters={"path": "str"},
            risk_level=RiskLevel.SAFE,
        )
        assert tool.name == "read_file"
        assert tool.risk_level == RiskLevel.SAFE


class TestToolRegistry:
    def test_register_and_get_tool(self):
        registry = ToolRegistry()
        tool = ToolDef(name="test_tool", description="test", parameters={}, risk_level=RiskLevel.SAFE)
        registry.register(tool, lambda **kwargs: ToolResult(success=True, output="ok"))
        assert registry.get("test_tool") is not None
        assert registry.get("nonexistent") is None

    def test_list_tools(self):
        registry = ToolRegistry()
        tool = ToolDef(name="t1", description="d1", parameters={}, risk_level=RiskLevel.SAFE)
        registry.register(tool, lambda **kwargs: ToolResult(success=True, output=""))
        assert "t1" in registry.list_tools()

    def test_get_tool_risk_level(self):
        registry = ToolRegistry()
        tool = ToolDef(name="dangerous", description="d", parameters={}, risk_level=RiskLevel.HITL_REQUIRED)
        registry.register(tool, lambda **kwargs: ToolResult(success=True, output=""))
        result = registry.execute("dangerous", {})
        assert result.success
        assert result.risk_level == RiskLevel.HITL_REQUIRED


class TestReadFile:
    def test_read_existing_file(self, temp_workspace):
        file_path = temp_workspace / "test.txt"
        file_path.write_text("hello world")
        result = execute_read_file(str(file_path))
        assert result.success
        assert result.output == "hello world"

    def test_read_nonexistent_file(self):
        result = execute_read_file("/nonexistent/path.txt")
        assert not result.success
        assert "error" in result.output.lower()


class TestWriteFile:
    def test_write_file(self, temp_workspace):
        file_path = temp_workspace / "output.txt"
        result = execute_write_file(str(file_path), "new content")
        assert result.success
        assert file_path.read_text() == "new content"

    def test_write_file_creates_directories(self, temp_workspace):
        file_path = temp_workspace / "subdir" / "nested" / "file.txt"
        result = execute_write_file(str(file_path), "nested content")
        assert result.success
        assert file_path.read_text() == "nested content"


class TestExecuteShell:
    @patch("subprocess.run")
    def test_execute_shell_success(self, mock_run):
        mock_run.return_value = MagicMock(stdout="output", stderr="", returncode=0)
        result = execute_shell("echo hello")
        assert result.success
        assert result.output == "output"

    @patch("subprocess.run")
    def test_execute_shell_failure(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", stderr="error msg", returncode=1)
        result = execute_shell("bad_command")
        assert not result.success
        assert "error msg" in result.output

    @patch("subprocess.run")
    def test_execute_shell_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)
        result = execute_shell("slow_command", timeout=30)
        assert not result.success
        assert "timeout" in result.output.lower()


class TestExecuteRunTests:
    @patch("subprocess.run")
    def test_run_tests_pytest(self, mock_run):
        mock_run.return_value = MagicMock(stdout="1 passed", stderr="", returncode=0)
        result = execute_run_tests()
        assert result.success
        assert "passed" in result.output

    @patch("subprocess.run")
    def test_run_tests_failure(self, mock_run):
        mock_run.return_value = MagicMock(stdout="1 failed", stderr="", returncode=1)
        result = execute_run_tests()
        assert not result.success
        assert "failed" in result.output


class TestExecuteSearchCode:
    @patch("subprocess.run")
    def test_search_code_found(self, mock_run):
        mock_run.return_value = MagicMock(stdout="file.py:10:def test():", stderr="", returncode=0)
        result = execute_search_code("def test")
        assert result.success
        assert "file.py" in result.output

    @patch("subprocess.run")
    def test_search_code_not_found(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=1)
        result = execute_search_code("nonexistent")
        assert result.success
        assert "no matches" in result.output.lower()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_tools.py -v
```

Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Create `codeguard/tools.py`:

```python
import subprocess
import json
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from typing import Callable, Any


class RiskLevel(str, Enum):
    SAFE = "SAFE"
    HITL_REQUIRED = "HITL_REQUIRED"
    BLOCK = "BLOCK"


@dataclass
class ToolResult:
    success: bool
    output: str
    risk_level: RiskLevel = RiskLevel.SAFE


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict
    risk_level: RiskLevel = RiskLevel.SAFE


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDef] = {}
        self._handlers: dict[str, Callable] = {}

    def register(self, tool_def: ToolDef, handler: Callable[..., ToolResult]) -> None:
        self._tools[tool_def.name] = tool_def
        self._handlers[tool_def.name] = handler

    def get(self, name: str) -> ToolDef | None:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def execute(self, name: str, params: dict) -> ToolResult:
        handler = self._handlers.get(name)
        if handler is None:
            return ToolResult(success=False, output=f"Unknown tool: {name}")
        try:
            result = handler(**params)
            if name in self._tools:
                result.risk_level = self._tools[name].risk_level
            return result
        except Exception as e:
            return ToolResult(success=False, output=f"Tool execution error: {e}")


def execute_read_file(path: str) -> ToolResult:
    try:
        p = Path(path)
        if not p.exists():
            return ToolResult(success=False, output=f"File not found: {path}")
        content = p.read_text(encoding="utf-8", errors="replace")
        return ToolResult(success=True, output=content)
    except Exception as e:
        return ToolResult(success=False, output=f"Error reading file: {e}")


def execute_write_file(path: str, content: str) -> ToolResult:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return ToolResult(success=True, output=f"File written: {path}")
    except Exception as e:
        return ToolResult(success=False, output=f"Error writing file: {e}")


def execute_shell(command: str, cwd: str | None = None, timeout: int = 30) -> ToolResult:
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )
        output = result.stdout
        if result.stderr:
            output += "\n[stderr]\n" + result.stderr
        if result.returncode != 0:
            return ToolResult(success=False, output=output.strip())
        return ToolResult(success=True, output=output.strip())
    except subprocess.TimeoutExpired:
        return ToolResult(success=False, output=f"Command timed out after {timeout}s")
    except Exception as e:
        return ToolResult(success=False, output=f"Error executing command: {e}")


def execute_run_tests(command: str | None = None) -> ToolResult:
    cmd = command or "python -m pytest"
    return execute_shell(cmd)


def execute_search_code(pattern: str, path: str = ".") -> ToolResult:
    try:
        cmd = f'rg --line-number "{pattern}" {path}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 1 and not result.stdout:
            return ToolResult(success=True, output="No matches found.")
        if result.returncode != 0 and result.returncode != 1:
            return ToolResult(success=False, output=result.stderr)
        return ToolResult(success=True, output=result.stdout.strip())
    except subprocess.TimeoutExpired:
        return ToolResult(success=False, output="Search timed out")
    except FileNotFoundError:
        return ToolResult(success=True, output="No matches found (rg not installed).")


def create_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDef("read_file", "Read a file's contents", {"path": "str"}, RiskLevel.SAFE),
        execute_read_file,
    )
    registry.register(
        ToolDef("write_file", "Write content to a file", {"path": "str", "content": "str"}, RiskLevel.HITL_REQUIRED),
        execute_write_file,
    )
    registry.register(
        ToolDef("execute_shell", "Execute a shell command", {"command": "str", "cwd": "str|None"}, RiskLevel.HITL_REQUIRED),
        execute_shell,
    )
    registry.register(
        ToolDef("run_tests", "Run the test suite", {"command": "str|None"}, RiskLevel.SAFE),
        execute_run_tests,
    )
    registry.register(
        ToolDef("search_code", "Search code with ripgrep", {"pattern": "str", "path": "str"}, RiskLevel.SAFE),
        execute_search_code,
    )
    return registry
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_tools.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add codeguard/tools.py tests/test_tools.py
git commit -m "feat: add tools module with registry and 5 tool executors"
```

---

### Task 6: Governance Module ★ (Deep Dimension)

**Files:**
- Create: `codeguard/governance.py`
- Create: `tests/test_governance.py`

**Interfaces:**
- Consumes: `RiskLevel` from `codeguard/tools.py`
- Produces: `classify_command(cmd: str) -> RiskLevel`, `classify_file_path(path: str, project_root: str) -> RiskLevel`, `HITLStateMachine`, `ApprovalRequest` dataclass, `GuardrailEngine`

- [ ] **Step 1: Write the failing test**

Create `tests/test_governance.py`:

```python
import pytest
import time
from codeguard.governance import (
    classify_command, classify_file_path, HITLStateMachine,
    HITLStatus, ApprovalRequest, GuardrailEngine,
)
from codeguard.tools import RiskLevel


class TestClassifyCommand:
    def test_rm_rf_root_is_blocked(self):
        assert classify_command("rm -rf /") == RiskLevel.BLOCK

    def test_rm_rf_home_is_blocked(self):
        assert classify_command("rm -rf ~") == RiskLevel.BLOCK

    def test_rm_rf_local_is_hitl(self):
        assert classify_command("rm -rf ./temp") == RiskLevel.HITL_REQUIRED

    def test_format_is_blocked(self):
        assert classify_command("format C:") == RiskLevel.BLOCK

    def test_sudo_is_blocked(self):
        assert classify_command("sudo rm file.txt") == RiskLevel.BLOCK

    def test_git_push_force_main_is_blocked(self):
        assert classify_command("git push --force origin main") == RiskLevel.BLOCK
        assert classify_command("git push -f origin master") == RiskLevel.BLOCK

    def test_git_push_normal_is_hitl(self):
        assert classify_command("git push origin feature") == RiskLevel.HITL_REQUIRED

    def test_chmod_recursive_is_blocked(self):
        assert classify_command("chmod -R 777 /") == RiskLevel.BLOCK

    def test_pip_install_is_hitl(self):
        assert classify_command("pip install requests") == RiskLevel.HITL_REQUIRED

    def test_safe_commands_are_safe(self):
        assert classify_command("ls -la") == RiskLevel.SAFE
        assert classify_command("pytest -v") == RiskLevel.SAFE
        assert classify_command("cat README.md") == RiskLevel.SAFE
        assert classify_command("echo hello") == RiskLevel.SAFE

    def test_empty_command_is_safe(self):
        assert classify_command("") == RiskLevel.SAFE


class TestClassifyFilePath:
    def test_system_paths_blocked(self):
        assert classify_file_path("/etc/passwd", "/home/project") == RiskLevel.BLOCK
        assert classify_file_path("/etc/shadow", "/home/project") == RiskLevel.BLOCK

    def test_env_file_blocked(self):
        assert classify_file_path("/home/project/.env", "/home/project") == RiskLevel.BLOCK
        assert classify_file_path(".env", "/home/project") == RiskLevel.BLOCK

    def test_credentials_file_blocked(self):
        assert classify_file_path("credentials.json", "/home/project") == RiskLevel.BLOCK
        assert classify_file_path("secrets.yaml", "/home/project") == RiskLevel.BLOCK

    def test_in_project_path_safe(self):
        assert classify_file_path("/home/project/src/main.py", "/home/project") == RiskLevel.SAFE
        assert classify_file_path("src/main.py", "/home/project") == RiskLevel.SAFE

    def test_outside_project_path_hitl(self):
        assert classify_file_path("/other/path/file.txt", "/home/project") == RiskLevel.HITL_REQUIRED


class TestHITLStateMachine:
    def test_initial_state_is_idle(self):
        sm = HITLStateMachine()
        assert sm.status == HITLStatus.IDLE

    def test_request_approval_transitions_to_awaiting(self):
        sm = HITLStateMachine()
        req = sm.request_approval("test_action", {"cmd": "ls"}, "Low risk")
        assert sm.status == HITLStatus.AWAITING_APPROVAL
        assert req is not None
        assert req.action_name == "test_action"
        assert req.status == HITLStatus.AWAITING_APPROVAL

    def test_approve_transitions_to_approved(self):
        sm = HITLStateMachine()
        req = sm.request_approval("test", {}, "risk")
        sm.approve()
        assert sm.status == HITLStatus.APPROVED
        assert sm.pending_request.status == HITLStatus.APPROVED

    def test_deny_transitions_to_denied(self):
        sm = HITLStateMachine()
        req = sm.request_approval("test", {}, "risk")
        sm.deny()
        assert sm.status == HITLStatus.DENIED
        assert sm.pending_request.status == HITLStatus.DENIED

    def test_reset_returns_to_idle(self):
        sm = HITLStateMachine()
        sm.request_approval("test", {}, "risk")
        sm.approve()
        sm.reset()
        assert sm.status == HITLStatus.IDLE
        assert sm.pending_request is None

    def test_timeout_transitions_to_denied(self):
        sm = HITLStateMachine(timeout=0.1)
        sm.request_approval("test", {}, "risk")
        time.sleep(0.2)
        result = sm.check_timeout()
        assert result is True
        assert sm.status == HITLStatus.DENIED

    def test_cannot_approve_when_idle(self):
        sm = HITLStateMachine()
        with pytest.raises(ValueError):
            sm.approve()

    def test_cannot_deny_when_idle(self):
        sm = HITLStateMachine()
        with pytest.raises(ValueError):
            sm.deny()


class TestGuardrailEngine:
    def test_evaluate_action_safe(self):
        engine = GuardrailEngine()
        result = engine.evaluate("read_file", {"path": "src/main.py"}, "/project")
        assert result == RiskLevel.SAFE

    def test_evaluate_action_hitl(self):
        engine = GuardrailEngine()
        result = engine.evaluate("write_file", {"path": "/other/file.txt"}, "/project")
        assert result == RiskLevel.HITL_REQUIRED

    def test_evaluate_action_block(self):
        engine = GuardrailEngine()
        result = engine.evaluate("execute_shell", {"command": "rm -rf /"}, "/project")
        assert result == RiskLevel.BLOCK

    def test_evaluate_unknown_tool_safe(self):
        engine = GuardrailEngine()
        result = engine.evaluate("unknown_tool", {}, "/project")
        assert result == RiskLevel.HITL_REQUIRED

    def test_custom_rule_added(self):
        engine = GuardrailEngine()
        engine.add_rule("echo hello", RiskLevel.BLOCK, "custom block")
        result = engine.evaluate("execute_shell", {"command": "echo hello"}, "/project")
        assert result == RiskLevel.BLOCK

    def test_safe_tool_no_command_override(self):
        engine = GuardrailEngine()
        result = engine.evaluate("read_file", {"path": "test.py"}, "/project")
        assert result == RiskLevel.SAFE
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_governance.py -v
```

Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Create `codeguard/governance.py`:

```python
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from codeguard.tools import RiskLevel


class HITLStatus(str, Enum):
    IDLE = "IDLE"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    DENIED = "DENIED"


@dataclass
class ApprovalRequest:
    action_name: str
    action_params: dict
    risk_detail: str
    status: HITLStatus = HITLStatus.AWAITING_APPROVAL
    timestamp: float = field(default_factory=time.time)


BLOCKED_COMMANDS = [
    (r"rm\s+-rf\s+/", "Recursive delete of root filesystem"),
    (r"rm\s+-rf\s+~", "Recursive delete of home directory"),
    (r"rm\s+-rf\s+\$HOME", "Recursive delete of home directory"),
    (r"format\s+[A-Z]:", "Disk format command"),
    (r"\bsudo\b", "Superuser command"),
    (r"git\s+push\s+.*--force.*\b(main|master)\b", "Force push to main/master branch"),
    (r"git\s+push\s+-f\s+.*\b(main|master)\b", "Force push to main/master branch"),
    (r"chmod\s+.*777\s+/", "World-writable permission on root"),
    (r"chmod\s+-R\s+777", "Recursive world-writable permission"),
    (r">\s*/dev/sda", "Write to block device"),
    (r"dd\s+if=.*of=/dev/", "Write to block device with dd"),
    (r"mkfs\.", "Filesystem creation command"),
    (r":\(\)\s*\{\s*:\|:&\s*\};:", "Fork bomb"),
]

HITL_COMMANDS = [
    (r"rm\s+-rf", "Recursive delete"),
    (r"git\s+push", "Git push"),
    (r"pip\s+install", "Python package installation"),
    (r"npm\s+install", "Node package installation"),
    (r"curl\b.*\b-o\b", "Download file with curl"),
    (r"wget\b", "Download file with wget"),
    (r"\bdocker\b", "Docker command"),
    (r"git\s+commit", "Git commit"),
]

SENSITIVE_FILES = [
    ".env", ".env.local", ".env.production",
    "credentials.json", "credentials.yaml", "credentials.yml",
    "secrets.yaml", "secrets.yml", "secret.key",
    "id_rsa", "id_ed25519", "*.pem", "*.key",
]


def classify_command(command: str) -> RiskLevel:
    if not command or not command.strip():
        return RiskLevel.SAFE
    for pattern, _ in BLOCKED_COMMANDS:
        if re.search(pattern, command, re.IGNORECASE):
            return RiskLevel.BLOCK
    for pattern, _ in HITL_COMMANDS:
        if re.search(pattern, command, re.IGNORECASE):
            return RiskLevel.HITL_REQUIRED
    return RiskLevel.SAFE


def classify_file_path(path: str, project_root: str) -> RiskLevel:
    resolved = Path(path).resolve()
    try:
        proj = Path(project_root).resolve()
    except (OSError, TypeError):
        return RiskLevel.HITL_REQUIRED
    filename = resolved.name.lower()
    for sensitive in SENSITIVE_FILES:
        if sensitive.startswith("*."):
            if filename.endswith(sensitive[1:]):
                return RiskLevel.BLOCK
        elif filename == sensitive:
            return RiskLevel.BLOCK
    if str(resolved).startswith("/etc/") or str(resolved).startswith("/sys/") or str(resolved).startswith("/proc/"):
        return RiskLevel.BLOCK
    try:
        resolved.relative_to(proj)
        return RiskLevel.SAFE
    except ValueError:
        return RiskLevel.HITL_REQUIRED


class HITLStateMachine:
    def __init__(self, timeout: float = 60.0):
        self.status = HITLStatus.IDLE
        self.pending_request: ApprovalRequest | None = None
        self.timeout = timeout
        self._request_time: float = 0.0

    def request_approval(self, action_name: str, params: dict, risk_detail: str) -> ApprovalRequest:
        if self.status != HITLStatus.IDLE:
            raise ValueError(f"Cannot request approval in state {self.status}")
        self.status = HITLStatus.AWAITING_APPROVAL
        self._request_time = time.time()
        self.pending_request = ApprovalRequest(
            action_name=action_name,
            action_params=params,
            risk_detail=risk_detail,
        )
        return self.pending_request

    def approve(self) -> None:
        if self.status != HITLStatus.AWAITING_APPROVAL:
            raise ValueError(f"Cannot approve in state {self.status}")
        self.status = HITLStatus.APPROVED
        if self.pending_request:
            self.pending_request.status = HITLStatus.APPROVED

    def deny(self) -> None:
        if self.status != HITLStatus.AWAITING_APPROVAL:
            raise ValueError(f"Cannot deny in state {self.status}")
        self.status = HITLStatus.DENIED
        if self.pending_request:
            self.pending_request.status = HITLStatus.DENIED

    def check_timeout(self) -> bool:
        if self.status != HITLStatus.AWAITING_APPROVAL:
            return False
        if time.time() - self._request_time > self.timeout:
            self.status = HITLStatus.DENIED
            if self.pending_request:
                self.pending_request.status = HITLStatus.DENIED
            return True
        return False

    def reset(self) -> None:
        self.status = HITLStatus.IDLE
        self.pending_request = None
        self._request_time = 0.0


class GuardrailEngine:
    def __init__(self):
        self._custom_rules: list[tuple[str, RiskLevel, str]] = []
        self._tool_risk_levels: dict[str, RiskLevel] = {
            "read_file": RiskLevel.SAFE,
            "write_file": RiskLevel.HITL_REQUIRED,
            "execute_shell": RiskLevel.HITL_REQUIRED,
            "run_tests": RiskLevel.SAFE,
            "search_code": RiskLevel.SAFE,
        }

    def add_rule(self, pattern: str, risk_level: RiskLevel, description: str) -> None:
        self._custom_rules.append((pattern, risk_level, description))

    def evaluate(self, tool_name: str, params: dict, project_root: str) -> RiskLevel:
        if tool_name == "execute_shell":
            cmd = params.get("command", "")
            for pattern, risk_level, _ in self._custom_rules:
                if re.search(pattern, cmd, re.IGNORECASE):
                    return risk_level
            return classify_command(cmd)
        if tool_name == "write_file":
            path = params.get("path", "")
            return classify_file_path(path, project_root)
        return self._tool_risk_levels.get(tool_name, RiskLevel.HITL_REQUIRED)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_governance.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add codeguard/governance.py tests/test_governance.py
git commit -m "feat: add governance module with guardrails and HITL state machine"
```

---

### Task 7: Feedback Module

**Files:**
- Create: `codeguard/feedback.py`
- Create: `tests/test_feedback.py`

**Interfaces:**
- Produces: `FeedbackReport` dataclass, `TestResultParser`, `LintResultParser`, `FeedbackInjector`

- [ ] **Step 1: Write the failing test**

Create `tests/test_feedback.py`:

```python
import pytest
from codeguard.feedback import (
    FeedbackReport, TestResultParser, LintResultParser,
    FeedbackInjector, TestFailure,
)


pytest_output_pass = """
============================= test session starts ==============================
collected 3 items

test_example.py ...                                                      [100%]

============================== 3 passed in 0.05s ===============================
"""

pytest_output_fail = """
============================= test session starts ==============================
collected 3 items

test_example.py .F.                                                      [100%]

=================================== FAILURES ===================================
________________________________ test_add ____________________________________

    def test_add():
>       assert add(1, 2) == 4
E       assert 3 == 4

test_example.py:5: AssertionError
========================= 1 failed, 2 passed in 0.05s ==========================
"""

lint_output = """
src/main.py:10:1: F401 'os' imported but unused
src/main.py:25:80: E501 line too long (92 > 79 characters)
src/utils.py:5:1: F841 local variable 'x' is assigned to but never used
"""


class TestFeedbackReport:
    def test_clean_report(self):
        report = FeedbackReport(source="pytest", is_clean=True, summary="All good")
        assert report.is_clean
        assert report.source == "pytest"

    def test_dirty_report(self):
        report = FeedbackReport(
            source="pytest",
            is_clean=False,
            summary="1 failed",
            failures=[TestFailure(name="test_add", message="assert 3 == 4", file="test_example.py", line=5)],
        )
        assert not report.is_clean
        assert len(report.failures) == 1


class TestTestResultParser:
    def test_parse_passing_output(self):
        report = TestResultParser.parse(pytest_output_pass)
        assert report.is_clean
        assert "3 passed" in report.summary

    def test_parse_failing_output(self):
        report = TestResultParser.parse(pytest_output_fail)
        assert not report.is_clean
        assert "1 failed" in report.summary
        assert len(report.failures) == 1
        assert report.failures[0].name == "test_add"
        assert "assert 3 == 4" in report.failures[0].message

    def test_parse_empty_output(self):
        report = TestResultParser.parse("")
        assert report.is_clean


class TestLintResultParser:
    def test_parse_lint_output(self):
        report = LintResultParser.parse(lint_output)
        assert not report.is_clean
        assert len(report.failures) == 3
        assert report.failures[0].file == "src/main.py"
        assert report.failures[0].line == 10

    def test_parse_empty_lint_output(self):
        report = LintResultParser.parse("")
        assert report.is_clean

    def test_parse_clean_lint_output(self):
        report = LintResultParser.parse("All checks passed!")
        assert report.is_clean


class TestFeedbackInjector:
    def test_inject_feedback(self):
        report = FeedbackReport(
            source="pytest",
            is_clean=False,
            summary="1 test failed",
            failures=[TestFailure(name="test_add", message="assert 3 == 4", file="test_example.py", line=5)],
        )
        feedback = FeedbackInjector.inject(report)
        assert "test_add" in feedback
        assert "test_example.py" in feedback
        assert "assert 3 == 4" in feedback

    def test_inject_clean_feedback(self):
        report = FeedbackReport(source="pytest", is_clean=True, summary="All passed")
        feedback = FeedbackInjector.inject(report)
        assert "passed" in feedback.lower()

    def test_format_for_llm(self):
        report = FeedbackReport(
            source="pytest",
            is_clean=False,
            summary="1 failed",
            failures=[TestFailure(name="test_add", message="error", file="f.py", line=1)],
        )
        msg = FeedbackInjector.format_for_llm(report)
        assert "test_add" in msg
        assert "ACTION:" in msg
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_feedback.py -v
```

Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Create `codeguard/feedback.py`:

```python
import re
from dataclasses import dataclass, field


@dataclass
class TestFailure:
    name: str = ""
    message: str = ""
    file: str = ""
    line: int = 0


@dataclass
class FeedbackReport:
    source: str
    is_clean: bool
    summary: str
    failures: list[TestFailure] = field(default_factory=list)


class TestResultParser:
    @staticmethod
    def parse(output: str) -> FeedbackReport:
        if not output:
            return FeedbackReport(source="pytest", is_clean=True, summary="No test output")
        passed_match = re.search(r"(\d+)\s+passed", output)
        failed_match = re.search(r"(\d+)\s+failed", output)
        error_match = re.search(r"(\d+)\s+error", output)
        passed = int(passed_match.group(1)) if passed_match else 0
        failed = int(failed_match.group(1)) if failed_match else 0
        errors = int(error_match.group(1)) if error_match else 0
        total_failures = failed + errors
        if total_failures == 0 and passed > 0:
            return FeedbackReport(source="pytest", is_clean=True, summary=f"{passed} passed")
        failures = []
        failure_blocks = re.split(r"_+\s+", output)
        for block in failure_blocks[1:]:
            name_match = re.search(r"^\s*(\w+)", block, re.MULTILINE)
            line_match = re.search(r">\s+(.+?)$", block, re.MULTILINE)
            error_match = re.search(r"E\s+(.+?)$", block, re.MULTILINE)
            file_match = re.search(r"(\S+\.py):(\d+):", block)
            if name_match:
                f = TestFailure(name=name_match.group(1).strip())
                if error_match:
                    f.message = error_match.group(1).strip()
                if file_match:
                    f.file = file_match.group(1)
                    f.line = int(file_match.group(2))
                failures.append(f)
        return FeedbackReport(
            source="pytest",
            is_clean=False,
            summary=f"{total_failures} failed, {passed} passed",
            failures=failures,
        )


class LintResultParser:
    @staticmethod
    def parse(output: str) -> FeedbackReport:
        if not output.strip():
            return FeedbackReport(source="lint", is_clean=True, summary="No lint issues")
        if "passed" in output.lower() or "no issues" in output.lower():
            return FeedbackReport(source="lint", is_clean=True, summary="All checks passed")
        failures = []
        pattern = re.compile(r"^(.+?):(\d+):(\d+)?:?\s*(\w+)\s+(.+)$", re.MULTILINE)
        for match in pattern.finditer(output):
            failures.append(TestFailure(
                file=match.group(1),
                line=int(match.group(2)),
                name=match.group(4),
                message=match.group(5).strip(),
            ))
        if not failures:
            return FeedbackReport(source="lint", is_clean=True, summary="No lint issues")
        return FeedbackReport(
            source="lint",
            is_clean=False,
            summary=f"{len(failures)} lint issues found",
            failures=failures,
        )


class FeedbackInjector:
    @staticmethod
    def inject(report: FeedbackReport) -> str:
        if report.is_clean:
            return f"[{report.source}] {report.summary}. No action needed."
        lines = [f"[{report.source}] {report.summary}:"]
        for f in report.failures:
            location = f"{f.file}:{f.line}" if f.file else "unknown"
            lines.append(f"  - {f.name} at {location}: {f.message}")
        return "\n".join(lines)

    @staticmethod
    def format_for_llm(report: FeedbackReport) -> str:
        if report.is_clean:
            return FeedbackInjector.inject(report)
        lines = [FeedbackInjector.inject(report)]
        lines.append("\nPlease fix the above failures. Use the following actions to investigate and fix:")
        lines.append("1. read_file to examine the failing file")
        lines.append("2. write_file to apply the fix")
        lines.append("3. run_tests to verify the fix")
        return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_feedback.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add codeguard/feedback.py tests/test_feedback.py
git commit -m "feat: add feedback module with test/lint parsers"
```

---

### Task 8: Agent Loop

**Files:**
- Create: `codeguard/loop.py`
- Create: `tests/test_loop.py`

**Interfaces:**
- Consumes: `Config`, `LLMAdapter`, `Memory`, `ContextBuilder`, `ToolRegistry`, `GuardrailEngine`, `HITLStateMachine`, `FeedbackInjector`
- Produces: `Agent` class, `Action` dataclass, `ActionParser`

- [ ] **Step 1: Write the failing test**

Create `tests/test_loop.py`:

```python
import pytest
from unittest.mock import MagicMock
from pathlib import Path
from codeguard.loop import Agent, Action, ActionParser, AgentStatus
from codeguard.llm import MockLLM, LLMResponse
from codeguard.memory import Memory, Message
from codeguard.tools import create_default_registry
from codeguard.governance import GuardrailEngine, HITLStateMachine, HITLStatus
from codeguard.feedback import FeedbackInjector
from codeguard.config import Config


class TestActionParser:
    def test_parse_action_with_params(self):
        response = 'ACTION: write_file\nPARAMS: {"path": "test.py", "content": "print(1)"}'
        action = ActionParser.parse(response)
        assert action.name == "write_file"
        assert action.params == {"path": "test.py", "content": "print(1)"}

    def test_parse_finish_action(self):
        response = 'ACTION: FINISH\nPARAMS: {"summary": "done"}'
        action = ActionParser.parse(response)
        assert action.name == "FINISH"
        assert action.params == {"summary": "done"}

    def test_parse_action_no_params(self):
        response = 'ACTION: run_tests\nPARAMS: {}'
        action = ActionParser.parse(response)
        assert action.name == "run_tests"
        assert action.params == {}

    def test_parse_invalid_json_params(self):
        response = 'ACTION: test\nPARAMS: {invalid'
        action = ActionParser.parse(response)
        assert action.name == "test"
        assert action.params == {}

    def test_parse_no_action_found(self):
        response = "Just some text without action format"
        action = ActionParser.parse(response)
        assert action.name == "NOOP"
        assert action.params == {}


class TestAgent:
    def test_agent_completes_task_with_finish(self, temp_workspace):
        mock_llm = MockLLM(responses=[
            'ACTION: read_file\nPARAMS: {"path": "test.py"}',
            'ACTION: FINISH\nPARAMS: {"summary": "task done"}',
        ])
        agent = Agent(
            config=Config(),
            llm=mock_llm,
            tool_registry=create_default_registry(),
            guardrail=GuardrailEngine(),
            hitl=HITLStateMachine(),
            project_root=temp_workspace,
        )
        result = agent.run("write a test file")
        assert result["status"] == AgentStatus.COMPLETED
        assert result["turns"] == 2
        assert len(mock_llm.call_history) == 2

    def test_agent_handles_blocked_action(self, temp_workspace):
        mock_llm = MockLLM(responses=[
            'ACTION: execute_shell\nPARAMS: {"command": "rm -rf /"}',
            'ACTION: FINISH\nPARAMS: {"summary": "blocked"}',
        ])
        agent = Agent(
            config=Config(),
            llm=mock_llm,
            tool_registry=create_default_registry(),
            guardrail=GuardrailEngine(),
            hitl=HITLStateMachine(),
            project_root=temp_workspace,
        )
        result = agent.run("do something dangerous")
        assert result["turns"] == 2
        assert mock_llm.call_history[1][-1].content.startswith("BLOCKED")

    def test_agent_max_turns_exceeded(self, temp_workspace):
        responses = ['ACTION: read_file\nPARAMS: {"path": "test.py"}'] * 10
        mock_llm = MockLLM(responses=responses)
        config = Config()
        config.agent.max_turns = 3
        agent = Agent(
            config=config,
            llm=mock_llm,
            tool_registry=create_default_registry(),
            guardrail=GuardrailEngine(),
            hitl=HITLStateMachine(),
            project_root=temp_workspace,
        )
        result = agent.run("keep reading")
        assert result["status"] == AgentStatus.MAX_TURNS

    def test_agent_stops_on_consecutive_no_progress(self, temp_workspace):
        mock_llm = MockLLM(responses=[
            'ACTION: NOOP\nPARAMS: {}',
            'ACTION: NOOP\nPARAMS: {}',
            'ACTION: NOOP\nPARAMS: {}',
        ])
        agent = Agent(
            config=Config(),
            llm=mock_llm,
            tool_registry=create_default_registry(),
            guardrail=GuardrailEngine(),
            hitl=HITLStateMachine(),
            project_root=temp_workspace,
        )
        result = agent.run("do nothing")
        assert result["status"] == AgentStatus.NO_PROGRESS

    def test_agent_retries_on_llm_error(self, temp_workspace):
        class FailingThenOkLLM(MockLLM):
            def __init__(self):
                super().__init__(responses=["ok"])
                self._fail_count = 0

            def chat(self, messages):
                if self._fail_count < 2:
                    self._fail_count += 1
                    raise RuntimeError("API error")
                return super().chat(messages)

        mock_llm = FailingThenOkLLM()
        config = Config()
        agent = Agent(
            config=config,
            llm=mock_llm,
            tool_registry=create_default_registry(),
            guardrail=GuardrailEngine(),
            hitl=HITLStateMachine(),
            project_root=temp_workspace,
        )
        result = agent.run("test")
        assert result["status"] == AgentStatus.COMPLETED

    def test_agent_hitl_workflow(self, temp_workspace):
        mock_llm = MockLLM(responses=[
            'ACTION: write_file\nPARAMS: {"path": "outside/file.txt", "content": "data"}',
            'ACTION: FINISH\nPARAMS: {"summary": "done"}',
        ])
        hitl = HITLStateMachine()
        agent = Agent(
            config=Config(),
            llm=mock_llm,
            tool_registry=create_default_registry(),
            guardrail=GuardrailEngine(),
            hitl=hitl,
            project_root=temp_workspace,
        )
        result = agent.run("write file")
        assert result["status"] == AgentStatus.HITL_PENDING

    def test_agent_context_includes_history(self, temp_workspace):
        mock_llm = MockLLM(responses=[
            'ACTION: FINISH\nPARAMS: {"summary": "done"}',
        ])
        agent = Agent(
            config=Config(),
            llm=mock_llm,
            tool_registry=create_default_registry(),
            guardrail=GuardrailEngine(),
            hitl=HITLStateMachine(),
            project_root=temp_workspace,
        )
        agent.run("task")
        assert len(mock_llm.call_history[0]) >= 2
        assert mock_llm.call_history[0][0].role == "system"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_loop.py -v
```

Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Create `codeguard/loop.py`:

```python
import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from codeguard.llm import LLMAdapter, LLMResponse
from codeguard.memory import Memory, Message, ContextBuilder
from codeguard.tools import ToolRegistry, RiskLevel
from codeguard.governance import GuardrailEngine, HITLStateMachine, HITLStatus
from codeguard.feedback import FeedbackInjector, TestResultParser
from codeguard.config import Config


class AgentStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    MAX_TURNS = "MAX_TURNS"
    NO_PROGRESS = "NO_PROGRESS"
    HITL_PENDING = "HITL_PENDING"
    ERROR = "ERROR"


@dataclass
class Action:
    name: str
    params: dict = field(default_factory=dict)


class ActionParser:
    @staticmethod
    def parse(response: str) -> Action:
        action_match = re.search(r"ACTION:\s*(\S+)", response)
        if not action_match:
            return Action(name="NOOP")
        action_name = action_match.group(1).strip()
        params = {}
        params_match = re.search(r"PARAMS:\s*(\{.+?\})", response, re.DOTALL)
        if params_match:
            try:
                params = json.loads(params_match.group(1).strip())
            except json.JSONDecodeError:
                try:
                    params = json.loads(params_match.group(1).strip() + "}")
                except json.JSONDecodeError:
                    params = {}
        return Action(name=action_name, params=params)


class Agent:
    def __init__(
        self,
        config: Config,
        llm: LLMAdapter,
        tool_registry: ToolRegistry,
        guardrail: GuardrailEngine,
        hitl: HITLStateMachine,
        project_root: Path,
    ):
        self.config = config
        self.llm = llm
        self.tool_registry = tool_registry
        self.guardrail = guardrail
        self.hitl = hitl
        self.project_root = project_root
        self.memory = Memory(project_root=project_root)
        self.context_builder = ContextBuilder(self.memory)
        self._consecutive_no_progress = 0

    def run(self, task: str) -> dict:
        self.memory.clear()
        self._consecutive_no_progress = 0
        turn = 0
        while turn < self.config.agent.max_turns:
            turn += 1
            messages = self.context_builder.build_context(task)
            response = self._call_llm_with_retry(messages)
            if response is None:
                return {"status": AgentStatus.ERROR, "turns": turn, "error": "LLM call failed after retries"}
            action = ActionParser.parse(response.content)
            if action.name == "NOOP":
                self._consecutive_no_progress += 1
                if self._consecutive_no_progress >= 3:
                    return {"status": AgentStatus.NO_PROGRESS, "turns": turn}
                self.memory.add(Message(role="assistant", content=response.content))
                self.memory.add(Message(role="user", content="No action detected. Please respond with ACTION: format."))
                continue
            self._consecutive_no_progress = 0
            if action.name == "FINISH":
                self.memory.add(Message(role="assistant", content=response.content))
                return {"status": AgentStatus.COMPLETED, "turns": turn, "summary": action.params.get("summary", "")}
            risk_level = self.guardrail.evaluate(action.name, action.params, str(self.project_root))
            self.memory.add(Message(role="assistant", content=response.content))
            if risk_level == RiskLevel.BLOCK:
                feedback = f"BLOCKED: Action '{action.name}' with params {action.params} was blocked by safety guardrails. Do not attempt this action again. Try an alternative approach."
                self.memory.add(Message(role="user", content=feedback))
                continue
            if risk_level == RiskLevel.HITL_REQUIRED:
                self.hitl.request_approval(action.name, action.params, f"Risk level: {risk_level}")
                return {"status": AgentStatus.HITL_PENDING, "turns": turn, "action": action}
            result = self.tool_registry.execute(action.name, action.params)
            if action.name == "run_tests" and result.output:
                test_report = TestResultParser.parse(result.output)
                feedback = FeedbackInjector.format_for_llm(test_report)
                self.memory.add(Message(role="user", content=feedback))
            else:
                result_text = f"Result: {result.output}" if result.success else f"Error: {result.output}"
                self.memory.add(Message(role="user", content=result_text))
            task = "Continue working on the task based on the result above."
        return {"status": AgentStatus.MAX_TURNS, "turns": turn}

    def _call_llm_with_retry(self, messages: list[Message], max_retries: int = 3) -> LLMResponse | None:
        for attempt in range(max_retries):
            try:
                return self.llm.chat(messages)
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        return None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_loop.py -v
```

Expected: PASS

- [ ] **Step 5: Update llm.py to remove duplicate Message**

Remove the `Message` class from `codeguard/llm.py` and import it from `codeguard/memory.py`.

- [ ] **Step 6: Commit**

```bash
git add codeguard/loop.py codeguard/llm.py tests/test_loop.py
git commit -m "feat: add agent loop with action parsing and retry logic"
```

---

### Task 9: CLI Module

**Files:**
- Create: `codeguard/cli.py`

**Interfaces:**
- Consumes: `Agent`, `Config`, `load_config`, `GuardrailEngine`, `HITLStateMachine`, `ToolRegistry`, `create_default_registry`, `DeepSeekAdapter`
- Produces: `main()` CLI entry point

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from codeguard.cli import create_agent_from_config, get_api_key


class TestGetApiKey:
    @patch("codeguard.cli.keyring")
    def test_get_key_from_keyring(self, mock_keyring):
        mock_keyring.get_password.return_value = "test-key-123"
        key = get_api_key()
        assert key == "test-key-123"

    @patch("codeguard.cli.keyring")
    @patch("codeguard.cli.os")
    def test_get_key_from_env_fallback(self, mock_os, mock_keyring):
        mock_keyring.get_password.return_value = None
        mock_os.environ.get.return_value = "env-key-456"
        key = get_api_key()
        assert key == "env-key-456"

    @patch("codeguard.cli.keyring")
    @patch("codeguard.cli.os")
    def test_no_key_found_raises(self, mock_os, mock_keyring):
        mock_keyring.get_password.return_value = None
        mock_os.environ.get.return_value = None
        with pytest.raises(RuntimeError, match="API key not found"):
            get_api_key()


class TestCreateAgent:
    @patch("codeguard.cli.get_api_key")
    def test_create_agent_from_config(self, mock_get_key, temp_workspace):
        from codeguard.config import Config
        mock_get_key.return_value = "test-key"
        config = Config()
        agent = create_agent_from_config(config, temp_workspace)
        assert agent is not None
        assert agent.project_root == temp_workspace
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_cli.py -v
```

Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Create `codeguard/cli.py`:

```python
import os
import sys
import keyring
from pathlib import Path
from codeguard.config import Config, load_config
from codeguard.llm import DeepSeekAdapter
from codeguard.tools import create_default_registry
from codeguard.governance import GuardrailEngine, HITLStateMachine
from codeguard.loop import Agent

SERVICE_NAME = "codeguard"
ACCOUNT_NAME = "deepseek_api_key"


def get_api_key() -> str:
    key = keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
    if key:
        return key
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key:
        return key
    raise RuntimeError(
        "API key not found. Set it via:\n"
        "  codeguard key set\n"
        "  or set DEEPSEEK_API_KEY environment variable"
    )


def set_api_key(key: str) -> None:
    keyring.set_password(SERVICE_NAME, ACCOUNT_NAME, key)
    print("API key stored securely in system keyring.")


def get_key_status() -> str:
    key = keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
    if key:
        masked = key[:4] + "****" + key[-4:] if len(key) >= 8 else "****"
        return f"API key: configured ({masked})"
    return "API key: not configured"


def clear_api_key() -> None:
    try:
        keyring.delete_password(SERVICE_NAME, ACCOUNT_NAME)
        print("API key cleared from system keyring.")
    except keyring.errors.PasswordDeleteError:
        print("No API key was stored.")


def create_agent_from_config(config: Config, project_root: Path) -> Agent:
    api_key = get_api_key()
    return Agent(
        config=config,
        llm=DeepSeekAdapter(api_key=api_key, config=config),
        tool_registry=create_default_registry(),
        guardrail=GuardrailEngine(),
        hitl=HITLStateMachine(timeout=config.agent.hitl_timeout),
        project_root=project_root,
    )


def main():
    if len(sys.argv) < 2:
        print("Usage: codeguard <command> [args]")
        print("Commands: key <set|status|clear>, start, config")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "key":
        if len(sys.argv) < 3:
            print("Usage: codeguard key <set|status|clear>")
            sys.exit(1)
        sub = sys.argv[2]
        if sub == "set":
            import getpass
            key = getpass.getpass("Enter your DeepSeek API key: ")
            set_api_key(key)
        elif sub == "status":
            print(get_key_status())
        elif sub == "clear":
            clear_api_key()
        else:
            print(f"Unknown subcommand: {sub}")
            sys.exit(1)
    elif cmd == "start":
        project_root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()
        config = load_config()
        agent = create_agent_from_config(config, project_root)
        task = input("Enter your task: ")
        print("Agent is working...")
        result = agent.run(task)
        print(f"Agent finished with status: {result['status']}")
        print(f"Turns: {result['turns']}")
        if "summary" in result:
            print(f"Summary: {result['summary']}")
    elif cmd == "serve":
        from codeguard.web import create_app
        import uvicorn
        app = create_app()
        uvicorn.run(app, host="0.0.0.0", port=8080)
    elif cmd == "config":
        config_path = Path(".codeguard") / "config.yaml"
        if config_path.exists():
            print(config_path.read_text())
        else:
            print("No .codeguard/config.yaml found. Using defaults.")
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_cli.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add codeguard/cli.py tests/test_cli.py
git commit -m "feat: add CLI module with key management and agent runner"
```

---

### Task 10: Web Module (FastAPI + WebSocket)

**Files:**
- Create: `codeguard/web.py`

**Interfaces:**
- Consumes: `Agent`, `Config`, `create_agent_from_config`
- Produces: FastAPI app with REST endpoints and WebSocket

- [ ] **Step 1: Write the failing test**

Create `tests/test_web.py`:

```python
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from codeguard.web import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestWebAPI:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_create_session(self, client):
        response = client.post("/sessions", json={
            "task": "write a hello world program",
            "project_root": "/tmp/test"
        })
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data

    def test_list_sessions_empty(self, client):
        response = client.get("/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data

    def test_get_session_not_found(self, client):
        response = client.get("/sessions/nonexistent")
        assert response.status_code == 404

    def test_approve_action_not_found(self, client):
        response = client.post("/sessions/nonexistent/approve")
        assert response.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_web.py -v
```

Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Create `codeguard/web.py`:

```python
import uuid
import json
import asyncio
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from codeguard.config import Config, load_config
from codeguard.cli import create_agent_from_config
from codeguard.governance import HITLStatus


class TaskRequest(BaseModel):
    task: str
    project_root: str = "."


class Session:
    def __init__(self, session_id: str, task: str, project_root: str):
        self.id = session_id
        self.task = task
        self.project_root = Path(project_root)
        self.status = "running"
        self.logs: list[str] = []
        self.agent = None
        self.config = load_config()
        self.hitl_pending = False

    def start(self):
        self.agent = create_agent_from_config(self.config, self.project_root)
        self.logs.append(f"Session started. Task: {self.task}")
        result = self.agent.run(self.task)
        self.status = result["status"]
        self.logs.append(f"Agent finished with status: {result['status']}")
        if "summary" in result:
            self.logs.append(f"Summary: {result['summary']}")
        return result


sessions: dict[str, Session] = {}


def create_app() -> FastAPI:
    app = FastAPI(title="CodeGuard", description="Coding Agent Harness WebUI")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/sessions")
    async def create_session(req: TaskRequest):
        session_id = str(uuid.uuid4())[:8]
        session = Session(session_id, req.task, req.project_root)
        sessions[session_id] = session
        return {"session_id": session_id}

    @app.get("/sessions")
    async def list_sessions():
        return {"sessions": [
            {"id": s.id, "task": s.task, "status": s.status}
            for s in sessions.values()
        ]}

    @app.get("/sessions/{session_id}")
    async def get_session(session_id: str):
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "id": session.id,
            "task": session.task,
            "status": session.status,
            "logs": session.logs,
            "hitl_pending": session.hitl_pending,
        }

    @app.post("/sessions/{session_id}/approve")
    async def approve_action(session_id: str):
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.agent and session.agent.hitl.status == HITLStatus.AWAITING_APPROVAL:
            session.agent.hitl.approve()
            session.hitl_pending = False
            session.logs.append("HITL action approved by user")
            return {"status": "approved"}
        raise HTTPException(status_code=400, detail="No pending approval")

    @app.post("/sessions/{session_id}/deny")
    async def deny_action(session_id: str):
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.agent and session.agent.hitl.status == HITLStatus.AWAITING_APPROVAL:
            session.agent.hitl.deny()
            session.hitl_pending = False
            session.logs.append("HITL action denied by user")
            return {"status": "denied"}
        raise HTTPException(status_code=400, detail="No pending approval")

    @app.websocket("/ws/{session_id}")
    async def websocket_endpoint(websocket: WebSocket, session_id: str):
        await websocket.accept()
        session = sessions.get(session_id)
        if not session:
            await websocket.send_text("Session not found")
            await websocket.close()
            return
        try:
            while True:
                await websocket.receive_text()
                if session.logs:
                    await websocket.send_text(json.dumps({"logs": session.logs}))
                await asyncio.sleep(0.5)
        except WebSocketDisconnect:
            pass

    @app.get("/")
    async def index():
        static_path = Path(__file__).parent.parent / "static" / "index.html"
        if static_path.exists():
            return FileResponse(static_path)
        return {"message": "CodeGuard API is running. Place static/index.html for WebUI."}

    return app
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_web.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add codeguard/web.py tests/test_web.py
git commit -m "feat: add web module with FastAPI and WebSocket"
```

---

### Task 11: WebUI Frontend

**Files:**
- Create: `static/index.html`

**Interfaces:**
- Consumes: Web API from Task 10

- [ ] **Step 1: Create the WebUI HTML**

Create `static/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CodeGuard - Coding Agent Harness</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #c9d1d9; min-height: 100vh; }
.container { max-width: 900px; margin: 0 auto; padding: 20px; }
.header { background: #161b22; border-bottom: 1px solid #30363d; padding: 16px 20px; }
.header h1 { color: #58a6ff; font-size: 20px; }
.header span { color: #8b949e; font-size: 14px; }
.panel { background: #161b22; border: 1px solid #30363d; border-radius: 6px; margin-top: 16px; }
.panel-header { padding: 12px 16px; border-bottom: 1px solid #30363d; font-weight: 600; }
.panel-body { padding: 16px; }
.input-group { display: flex; gap: 8px; margin-bottom: 12px; }
.input-group input { flex: 1; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 8px 12px; color: #c9d1d9; font-size: 14px; }
.input-group input:focus { outline: none; border-color: #58a6ff; }
.btn { background: #238636; color: #fff; border: none; border-radius: 6px; padding: 8px 16px; cursor: pointer; font-size: 14px; }
.btn:hover { background: #2ea043; }
.btn-danger { background: #da3633; }
.btn-danger:hover { background: #f85149; }
.btn-warning { background: #d29922; }
.btn-warning:hover { background: #e3b341; }
.btn-group { display: flex; gap: 8px; margin-top: 12px; }
.logs { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 12px; max-height: 400px; overflow-y: auto; font-family: 'Consolas', monospace; font-size: 13px; line-height: 1.6; }
.log-entry { padding: 2px 0; }
.log-entry.blocked { color: #f85149; }
.log-entry.success { color: #3fb950; }
.log-entry.warning { color: #d29922; }
.status-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
.status-badge.running { background: #1f6feb33; color: #58a6ff; }
.status-badge.completed { background: #23863633; color: #3fb950; }
.status-badge.error { background: #da363333; color: #f85149; }
.hitl-panel { display: none; background: #1f2429; border: 1px solid #d29922; border-radius: 6px; padding: 16px; margin-top: 12px; }
.hitl-panel.active { display: block; }
</style>
</head>
<body>
<div class="header">
  <div class="container">
    <h1>CodeGuard <span>Coding Agent Harness</span></h1>
  </div>
</div>
<div class="container">
  <div class="panel">
    <div class="panel-header">Task Input</div>
    <div class="panel-body">
      <div class="input-group">
        <input type="text" id="taskInput" placeholder="Enter your coding task..." />
        <input type="text" id="projectInput" placeholder="Project root (default: .)" value="." style="max-width: 200px;" />
      </div>
      <button class="btn" onclick="startSession()">Start Agent</button>
    </div>
  </div>

  <div class="panel" id="statusPanel" style="display: none;">
    <div class="panel-header">Session <span id="sessionId"></span> — <span id="sessionStatus" class="status-badge"></span></div>
    <div class="panel-body">
      <div class="logs" id="logs"></div>
    </div>
  </div>

  <div class="hitl-panel" id="hitlPanel">
    <div class="panel-header" style="color: #d29922;">&#9888; Action Requires Approval</div>
    <div class="panel-body">
      <div id="hitlDetails"></div>
      <div class="btn-group">
        <button class="btn" onclick="approveAction()">Approve</button>
        <button class="btn btn-danger" onclick="denyAction()">Deny</button>
      </div>
    </div>
  </div>
</div>
<script>
let currentSessionId = null;
let ws = null;

async function startSession() {
  const task = document.getElementById('taskInput').value;
  const projectRoot = document.getElementById('projectInput').value;
  if (!task) return;
  const resp = await fetch('/sessions', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({task, project_root: projectRoot})
  });
  const data = await resp.json();
  currentSessionId = data.session_id;
  document.getElementById('statusPanel').style.display = 'block';
  document.getElementById('sessionId').textContent = '#' + currentSessionId;
  document.getElementById('sessionStatus').textContent = 'running';
  document.getElementById('sessionStatus').className = 'status-badge running';
  document.getElementById('logs').innerHTML = '';
  connectWebSocket();
}

function connectWebSocket() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${protocol}//${location.host}/ws/${currentSessionId}`);
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    renderLogs(data.logs || []);
  };
  ws.onclose = () => {
    fetch(`/sessions/${currentSessionId}`).then(r => r.json()).then(data => {
      const statusClass = data.status === 'COMPLETED' ? 'completed' : 'error';
      document.getElementById('sessionStatus').textContent = data.status;
      document.getElementById('sessionStatus').className = `status-badge ${statusClass}`;
      if (data.hitl_pending) showHitlPanel(data);
      renderLogs(data.logs);
    });
  };
}

function renderLogs(logs) {
  const container = document.getElementById('logs');
  container.innerHTML = logs.map(log => {
    let cls = '';
    if (log.includes('BLOCKED')) cls = 'blocked';
    else if (log.includes('passed') || log.includes('success')) cls = 'success';
    else if (log.includes('HITL')) cls = 'warning';
    return `<div class="log-entry ${cls}">${escapeHtml(log)}</div>`;
  }).join('');
  container.scrollTop = container.scrollHeight;
}

function showHitlPanel(data) {
  document.getElementById('hitlPanel').classList.add('active');
  document.getElementById('hitlDetails').innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
}

async function approveAction() {
  await fetch(`/sessions/${currentSessionId}/approve`, {method: 'POST'});
  document.getElementById('hitlPanel').classList.remove('active');
  connectWebSocket();
}

async function denyAction() {
  await fetch(`/sessions/${currentSessionId}/deny`, {method: 'POST'});
  document.getElementById('hitlPanel').classList.remove('active');
  connectWebSocket();
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
</script>
</body>
</html>
```

- [ ] **Step 2: Verify the file exists and is readable**

```bash
Test-Path static/index.html
```

Expected: True

- [ ] **Step 3: Commit**

```bash
git add static/index.html
git commit -m "feat: add WebUI frontend with dark theme"
```

---

### Task 12: Mechanism Demonstrations

**Files:**
- Create: `tests/test_mechanisms.py`

**Interfaces:**
- Consumes: All core modules from Tasks 1-8
- Produces: Three deterministic demonstrations (guardrail, feedback, governance deep)

- [ ] **Step 1: Write the mechanism demonstration tests**

Create `tests/test_mechanisms.py`:

```python
import pytest
from pathlib import Path
from codeguard.llm import MockLLM
from codeguard.tools import create_default_registry, RiskLevel
from codeguard.governance import GuardrailEngine, HITLStateMachine, HITLStatus, classify_command
from codeguard.feedback import TestResultParser, FeedbackInjector, FeedbackReport, TestFailure
from codeguard.loop import Agent, ActionParser, AgentStatus
from codeguard.config import Config


class TestDemo1Guardrail:
    def test_guardrail_blocks_rm_rf_root(self):
        engine = GuardrailEngine()
        result = engine.evaluate("execute_shell", {"command": "rm -rf /"}, "/project")
        assert result == RiskLevel.BLOCK

    def test_guardrail_blocks_format(self):
        engine = GuardrailEngine()
        result = engine.evaluate("execute_shell", {"command": "format C:"}, "/project")
        assert result == RiskLevel.BLOCK

    def test_guardrail_blocks_sudo(self):
        engine = GuardrailEngine()
        result = engine.evaluate("execute_shell", {"command": "sudo rm file.txt"}, "/project")
        assert result == RiskLevel.BLOCK

    def test_guardrail_blocks_git_push_force_main(self):
        engine = GuardrailEngine()
        result = engine.evaluate("execute_shell", {"command": "git push --force origin main"}, "/project")
        assert result == RiskLevel.BLOCK

    def test_guardrail_blocks_env_file_write(self):
        engine = GuardrailEngine()
        result = engine.evaluate("write_file", {"path": "/project/.env", "content": "SECRET=123"}, "/project")
        assert result == RiskLevel.BLOCK

    def test_guardrail_allows_safe_commands(self):
        engine = GuardrailEngine()
        assert engine.evaluate("execute_shell", {"command": "ls -la"}, "/project") == RiskLevel.SAFE
        assert engine.evaluate("execute_shell", {"command": "pytest -v"}, "/project") == RiskLevel.SAFE
        assert engine.evaluate("read_file", {"path": "src/main.py"}, "/project") == RiskLevel.SAFE

    def test_guardrail_hitl_for_moderate_risk(self):
        engine = GuardrailEngine()
        assert engine.evaluate("execute_shell", {"command": "pip install requests"}, "/project") == RiskLevel.HITL_REQUIRED
        assert engine.evaluate("write_file", {"path": "/other/file.txt", "content": "data"}, "/project") == RiskLevel.HITL_REQUIRED

    def test_hitl_state_machine_full_cycle(self):
        sm = HITLStateMachine(timeout=60)
        assert sm.status == HITLStatus.IDLE
        req = sm.request_approval("execute_shell", {"command": "pip install numpy"}, "Package installation")
        assert sm.status == HITLStatus.AWAITING_APPROVAL
        assert req.action_name == "execute_shell"
        sm.approve()
        assert sm.status == HITLStatus.APPROVED
        sm.reset()
        assert sm.status == HITLStatus.IDLE
        assert sm.pending_request is None

    def test_hitl_deny_and_timeout(self):
        import time
        sm = HITLStateMachine(timeout=0.05)
        sm.request_approval("test", {}, "risk")
        time.sleep(0.1)
        assert sm.check_timeout() is True
        assert sm.status == HITLStatus.DENIED


class TestDemo2FeedbackLoop:
    def test_feedback_loop_with_failing_test(self, temp_workspace):
        mock_llm = MockLLM(responses=[
            'ACTION: write_file\nPARAMS: {"path": "test_calc.py", "content": "def add(a, b): return a - b"}',
            'ACTION: run_tests\nPARAMS: {}',
            'ACTION: read_file\nPARAMS: {"path": "test_calc.py"}',
            'ACTION: write_file\nPARAMS: {"path": "test_calc.py", "content": "def add(a, b): return a + b"}',
            'ACTION: run_tests\nPARAMS: {}',
            'ACTION: FINISH\nPARAMS: {"summary": "fixed the add function"}',
        ])
        config = Config()
        config.agent.max_turns = 10
        agent = Agent(
            config=config,
            llm=mock_llm,
            tool_registry=create_default_registry(),
            guardrail=GuardrailEngine(),
            hitl=HITLStateMachine(),
            project_root=temp_workspace,
        )
        result = agent.run("implement add function")
        assert result["status"] == AgentStatus.COMPLETED
        call_contents = [msg.content for call in mock_llm.call_history for msg in call if msg.role == "user"]
        assert any("fix" in c.lower() or "test" in c.lower() for c in call_contents)

    def test_test_result_parser_failure(self):
        output = """
============================= test session starts ==============================
test_calc.py .F.                                                          [100%]
=================================== FAILURES ===================================
________________________________ test_add ____________________________________
    def test_add():
>       assert add(1, 2) == 4
E       assert 3 == 4
test_calc.py:5: AssertionError
========================= 1 failed, 2 passed in 0.05s ==========================
"""
        report = TestResultParser.parse(output)
        assert not report.is_clean
        assert len(report.failures) == 1
        assert report.failures[0].name == "test_add"
        assert "assert 3 == 4" in report.failures[0].message

    def test_feedback_injector_formats_for_llm(self):
        report = FeedbackReport(
            source="pytest",
            is_clean=False,
            summary="1 test failed",
            failures=[TestFailure(name="test_add", message="assert 3 == 4", file="test_calc.py", line=5)],
        )
        msg = FeedbackInjector.format_for_llm(report)
        assert "test_add" in msg
        assert "test_calc.py" in msg
        assert "fix" in msg.lower() or "ACTION" in msg


class TestDemo3DeepGovernance:
    def test_classify_command_all_levels(self):
        assert classify_command("rm -rf /") == RiskLevel.BLOCK
        assert classify_command("sudo reboot") == RiskLevel.BLOCK
        assert classify_command("git push --force origin main") == RiskLevel.BLOCK
        assert classify_command("pip install numpy") == RiskLevel.HITL_REQUIRED
        assert classify_command("git push origin feature") == RiskLevel.HITL_REQUIRED
        assert classify_command("rm -rf ./temp") == RiskLevel.HITL_REQUIRED
        assert classify_command("ls -la") == RiskLevel.SAFE
        assert classify_command("echo hello") == RiskLevel.SAFE
        assert classify_command("pytest") == RiskLevel.SAFE

    def test_custom_rules_override_defaults(self):
        engine = GuardrailEngine()
        assert engine.evaluate("execute_shell", {"command": "echo hello"}, "/p") == RiskLevel.SAFE
        engine.add_rule("echo hello", RiskLevel.BLOCK, "custom echo block")
        assert engine.evaluate("execute_shell", {"command": "echo hello"}, "/p") == RiskLevel.BLOCK

    def test_file_path_classification(self):
        from codeguard.governance import classify_file_path
        assert classify_file_path("/etc/passwd", "/project") == RiskLevel.BLOCK
        assert classify_file_path("/etc/shadow", "/project") == RiskLevel.BLOCK
        assert classify_file_path("/sys/class/power", "/project") == RiskLevel.BLOCK
        assert classify_file_path("/project/.env", "/project") == RiskLevel.BLOCK
        assert classify_file_path("/project/credentials.json", "/project") == RiskLevel.BLOCK
        assert classify_file_path("/project/src/main.py", "/project") == RiskLevel.SAFE
        assert classify_file_path("/other/path/file.txt", "/project") == RiskLevel.HITL_REQUIRED
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_mechanisms.py -v
```

Expected: FAIL (some tests may fail if modules not yet fully integrated)

- [ ] **Step 3: Run test to verify it passes**

```bash
pytest tests/test_mechanisms.py -v
```

Expected: PASS (all mechanism demonstrations work deterministically)

- [ ] **Step 4: Commit**

```bash
git add tests/test_mechanisms.py
git commit -m "feat: add mechanism demonstrations (guardrail, feedback, governance)"
```

---

### Task 13: Docker + CI

**Files:**
- Create: `Dockerfile`
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Produces: Docker image and CI pipeline

- [ ] **Step 1: Create Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ripgrep && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN pip install -e .

EXPOSE 8080

ENTRYPOINT ["python", "-m", "codeguard.cli", "serve"]
```

- [ ] **Step 2: Create CI workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  unit-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      - name: Run tests
        run: pytest -v

  build-docker:
    runs-on: ubuntu-latest
    needs: unit-test
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker image
        run: docker build -t codeguard .
```

- [ ] **Step 3: Verify Dockerfile builds**

```bash
docker build -t codeguard .
```

Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add Dockerfile .github/workflows/ci.yml
git commit -m "feat: add Dockerfile and CI pipeline"
```

---

### Task 14: README and Documentation

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README.md**

Create `README.md`:

```markdown
# CodeGuard - Coding Agent Harness

A coding agent harness with governance-first architecture. Built as part of the AI4SE final project.

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
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with installation, security, and architecture"
```

---

## Final Step: Run All Tests

- [ ] **Run full test suite**

```bash
pytest -v
```

Expected: All tests pass

- [ ] **Install and verify CLI**

```bash
pip install -e .
codeguard --help
```

Expected: CLI help message displayed