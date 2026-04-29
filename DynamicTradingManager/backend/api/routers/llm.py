"""
API router for LLM management.

All provider config (base_url, api_key, model) is sent from the frontend
per-request. The backend is a stateless proxy.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from LLMManagement.client import chat_completion, stream_completion, list_models, ChatResult
from LLMManagement.providers import get_known_providers

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/llm", tags=["LLM"])


# ── Request / Response Schemas ──────────────────────────────────────────


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    base_url: str
    api_key: str = ""
    model: str
    messages: list[ChatMessage]
    thinking: bool = False
    temperature: float | None = None
    max_tokens: int | None = None


class ChatResponse(BaseModel):
    content: str
    thinking: str | None = None
    model: str
    usage: dict[str, Any] = Field(default_factory=dict)


class ModelsRequest(BaseModel):
    base_url: str
    api_key: str = ""


class ModelEntry(BaseModel):
    id: str
    name: str


# ── Endpoints ───────────────────────────────────────────────────────────


@router.get("/providers")
async def get_providers():
    """Return the list of known provider presets."""
    return get_known_providers()


@router.post("/chat", response_model=ChatResponse)
async def proxy_chat(req: ChatRequest):
    """
    Proxy a chat completion to the specified OpenAI-compatible provider.
    All credentials are sent per-request from the frontend.
    """
    if not req.base_url:
        raise HTTPException(400, "base_url is required for non-browser providers.")
    if not req.model:
        raise HTTPException(400, "model is required.")

    try:
        result: ChatResult = await chat_completion(
            base_url=req.base_url,
            api_key=req.api_key,
            model=req.model,
            messages=[m.model_dump() for m in req.messages],
            thinking=req.thinking,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
        return ChatResponse(
            content=result.content,
            thinking=result.thinking,
            model=result.model,
            usage=result.usage,
        )
    except Exception as exc:
        logger.exception("LLM chat failed")
        raise HTTPException(502, f"LLM provider error: {exc}")


@router.post("/chat/stream")
async def proxy_chat_stream(req: ChatRequest):
    """
    Proxy a streaming chat completion. Returns a StreamingResponse of JSON lines.
    """
    if not req.base_url:
        raise HTTPException(400, "base_url is required for non-browser providers.")
    
    # We use a generator to yield chunks to StreamingResponse
    return StreamingResponse(
        stream_completion(
            base_url=req.base_url,
            api_key=req.api_key,
            model=req.model,
            messages=[m.model_dump() for m in req.messages],
            thinking=req.thinking,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        ),
        media_type="application/x-ndjson",
    )


@router.post("/models", response_model=list[ModelEntry])
async def proxy_list_models(req: ModelsRequest):
    """Fetch available models from a provider's /v1/models endpoint."""
    if not req.base_url:
        raise HTTPException(400, "base_url is required.")

    models = await list_models(base_url=req.base_url, api_key=req.api_key)
    return [ModelEntry(id=m["id"], name=m["name"]) for m in models]
