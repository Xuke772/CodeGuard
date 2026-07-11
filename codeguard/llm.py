from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from codeguard.memory import Message


@dataclass
class LLMResponse:
    content: str
    finish_reason: str = "stop"


class LLMAdapter(ABC):
    @abstractmethod
    def chat(self, messages: list[Message]) -> LLMResponse:
        ...


class MockLLM(LLMAdapter):
    def __init__(self, responses: list[str] | None = None):
        self.responses = responses or []
        self._index = 0
        self.call_history: list[list[Message]] = []

    def chat(self, messages: list[Message]) -> LLMResponse:
        self.call_history.append(messages)
        if not self.responses:
            return LLMResponse(content="FINISH", finish_reason="stop")
        response = self.responses[self._index]
        if self._index < len(self.responses) - 1:
            self._index += 1
        return LLMResponse(content=response, finish_reason="stop")


class DeepSeekAdapter(LLMAdapter):
    def __init__(self, api_key: str, config):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=api_key,
            base_url=config.llm.api_base,
        )
        self.model = config.llm.model
        self.temperature = config.llm.temperature
        self.max_tokens = config.llm.max_tokens

    def chat(self, messages: list[Message]) -> LLMResponse:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            finish_reason=choice.finish_reason or "stop",
        )