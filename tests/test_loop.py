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
        assert mock_llm.call_history[1][-2].content.startswith("BLOCKED")

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
                super().__init__(responses=['ACTION: FINISH\nPARAMS: {"summary": "done"}'])
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
            'ACTION: write_file\nPARAMS: {"path": "C:/some_outside_dir/file.txt", "content": "data"}',
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