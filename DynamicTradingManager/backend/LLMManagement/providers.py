"""
LLMManagement.providers
~~~~~~~~~~~~~~~~~~~~~~~
Registry of well-known LLM providers and their default configurations.
Users can always add custom providers from the frontend; these are just
convenient presets.
"""

from __future__ import annotations

KNOWN_PROVIDERS: dict[str, dict] = {
    "puter": {
        "id": "puter",
        "label": "Puter AI (Browser)",
        "description": "Free browser-based AI. Runs client-side, no API key needed.",
        "base_url": "",
        "api_key": "",
        "model": "",
        "supports_thinking": False,
        "is_local": False,
        "is_browser_only": True,
    },
    "lmstudio": {
        "id": "lmstudio",
        "label": "LM Studio (Local)",
        "description": "Run models locally via LM Studio's OpenAI-compatible server.",
        "base_url": "http://localhost:1234/v1",
        "api_key": "lm-studio",
        "model": "",
        "supports_thinking": False,
        "is_local": True,
        "is_browser_only": False,
    },
    "nvidia": {
        "id": "nvidia",
        "label": "NVIDIA NIM",
        "description": "Cloud inference via NVIDIA's Integrate API.",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key": "",
        "model": "minimaxai/minimax-m2.7",
        "supports_thinking": False,
        "is_local": False,
        "is_browser_only": False,
    },
    "groq": {
        "id": "groq",
        "label": "Groq Cloud",
        "description": "Ultra-fast inference via Groq LPUs.",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": "",
        "model": "llama-3.3-70b-versatile",
        "supports_thinking": False,
        "is_local": False,
        "is_browser_only": False,
    },
}


def get_known_providers() -> list[dict]:
    """Return the list of known provider presets."""
    return list(KNOWN_PROVIDERS.values())


def get_provider_defaults(provider_id: str) -> dict | None:
    """Return defaults for a known provider, or None if unknown."""
    return KNOWN_PROVIDERS.get(provider_id)
