"""Provider-agnostic LLM client.

Any OpenAI-compatible endpoint works — switched via environment variables
(or a .env file), no code changes:

    CLAUSELENS_BASE_URL     (default https://openrouter.ai/api/v1)
    CLAUSELENS_MODEL        (default google/gemma-4-31b-it:free)
    CLAUSELENS_API_KEY      (required)
    CLAUSELENS_MIN_INTERVAL (seconds between requests, default 0)
"""

import json
import os
import re
import threading
import time

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

load_dotenv()


class TransientLLMError(Exception):
    """Endpoint hiccup that is worth retrying (throttling, empty response)."""


class _RateLimiter:
    """Process-wide minimum spacing between requests.

    Free tiers cap requests per minute (OpenRouter free: 20/min). Firing chunk
    requests back to back trips that cap on long runs: the endpoint starts
    returning 429s and empty bodies, retries exhaust, and whole chunks are
    lost — silently depressing recall with a network artifact, not a model
    result. Spacing requests just under the cap avoids tripping it at all. The
    limit is per account, so the spacing is global, guarded by a lock.
    """

    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        if self.min_interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            sleep_for = self._next_allowed - now
            if sleep_for > 0:
                time.sleep(sleep_for)
            self._next_allowed = time.monotonic() + self.min_interval


_rate_limiter = _RateLimiter(float(os.getenv("CLAUSELENS_MIN_INTERVAL", "0")))


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
            "CLAUSELENS_MODEL", "google/gemma-4-31b-it:free")
        self.temperature = temperature
        key = api_key or os.getenv("CLAUSELENS_API_KEY")
        if not key:
            raise RuntimeError(
                "CLAUSELENS_API_KEY is not set (put it in .env or the environment)")
        self._client = OpenAI(base_url=self.base_url, api_key=key)

    def chat(self, system: str, user: str, retries: int = 4) -> str:
        """Single chat turn with exponential backoff.

        Free-tier endpoints fail in two ways that must both be retried:
        transport errors (429/5xx) and, nastier, HTTP 200 with an empty
        `choices` field when the upstream provider chokes.
        """
        delay = 2.0
        last_err: Exception | None = None
        for attempt in range(retries + 1):
            try:
                _rate_limiter.wait()
                resp = self._client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                if not resp.choices:
                    raise TransientLLMError(
                        f"empty choices in response: {getattr(resp, 'error', None)}")
                return resp.choices[0].message.content or ""
            except (TransientLLMError, OpenAIError) as e:
                last_err = e
                if attempt == retries:
                    break
                time.sleep(delay)
                delay *= 2
        raise TransientLLMError(f"chat failed after {retries + 1} attempts: {last_err}")

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
