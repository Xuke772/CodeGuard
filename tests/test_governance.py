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