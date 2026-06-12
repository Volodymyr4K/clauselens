"""Provider-agnostic LLM client.

Any OpenAI-compatible endpoint works: local Ollama (default), OpenRouter,
or anything else — switched via environment variables, no code changes:

    CLAUSELENS_BASE_URL  (default http://localhost:11434/v1  — local Ollama)
    CLAUSELENS_MODEL     (default gemma4:latest)
    CLAUSELENS_API_KEY   (default "ollama"; OpenRouter key when using it)
"""

import json
import os
import re

from openai import OpenAI


class LLMClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.0,
    ):
        self.base_url = base_url or os.getenv(
            "CLAUSELENS_BASE_URL", "http://localhost:11434/v1")
        self.model = model or os.getenv("CLAUSELENS_MODEL", "gemma4:latest")
        self.temperature = temperature
        self._client = OpenAI(
            base_url=self.base_url,
            api_key=api_key or os.getenv("CLAUSELENS_API_KEY", "ollama"),
        )

    def chat(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or ""

    def chat_json(self, system: str, user: str, retries: int = 2) -> dict:
        """Chat expecting a JSON object back; retries on unparseable output."""
        last_err: Exception | None = None
        for _ in range(retries + 1):
            text = self.chat(system, user)
            try:
                return _parse_json_object(text)
            except ValueError as e:
                last_err = e
        raise ValueError(f"model returned unparseable JSON after retries: {last_err}")


def _parse_json_object(text: str) -> dict:
    """Extract a JSON object from model output, tolerating markdown fences."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text
    start, end = candidate.find("{"), candidate.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found in output")
    obj = json.loads(candidate[start:end + 1])
    if not isinstance(obj, dict):
        raise ValueError("top-level JSON is not an object")
    return obj
