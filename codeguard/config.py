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


DEFAULT_CONFIG = Config()