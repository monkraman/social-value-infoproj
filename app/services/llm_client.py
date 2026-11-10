"""One small call into the configured AI provider that returns parsed JSON.

Switching provider (scope §10: "the approved AI provider") is a .env change only:
LLM_PROVIDER=gemini|openai plus that provider's key and model.
"""
import json
import time

import httpx
from openai import OpenAI

from app.core.config import settings


class LLMUnavailable(RuntimeError):
    """The provider is not configured, refused the call, or returned something unparseable."""


# Status codes where another Gemini model may still work (quota, overload, model retired).
_GEMINI_RETRYABLE = {404, 429, 500, 503}
# A model that just failed is skipped for this long so every request doesn't wait on it again.
_GEMINI_COOLDOWN_SECONDS = 600
_gemini_cooldown_until: dict[str, float] = {}


def _gemini_models() -> list[str]:
    models = [settings.GEMINI_MODEL]
    for m in settings.GEMINI_FALLBACK_MODELS.split(","):
        m = m.strip()
        if m and m not in models:
            models.append(m)
    return models


def gemini_generate(
    prompt: str,
    *,
    system: str | None = None,
    generation_config: dict | None = None,
    timeout: float | None = None,
) -> str:
    """Call Gemini generateContent, moving down the model list on quota/overload/timeout.

    Returns the response text; raises LLMUnavailable if no model answered.
    """
    payload: dict = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    if generation_config:
        payload["generationConfig"] = generation_config
    timeout = timeout or settings.GEMINI_GENERATION_TIMEOUT_SECONDS

    errors: list[str] = []
    now = time.monotonic()
    models = _gemini_models()
    ready = [m for m in models if _gemini_cooldown_until.get(m, 0) <= now]
    # If every model is cooling down, try them all anyway rather than failing outright.
    for model in ready or models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            r = httpx.post(url, params={"key": settings.GEMINI_API_KEY}, json=payload, timeout=timeout)
        except httpx.HTTPError as e:
            errors.append(f"{model}: {type(e).__name__}")
            print(f"[LLM] Gemini {model} failed: {type(e).__name__}; trying next model")
            _gemini_cooldown_until[model] = time.monotonic() + _GEMINI_COOLDOWN_SECONDS
            continue

        if r.status_code == 200:
            try:
                parts = r.json()["candidates"][0]["content"]["parts"]
            except (KeyError, IndexError, ValueError):
                errors.append(f"{model}: no content")
                continue
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            if text.strip():
                _gemini_cooldown_until.pop(model, None)
                print(f"[LLM] Gemini answered with {model}")
                return text
            reason = r.json()["candidates"][0].get("finishReason")
            errors.append(f"{model}: empty response ({reason})")
            print(f"[LLM] Gemini {model} returned no text (finishReason={reason}); trying next model")
            continue

        errors.append(f"{model}: HTTP {r.status_code}")
        print(f"[LLM] Gemini {model} HTTP {r.status_code}: {r.text[:160]!r}")
        if r.status_code not in _GEMINI_RETRYABLE:
            break  # bad request / bad key: another model won't help
        _gemini_cooldown_until[model] = time.monotonic() + _GEMINI_COOLDOWN_SECONDS

    msg = "Gemini unavailable (" + "; ".join(errors) + ")"
    print(f"[LLM] {msg}")
    raise LLMUnavailable(msg)


def strip_code_fence(text: str) -> str:
    text = text.strip()
    if "```json" in text:
        return text.split("```json", 1)[1].split("```", 1)[0].strip()
    if text.startswith("```"):
        return text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return text


def _parse(text: str) -> dict:
    try:
        return json.loads(strip_code_fence(text))
    except json.JSONDecodeError as e:
        raise LLMUnavailable(f"AI returned invalid JSON: {e}") from e


def complete_json(system: str, user: str) -> dict:
    provider = settings.active_provider
    timeout = settings.GEMINI_GENERATION_TIMEOUT_SECONDS

    if provider == "gemini" and settings.is_gemini_configured:
        text = gemini_generate(
            user,
            system=system,
            generation_config={"temperature": 0.2, "responseMimeType": "application/json"},
            timeout=timeout,
        )
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
