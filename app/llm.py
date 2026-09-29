"""Thin, defensive wrapper around an OpenAI-compatible endpoint (Groq by default).

The brief warns that models can fail on function calling, so Blackbox does not depend on it.
We ask for JSON in plain text, parse it defensively, retry, then fall back to a second model.
"""
import asyncio
import json
import re
from typing import Optional

from openai import AsyncOpenAI

from .config import settings


class LLMError(RuntimeError):
    pass


_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if not settings.llm_api_key:
            raise LLMError("GROQ_API_KEY is not set. Add it to .env or set LLM_MODE=mock.")
        _client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url, timeout=45.0)
    return _client


def extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model reply, tolerating think tags and code fences."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)
    raise LLMError("Model did not return valid JSON")


async def complete_json(system: str, user: str) -> tuple[dict, str]:
    """Returns (parsed_json, model_used)."""
    last: Exception = LLMError("no attempt made")
    models = [m for m in (settings.llm_model, settings.llm_fallback_model) if m]
    for model in models:
        for attempt in range(2):
            try:
                resp = await _get_client().chat.completions.create(
                    model=model,
                    temperature=0.2,
                    max_tokens=1400,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                )
                return extract_json(resp.choices[0].message.content or ""), model
            except Exception as e:  # rate limits, timeouts, bad JSON: retry, then fall back to the next model
                last = e
                await asyncio.sleep(0.6 * (attempt + 1))
    raise LLMError(f"All models failed: {last}")
