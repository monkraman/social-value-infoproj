"""One small call into the configured AI provider that returns parsed JSON.

Switching provider (scope §10: "the approved AI provider") is a configuration change only:
LLM_PROVIDER=azure|gemini|openai picks the first provider, LLM_FALLBACK lists the ones tried
next when it is out of quota or down. Keys live only in the backend's environment.
"""
import json
import time

import httpx
from openai import AzureOpenAI, OpenAI

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
    deadline = now + settings.GEMINI_TOTAL_TIMEOUT_SECONDS
    models = _gemini_models()
    ready = [m for m in models if _gemini_cooldown_until.get(m, 0) <= now]
    # If every model is cooling down, try them all anyway rather than failing outright.
    for model in ready or models:
        # Falling back is only worth it while someone is still waiting for the answer.
        remaining = deadline - time.monotonic()
        if remaining < 10:
            errors.append(f"{model}: skipped, {settings.GEMINI_TOTAL_TIMEOUT_SECONDS:.0f}s budget spent")
            break
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            r = httpx.post(url, params={"key": settings.GEMINI_API_KEY}, json=payload, timeout=min(timeout, remaining))
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


def _openai_style(client, model: str, system: str, user: str, temperature) -> str:
    kwargs = {}
    if temperature is not None:
        kwargs["temperature"] = temperature  # reasoning models (gpt-5, o-series) accept only the default
    resp = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        **kwargs,
    )
    return resp.choices[0].message.content or ""


def _call(provider: str, system: str, user: str) -> tuple[dict, str]:
    """One attempt with one provider. Returns (parsed JSON, "provider/model")."""
    if provider == "azure":
        client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            timeout=settings.AZURE_OPENAI_TIMEOUT_SECONDS,
            max_retries=1,
        )
        try:
            text = _openai_style(client, settings.AZURE_OPENAI_DEPLOYMENT, system, user, settings.AZURE_OPENAI_TEMPERATURE)
        except Exception as e:  # SDK raises several error types; the message names the cause (e.g. 429)
            raise LLMUnavailable(f"Azure OpenAI request failed: {e}") from e
        return _parse(text), f"azure/{settings.AZURE_OPENAI_DEPLOYMENT}"

    if provider == "gemini":
        text = gemini_generate(
            user,
            system=system,
            generation_config={"temperature": 0.2, "responseMimeType": "application/json"},
            timeout=settings.GEMINI_GENERATION_TIMEOUT_SECONDS,
        )
        return _parse(text), f"gemini/{settings.GEMINI_MODEL}"

    if provider == "openai":
        client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=settings.GEMINI_GENERATION_TIMEOUT_SECONDS)
        try:
            text = _openai_style(client, settings.OPENAI_CHAT_MODEL, system, user, 0.2)
        except Exception as e:
            raise LLMUnavailable(f"OpenAI request failed: {e}") from e
        return _parse(text), f"openai/{settings.OPENAI_CHAT_MODEL}"

    raise LLMUnavailable(f"Unknown AI provider '{provider}'.")


def complete_json_with_source(system: str, user: str) -> tuple[dict, str]:
    """Try each configured provider in order (LLM_PROVIDER, then LLM_FALLBACK).

    Returns the parsed JSON and which provider/model produced it, so a result can say where it
    came from. Raises LLMUnavailable with every provider's reason when all of them fail.
    """
    from app.services.ai_settings_service import effective_order  # avoids an import cycle with the models

    order = effective_order()
    if not order:
        raise LLMUnavailable("No AI provider is configured (set LLM_PROVIDER and its API key in .env).")
    errors = []
    for provider in order:
        try:
            return _call(provider, system, user)
        except LLMUnavailable as e:
            errors.append(str(e))
    raise LLMUnavailable(" | ".join(errors))


def complete_json(system: str, user: str) -> dict:
    return complete_json_with_source(system, user)[0]
