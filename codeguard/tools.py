import subprocess
from dataclasses import dataclass
from pathlib import Path
from enum import Enum
from typing import Callable


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
            return ToolResult(success=False, output=f"Error: file not found: {path}")
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
        return ToolResult(success=False, output=f"Command timeout after {timeout}s")
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