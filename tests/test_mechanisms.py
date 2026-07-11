import pytest
import time
from pathlib import Path
from codeguard.llm import MockLLM
from codeguard.tools import create_default_registry, RiskLevel
from codeguard.governance import GuardrailEngine, HITLStateMachine, HITLStatus, classify_command, classify_file_path
from codeguard.feedback import TestResultParser, FeedbackInjector, FeedbackReport, TestFailure
from codeguard.loop import Agent, ActionParser, AgentStatus
from codeguard.config import Config


def _create_mechanism_demo_registry(workspace):
    from codeguard.tools import ToolRegistry, ToolDef, ToolResult, execute_read_file, execute_write_file

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
        ToolDef("search_code", "Search code with ripgrep", {"pattern": "str", "path": "str"}, RiskLevel.SAFE),
        lambda pattern, path=".": ToolResult(success=True, output="No matches found."),
    )

    run_tests_call_count = [0]
    def mock_run_tests(command=None):
        run_tests_call_count[0] += 1
        if run_tests_call_count[0] == 1:
            failure_output = (
                "============================= test session starts ==============================\n"
                "test_calc.py .F.                                                          [100%]\n"
                "=================================== FAILURES ===================================\n"
                "________________________________ test_add ____________________________________\n"
                "    def test_add():\n"
                ">       assert add(1, 2) == 4\n"
                "E       assert 3 == 4\n"
                "test_calc.py:5: AssertionError\n"
                "========================= 1 failed, 2 passed in 0.05s ==========================\n"
            )
            return ToolResult(success=False, output=failure_output)
        return ToolResult(success=True, output="3 passed in 0.05s")

    registry.register(
        ToolDef("run_tests", "Run the test suite", {"command": "str|None"}, RiskLevel.SAFE),
        mock_run_tests,
    )
    registry.register(
        ToolDef("execute_shell", "Execute a shell command", {"command": "str", "cwd": "str|None"}, RiskLevel.HITL_REQUIRED),
        lambda command, cwd=None: ToolResult(success=True, output="executed: " + command),
    )
    return registry


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
            tool_registry=_create_mechanism_demo_registry(temp_workspace),
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
        assert classify_file_path("/etc/passwd", "/project") == RiskLevel.BLOCK
        assert classify_file_path("/etc/shadow", "/project") == RiskLevel.BLOCK
        assert classify_file_path("/sys/class/power", "/project") == RiskLevel.BLOCK
        assert classify_file_path("/project/.env", "/project") == RiskLevel.BLOCK
        assert classify_file_path("/project/credentials.json", "/project") == RiskLevel.BLOCK
        assert classify_file_path("/project/src/main.py", "/project") == RiskLevel.SAFE
        assert classify_file_path("/other/path/file.txt", "/project") == RiskLevel.HITL_REQUIRED