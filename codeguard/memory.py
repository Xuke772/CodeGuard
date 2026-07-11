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