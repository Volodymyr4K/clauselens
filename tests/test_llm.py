from types import SimpleNamespace
from unittest.mock import patch

import pytest
from openai import APIConnectionError

from clauselens.llm import LLMClient, TransientLLMError


def make_client() -> LLMClient:
    return LLMClient(api_key="test-key", base_url="http://test")


def response_with(content):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def empty_response():
    return SimpleNamespace(choices=None, error={"code": 502})


class TestChatRetries:
    @patch("clauselens.llm.time.sleep")
    def test_empty_choices_retried_then_succeeds(self, _sleep):
        client = make_client()
        calls = iter([empty_response(), response_with("hello")])
        client._client = SimpleNamespace(chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kw: next(calls))))
        assert client.chat("s", "u") == "hello"

    @patch("clauselens.llm.time.sleep")
    def test_transport_error_retried_then_succeeds(self, _sleep):
        client = make_client()
        attempts = {"n": 0}

        def create(**kw):
            attempts["n"] += 1
            if attempts["n"] == 1:
                raise APIConnectionError(request=None)
            return response_with("ok")

        client._client = SimpleNamespace(chat=SimpleNamespace(
            completions=SimpleNamespace(create=create)))
        assert client.chat("s", "u") == "ok"
        assert attempts["n"] == 2

    @patch("clauselens.llm.time.sleep")
    def test_persistent_failure_raises_after_retries(self, _sleep):
        client = make_client()
        attempts = {"n": 0}

        def create(**kw):
            attempts["n"] += 1
            return empty_response()

        client._client = SimpleNamespace(chat=SimpleNamespace(
            completions=SimpleNamespace(create=create)))
        with pytest.raises(TransientLLMError):
            client.chat("s", "u", retries=2)
        assert attempts["n"] == 3  # initial + 2 retries


class TestChatJson:
    @patch("clauselens.llm.time.sleep")
    def test_markdown_fenced_json_parsed(self, _sleep):
        client = make_client()
        client._client = SimpleNamespace(chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kw: response_with('```json\n{"a": [1]}\n```'))))
        assert client.chat_json("s", "u") == {"a": [1]}

    @patch("clauselens.llm.time.sleep")
    def test_garbage_raises_value_error(self, _sleep):
        client = make_client()
        client._client = SimpleNamespace(chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kw: response_with("no json here"))))
        with pytest.raises(ValueError):
            client.chat_json("s", "u", retries=1)
