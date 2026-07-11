import pytest
from unittest.mock import patch, MagicMock
from codeguard.llm import LLMResponse, MockLLM, DeepSeekAdapter, Message
from codeguard.config import Config


class TestLLMResponse:
    def test_response_creation(self):
        resp = LLMResponse(content="Hello", finish_reason="stop")
        assert resp.content == "Hello"
        assert resp.finish_reason == "stop"

    def test_response_defaults(self):
        resp = LLMResponse(content="test")
        assert resp.content == "test"
        assert resp.finish_reason == "stop"


class TestMockLLM:
    def test_mock_returns_configured_response(self):
        mock = MockLLM(responses=["action: write_file"])
        resp = mock.chat([Message(role="user", content="create a file")])
        assert resp.content == "action: write_file"
        assert resp.finish_reason == "stop"

    def test_mock_cycles_through_responses(self):
        mock = MockLLM(responses=["first", "second", "third"])
        assert mock.chat([Message(role="user", content="hi")]).content == "first"
        assert mock.chat([Message(role="user", content="hi")]).content == "second"
        assert mock.chat([Message(role="user", content="hi")]).content == "third"

    def test_mock_repeats_last_response(self):
        mock = MockLLM(responses=["only"])
        assert mock.chat([Message(role="user", content="q1")]).content == "only"
        assert mock.chat([Message(role="user", content="q2")]).content == "only"

    def test_mock_call_history(self):
        mock = MockLLM(responses=["a", "b"])
        mock.chat([Message(role="user", content="q1")])
        mock.chat([Message(role="user", content="q2")])
        assert len(mock.call_history) == 2
        assert mock.call_history[0][0].content == "q1"
        assert mock.call_history[1][0].content == "q2"

    def test_mock_empty_responses(self):
        mock = MockLLM()
        resp = mock.chat([Message(role="user", content="test")])
        assert resp.content == "FINISH"
        assert resp.finish_reason == "stop"


class TestMessage:
    def test_message_to_dict(self):
        msg = Message(role="user", content="hello")
        d = msg.to_dict()
        assert d == {"role": "user", "content": "hello"}

    def test_message_creation(self):
        msg = Message(role="assistant", content="response")
        assert msg.role == "assistant"
        assert msg.content == "response"