"""One small call into the configured AI provider that returns parsed JSON.

Switching provider (scope §10: "the approved AI provider") is a .env change only:
LLM_PROVIDER=gemini|openai plus that provider's key and model.
"""
import json

import httpx
from openai import OpenAI

from app.core.config import settings


class LLMUnavailable(RuntimeError):
    """The provider is not configured, refused the call, or returned something unparseable."""


def _parse(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise LLMUnavailable(f"AI returned invalid JSON: {e}") from e


def complete_json(system: str, user: str) -> dict:
    provider = settings.active_provider
    timeout = settings.GEMINI_GENERATION_TIMEOUT_SECONDS

    if provider == "gemini" and settings.is_gemini_configured:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
        }
        try:
            r = httpx.post(url, params={"key": settings.GEMINI_API_KEY}, json=payload, timeout=timeout)
        except httpx.HTTPError as e:
            raise LLMUnavailable(f"Gemini request failed: {e}") from e
        if r.status_code != 200:
            raise LLMUnavailable(f"Gemini returned HTTP {r.status_code}")
        try:
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, ValueError) as e:
            raise LLMUnavailable("Gemini returned no content") from e
        return _parse(text)

    if provider == "openai" and settings.is_openai_configured:
        try:
            resp = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=timeout).chat.completions.create(
                model=settings.OPENAI_CHAT_MODEL,
                response_format={"type": "json_object"},
                temperature=0.2,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            )
        except Exception as e:  # SDK raises several error types
            raise LLMUnavailable(f"OpenAI request failed: {e}") from e
        return _parse(resp.choices[0].message.content or "")

    raise LLMUnavailable("No AI provider is configured (set LLM_PROVIDER and its API key in .env).")
