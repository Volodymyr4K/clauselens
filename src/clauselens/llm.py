"""Provider-agnostic LLM client.

Any OpenAI-compatible endpoint works — switched via environment variables
(or a .env file), no code changes:

    CLAUSELENS_BASE_URL  (default https://openrouter.ai/api/v1)
    CLAUSELENS_MODEL     (default nvidia/nemotron-3-ultra-550b-a55b:free)
    CLAUSELENS_API_KEY   (required)
"""

import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class LLMClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.0,
    ):
        self.base_url = base_url or os.getenv(
            "CLAUSELENS_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = model or os.getenv(
            "CLAUSELENS_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")
        self.temperature = temperature
        key = api_key or os.getenv("CLAUSELENS_API_KEY")
        if not key:
            raise RuntimeError(
                "CLAUSELENS_API_KEY is not set (put it in .env or the environment)")
        self._client = OpenAI(base_url=self.base_url, api_key=key)

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
