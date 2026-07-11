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