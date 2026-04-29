"""
LLMManagement.client
~~~~~~~~~~~~~~~~~~~~
Stateless OpenAI-compatible chat completion client.
All config (base_url, api_key, model) is passed per-request from the frontend.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


@dataclass
class ChatResult:
    content: str
    thinking: str | None
    model: str
    usage: dict[str, Any]


def _build_client(base_url: str, api_key: str) -> AsyncOpenAI:
    """Create a disposable AsyncOpenAI client for a single request."""
    return AsyncOpenAI(
        base_url=base_url.rstrip("/"),
        api_key=api_key or "no-key",
        timeout=60.0,
    )


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
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    # Thinking mode: try provider-specific reasoning parameters
    if thinking:
        kwargs.setdefault("extra_body", {})
        kwargs["extra_body"]["reasoning_effort"] = "high"

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

            stream_response = await client.chat.completions.create(**kwargs)
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
            response = await client.chat.completions.create(**kwargs)
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
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    if thinking and ("o1-" in model or "o3-" in model):
        kwargs.setdefault("extra_body", {})
        kwargs["extra_body"]["reasoning_effort"] = "high"

    logger.info("Starting LLM stream: model=%s base_url=%s thinking=%s", model, base_url, thinking)

    try:
        stream_response = await client.chat.completions.create(**kwargs)
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
                
    except Exception as exc:
        logger.error("Error in LLM stream: %s", exc, exc_info=True)
        yield json.dumps({"error": str(exc) or "Unknown stream error"}) + "\n"
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

