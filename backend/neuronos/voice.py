from __future__ import annotations

import os
import re
from pathlib import Path

from .site_catalog import COMMON_TRANSCRIPT_REPLACEMENTS


COMMAND_PROMPT = (
    "NeuronOS desktop assistant commands. "
    "Common words: Open Brave, YouTube, Gmail, ChatGPT, Google Cloud, Discord, "
    "Bluetooth, Wi-Fi, volume up, volume down, increase volume, decrease volume, "
    "brightness, settings, VS Code, remember that."
)


class VoiceService:
    _model = None
    _model_name = None

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or os.environ.get("NEURONOS_WHISPER_MODEL", "tiny.en")
        self.beam_size = _int_env("NEURONOS_WHISPER_BEAM_SIZE", 3)

    def transcribe(self, audio_path: Path) -> str:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            return "Voice transcription requires installing the voice extra."

        if VoiceService._model is None or VoiceService._model_name != self.model_name:
            VoiceService._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
            VoiceService._model_name = self.model_name

        segments, _ = VoiceService._model.transcribe(
            str(audio_path),
            beam_size=self.beam_size,
            language="en",
            initial_prompt=COMMAND_PROMPT,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 450, "speech_pad_ms": 250},
            condition_on_previous_text=False,
            no_speech_threshold=0.55,
        )
        transcript = " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()
        return self._normalize_transcript(transcript)

    def _normalize_transcript(self, transcript: str) -> str:
        normalized = transcript.strip()
        for pattern, replacement in COMMON_TRANSCRIPT_REPLACEMENTS:
            normalized = re.sub(pattern, replacement, normalized, flags=re.I)
        normalized = re.sub(r"\bthen\s+", "", normalized, flags=re.I)
        normalized = re.sub(r"\bblue\s+tooth\b", "bluetooth", normalized, flags=re.I)
        normalized = re.sub(r"\bwi\s*fi\b", "wifi", normalized, flags=re.I)
        normalized = re.sub(r"\b(?:wallume|wolume|value|walume)\b", "volume", normalized, flags=re.I)
        normalized = re.sub(r"\bchat\s+g\s*p\s*t\b", "chatgpt", normalized, flags=re.I)
        normalized = re.sub(r"\bopen\s+male\b", "open gmail", normalized, flags=re.I)
        normalized = re.sub(r"\bopen\s+mail\b", "open gmail", normalized, flags=re.I)
        normalized = re.sub(r"\s+", " ", normalized)
        normalized = re.sub(r"\s+([,.!?])", r"\1", normalized)
        return normalized.strip()


def _int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, default)))
    except ValueError:
        return default
