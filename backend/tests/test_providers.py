from neuronos.providers import OllamaProvider


def test_ollama_provider_defaults_to_gemma3_1b(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("NEURONOS_CHAT_MODEL", raising=False)

    assert OllamaProvider().model == "gemma3:1b"


def test_ollama_provider_can_be_overridden_by_env(monkeypatch):
    monkeypatch.setenv("NEURONOS_CHAT_MODEL", "gemma4:e2b")

    assert OllamaProvider().model == "gemma4:e2b"


async def test_ollama_provider_falls_back_to_smaller_model(monkeypatch):
    provider = OllamaProvider(model="gemma4:e4b")
    provider.fallback_models = ["gemma3:1b"]

    async def fake_chat(model: str, message: str) -> str:
        if model == "gemma4:e4b":
            return ""
        if model == "gemma3:1b":
            return "LangGraph is a framework for stateful LLM workflows."
        return ""

    monkeypatch.setattr(provider, "_chat", fake_chat)

    response = await provider.respond("What is LangGraph?")

    assert response == "LangGraph is a framework for stateful LLM workflows."


async def test_ollama_provider_uses_fast_generation_settings(monkeypatch):
    provider = OllamaProvider(model="gemma3:1b")
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": "Short answer."}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr("neuronos.providers.httpx.AsyncClient", FakeClient)

    response = await provider.respond("What is LangGraph?")

    assert response == "Short answer."
    assert captured["timeout"] == 12
    assert captured["url"] == "http://localhost:11434/api/generate"
    assert captured["json"]["keep_alive"] == "10m"
    assert captured["json"]["options"]["num_predict"] == 80
    assert captured["json"]["options"]["temperature"] == 0.2
    assert "User: What is LangGraph?" in captured["json"]["prompt"]
