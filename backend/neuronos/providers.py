from __future__ import annotations

import os

import httpx


class OllamaProvider:
    def __init__(self, model: str | None = None, base_url: str = "http://localhost:11434"):
        self.model = model or os.environ.get("NEURONOS_CHAT_MODEL", "gemma3:1b")
        self.base_url = base_url.rstrip("/")
        configured_fallback = os.environ.get("OLLAMA_FALLBACK_MODEL", "gemma4:e2b")
        self.fallback_models = _unique_models(
            [configured_fallback, "gemma3:1b", "gemma3:4b", "gemma4:e2b"]
        )

    async def respond(self, message: str) -> str:
        for candidate in _unique_models([self.model, *self.fallback_models]):
            text = await self._chat(candidate, message)
            if text:
                return text
        return _fallback_response(message)

    async def _chat(self, model: str, message: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "stream": False,
                        "keep_alive": "10m",
                        "options": {
                            "temperature": 0.2,
                            "top_p": 0.9,
                            "num_predict": 80,
                        },
                        "prompt": (
                            "You are NeuronOS, a concise local desktop assistant. "
                            "Answer the user's question naturally in 2-4 short sentences.\n\n"
                            f"User: {message}\nAssistant:"
                        ),
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError):
            return ""

        return payload.get("response", "").strip()


def _unique_models(models: list[str]) -> list[str]:
    ordered: list[str] = []
    for model in models:
        if model and model not in ordered:
            ordered.append(model)
    return ordered


def _fallback_response(message: str) -> str:
    lowered = message.lower().strip()
    if lowered.startswith("remember"):
        return "Saved that to local memory."
    if lowered.startswith(("what ", "how ", "why ", "when ", "where ", "who ")):
        return "I can help with that. Ask me a question or tell me what to do on this PC."
    if lowered.startswith(("open ", "launch ", "run ", "execute ")):
        return "Working on it locally."
    return "Tell me what you want to do, or ask me a general question."
