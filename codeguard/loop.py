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