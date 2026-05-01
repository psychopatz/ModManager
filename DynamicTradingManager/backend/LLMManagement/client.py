"""
LLMManagement.client
~~~~~~~~~~~~~~~~~~~~
Stateless OpenAI-compatible chat completion client.
All config (base_url, api_key, model) is passed per-request from the frontend.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator

from openai import AsyncOpenAI, RateLimitError

logger = logging.getLogger(__name__)


# Provider pacing state (process-local): helps prevent bursty 429s under batch runs.
_PROVIDER_PACING_LOCKS: dict[str, asyncio.Lock] = {}
_PROVIDER_NEXT_ALLOWED_TS: dict[str, float] = {}


def _provider_key(base_url: str) -> str:
    return str(base_url or "").strip().lower().rstrip("/")


def _provider_min_interval_seconds(base_url: str) -> float:
    normalized = _provider_key(base_url)

    # Local providers generally don't need pacing.
    if "localhost" in normalized or "127.0.0.1" in normalized:
        return 0.0

    # Cloud provider-specific defaults.
    if "integrate.api.nvidia.com" in normalized:
        return 1.25
    if "api.groq.com" in normalized:
        return 0.6

    # Conservative default for unknown cloud endpoints.
    return 0.4


async def _wait_for_provider_slot(*, base_url: str) -> None:
    interval = _provider_min_interval_seconds(base_url)
    if interval <= 0:
        return

    key = _provider_key(base_url)
    lock = _PROVIDER_PACING_LOCKS.setdefault(key, asyncio.Lock())

    async with lock:
        now = time.monotonic()
        earliest = _PROVIDER_NEXT_ALLOWED_TS.get(key, 0.0)
        delay = earliest - now
        if delay > 0:
            await asyncio.sleep(delay)
            now = time.monotonic()

        _PROVIDER_NEXT_ALLOWED_TS[key] = now + interval


@dataclass
class ChatResult:
    content: str
    thinking: str | None
    model: str
    usage: dict[str, Any]


import httpx

def _build_client(base_url: str, api_key: str) -> AsyncOpenAI:
    """Create a disposable AsyncOpenAI client for a single request."""
    return AsyncOpenAI(
        base_url=base_url.rstrip("/"),
        api_key=api_key or "no-key",
        timeout=httpx.Timeout(600.0, connect=60.0),
        # We manage rate-limit retries ourselves to avoid short retry storms.
        max_retries=0,
    )


def _extract_retry_after_seconds(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    if response is None:
        return None
    headers = getattr(response, "headers", None) or {}
    value = headers.get("retry-after") or headers.get("Retry-After")
    if not value:
        return None
    try:
        parsed = float(str(value).strip())
    except Exception:
        return None
    return parsed if parsed > 0 else None


async def _create_with_rate_limit_backoff(
    client: AsyncOpenAI,
    kwargs: dict[str, Any],
    *,
    model: str,
    base_url: str,
    max_attempts: int = 6,
    base_delay_seconds: float = 1.5,
    max_delay_seconds: float = 30.0,
):
    """Create a completion with explicit 429 backoff and jitter."""
    attempt = 1
    while True:
        try:
            await _wait_for_provider_slot(base_url=base_url)
            return await client.chat.completions.create(**kwargs)
        except RateLimitError as exc:
            if attempt >= max_attempts:
                raise

            retry_after = _extract_retry_after_seconds(exc)
            backoff = min(max_delay_seconds, base_delay_seconds * (2 ** (attempt - 1)))
            wait_seconds = retry_after if retry_after is not None else (backoff + random.uniform(0.0, 0.6))

            logger.warning(
                "LLM rate-limited (model=%s base_url=%s attempt=%d/%d). Backing off %.2fs.",
                model,
                base_url,
                attempt,
                max_attempts,
                wait_seconds,
            )
            await asyncio.sleep(wait_seconds)
            attempt += 1


def _is_reasoning_effort_supported(model: str, base_url: str) -> bool:
    """Determine if a model or provider supports the reasoning_effort parameter."""
    m_lower = model.lower()
    # OpenAI native reasoning models
    if "o1" in m_lower or "o3" in m_lower:
        return True
    # Groq's reasoning-capable models (Qwen 3, DeepSeek R1)
    if "api.groq.com" in base_url.lower():
        if "qwen" in m_lower or "deepseek" in m_lower or "r1" in m_lower:
            return True
    # General deepseek reasoner
    if "deepseek-reasoner" in m_lower:
        return True
    if "reasoner" in m_lower:
        return True
    return False


def _map_reasoning_effort(model: str, base_url: str, effort: str | None) -> str:
    """Map standard effort levels (low, medium, high) to provider-specific values."""
    if not effort:
        effort = "medium"
    
    effort = effort.lower()
    
    # Groq specific mapping: only supports 'none' or 'default'
    if "api.groq.com" in base_url.lower():
        if effort in ["low", "medium", "high"]:
            return "default"
        return effort if effort in ["none", "default"] else "default"
        
    # OpenAI and others usually support low/medium/high
    return effort


async def chat_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    thinking: bool = False,
    temperature: float | None = None,
    max_tokens: int | None = None,
    stream: bool = True,
    reasoning_effort: str | None = None,
) -> ChatResult:
    """
    Send a chat completion request to any OpenAI-compatible endpoint.
    All logic is now asynchronous to prevent blocking the event loop.
    """
    client = _build_client(base_url, api_key)

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": stream,
    }

    if temperature is not None:
        kwargs["temperature"] = temperature

    # Support modern token limit field for reasoning models
    if max_tokens is not None:
        if _is_reasoning_effort_supported(model, base_url) or "qwen" in model.lower():
            kwargs["max_completion_tokens"] = max_tokens
        else:
            kwargs["max_tokens"] = max_tokens

    # Thinking mode / Reasoning parameters
    if thinking and _is_reasoning_effort_supported(model, base_url):
        kwargs["reasoning_effort"] = _map_reasoning_effort(model, base_url, reasoning_effort)

    logger.info(
        "LLM async chat request: model=%s base_url=%s thinking=%s stream=%s",
        model,
        base_url,
        thinking,
        stream,
    )

    try:
        if stream:
            content_parts = []
            thinking_parts = []
            response_model = model

            stream_response = await _create_with_rate_limit_backoff(
                client,
                kwargs,
                model=model,
                base_url=base_url,
            )
            async for chunk in stream_response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    content_parts.append(delta.content)
                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    thinking_parts.append(delta.reasoning_content)
                if chunk.model:
                    response_model = chunk.model

            return ChatResult(
                content="".join(content_parts),
                thinking="".join(thinking_parts) if thinking_parts else None,
                model=response_model,
                usage={},
            )
        else:
            response = await _create_with_rate_limit_backoff(
                client,
                kwargs,
                model=model,
                base_url=base_url,
            )
            choice = response.choices[0] if response.choices else None
            content = ""
            thinking_content = None

            if choice and choice.message:
                content = choice.message.content or ""
                if hasattr(choice.message, "reasoning_content"):
                    thinking_content = choice.message.reasoning_content
                elif hasattr(choice.message, "thinking"):
                    thinking_content = choice.message.thinking

            usage_data = {}
            if response.usage:
                usage_data = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return ChatResult(
                content=content,
                thinking=thinking_content,
                model=response.model or model,
                usage=usage_data,
            )
    finally:
        await client.close()


async def stream_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    thinking: bool = False,
    temperature: float | None = None,
    max_tokens: int | None = None,
    reasoning_effort: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    Asynchronous generator that yields JSON chunks for a streaming chat completion.
    """
    import json
    client = _build_client(base_url, api_key)

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
    }

    if temperature is not None:
        kwargs["temperature"] = temperature
    # Support modern token limit field for reasoning models
    if max_tokens is not None:
        if _is_reasoning_effort_supported(model, base_url) or "qwen" in model.lower():
            kwargs["max_completion_tokens"] = max_tokens
        else:
            kwargs["max_tokens"] = max_tokens

    if thinking and _is_reasoning_effort_supported(model, base_url):
        kwargs["reasoning_effort"] = _map_reasoning_effort(model, base_url, reasoning_effort)

    logger.info("Starting LLM stream: model=%s base_url=%s thinking=%s", model, base_url, thinking)

    try:
        stream_response = await _create_with_rate_limit_backoff(
            client,
            kwargs,
            model=model,
            base_url=base_url,
        )
        async for chunk in stream_response:
            try:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                
                payload = {}
                if delta and hasattr(delta, "content") and delta.content:
                    payload["content"] = delta.content
                
                # Look for reasoning content in multiple possible fields
                reasoning = None
                if delta:
                    if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                        reasoning = delta.reasoning_content
                    elif hasattr(delta, "thinking") and delta.thinking:
                        reasoning = delta.thinking
                    # Some providers might put it in content if thinking toggle is off but model thinks anyway
                
                if reasoning:
                    payload["thinking"] = reasoning
                
                if chunk.model:
                    payload["model"] = chunk.model
                    
                if payload:
                    yield json.dumps(payload) + "\n"
            except Exception as inner_exc:
                logger.error("Error processing stream chunk: %s", inner_exc, exc_info=True)
                continue
                
    except RateLimitError as exc:
        retry_after = _extract_retry_after_seconds(exc)
        logger.warning(
            "LLM stream rate-limited after retries: model=%s base_url=%s retry_after=%s",
            model,
            base_url,
            retry_after,
        )
        payload = {
            "error": str(exc) or "LLM provider rate limited",
            "error_type": "rate_limit",
        }
        if retry_after is not None:
            payload["retry_after"] = retry_after
        yield json.dumps(payload) + "\n"
    except Exception as exc:
        logger.error("Error in LLM stream: %s", exc, exc_info=True)
        yield json.dumps({"error": str(exc) or "Unknown stream error", "error_type": "provider_error"}) + "\n"
    finally:
        await client.close()


async def list_models(*, base_url: str, api_key: str) -> list[dict[str, str]]:
    """Fetch available models asynchronously."""
    client = _build_client(base_url, api_key)
    try:
        response = await client.models.list()
        return [
            {"id": m.id, "name": getattr(m, "name", m.id)}
            for m in response.data
        ]
    except Exception as exc:
        logger.warning("Failed to list models from %s: %s", base_url, exc)
        return []
    finally:
        await client.close()

