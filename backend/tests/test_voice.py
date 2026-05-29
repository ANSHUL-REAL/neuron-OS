from neuronos.voice import VoiceService


def test_voice_service_defaults_to_tiny_en(monkeypatch):
    monkeypatch.delenv("NEURONOS_WHISPER_MODEL", raising=False)

    assert VoiceService().model_name == "tiny.en"


def test_voice_service_normalizes_common_misheard_phrases():
    service = VoiceService()

    assert service._normalize_transcript("open-brand search for latest news videos") == "open brave search for latest news videos"
    assert service._normalize_transcript("open chagibity and ask what is the weather today") == "open chatgpt and ask what is the weather today"
    assert service._normalize_transcript("Open the RAF, then search charge equity and open it.") == "open brave, search chatgpt and open it."
    assert service._normalize_transcript("Open brave and search chat GPP and open it.") == "Open brave and search chatgpt and open it."
    assert service._normalize_transcript("Open Brave and Search Google Cloud and Open Hit.") == "Open Brave and Search Google Cloud and open it."
    assert service._normalize_transcript("Open discard.") == "Open discord."
    assert service._normalize_transcript("Open the brief and open YouTube and play global warming video.") == "Open brave and open YouTube and play global warming video."
    assert service._normalize_transcript("Open the raise and open YouTube and video on global warming.") == "Open brave and open YouTube and video on global warming."
    assert service._normalize_transcript("turn on blue tooth") == "turn on bluetooth"
    assert service._normalize_transcript("increase the wallume") == "increase the volume"
    assert service._normalize_transcript("open male and search chat g p t") == "open gmail and search chatgpt"


def test_voice_service_uses_command_prompt_and_configurable_beam(monkeypatch, tmp_path):
    calls = []

    class FakeModel:
        def transcribe(self, *args, **kwargs):
            calls.append(kwargs)
            return [], {}

    monkeypatch.setenv("NEURONOS_WHISPER_BEAM_SIZE", "3")
    monkeypatch.setattr(VoiceService, "_model", FakeModel())
    monkeypatch.setattr(VoiceService, "_model_name", "tiny.en")

    VoiceService().transcribe(tmp_path / "sample.webm")

    assert calls[0]["beam_size"] == 3
    assert calls[0]["language"] == "en"
    assert "Open Brave" in calls[0]["initial_prompt"]
    assert "ChatGPT" in calls[0]["initial_prompt"]
