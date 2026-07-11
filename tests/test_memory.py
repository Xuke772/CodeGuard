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