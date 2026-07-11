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