"""
Tests for the transcription service provider abstraction
"""

import os
import json
from unittest.mock import patch

from app.services.transcription_service import (
    FakeTranscriptionProvider,
    WhisperTranscriptionProvider,
    TranscriptionResult,
    get_transcription_provider,
)


class TestFakeTranscriptionProvider:

    def test_provider_attributes(self):
        provider = FakeTranscriptionProvider()
        assert provider.name == "fake_transcriber"
        assert provider.version == "1.0.0"

    async def test_transcribe_audio_returns_result(self):
        provider = FakeTranscriptionProvider()
        result = await provider.transcribe_audio("/tmp/test_audio.mp3")
        assert result.transcript is not None
        assert "Fake transcription" in result.transcript
        assert result.detected_language == "en"
        assert result.confidence == 0.95

    def test_get_transcription_provider_fake(self):
        with patch("app.services.transcription_service.settings.TRANSCRIPTION_PROVIDER", "fake"):
            provider = get_transcription_provider()
            assert provider.name == "fake_transcriber"


class TestWhisperTranscriptionProvider:

    def test_provider_attributes(self):
        provider = WhisperTranscriptionProvider()
        assert provider.name == "whisper"
        assert provider.version == "1.0.0"

    def test_get_transcription_provider_whisper(self):
        with patch("app.services.transcription_service.settings.TRANSCRIPTION_PROVIDER", "whisper"):
            provider = get_transcription_provider()
            assert provider.name == "whisper"

    async def test_transcribe_error_returns_empty(self, tmp_path):
        provider = WhisperTranscriptionProvider()
        fake_audio = tmp_path / "audio.mp3"
        fake_audio.write_bytes(b"not really audio")

        async def fake_model_transcribe(*args, **kwargs):
            raise RuntimeError("model load failed")

        async def fake_to_thread(fn, *args, **kwargs):
            return fn()

        with patch.object(provider, "_get_model") as mock_model, \
             patch("app.services.transcription_service.asyncio.to_thread", side_effect=fake_to_thread):
            mock_model.return_value = type("M", (), {
                "transcribe": fake_model_transcribe,
            })()
            result = await provider.transcribe_audio(str(fake_audio))
        assert result.transcript == ""
        assert result.confidence == 0.0

    async def test_transcribe_success_parses_segments(self, tmp_path):
        provider = WhisperTranscriptionProvider()
        fake_audio = tmp_path / "audio.mp3"
        fake_audio.write_bytes(b"data")

        def fake_segments():
            for text in (" hello ", " world"):
                yield type("S", (), {"text": text})()

        class FakeInfo:
            language = "ar"
            language_probability = 0.87

        def fake_transcribe(*args, **kwargs):
            return fake_segments(), FakeInfo()

        model = type("M", (), {"transcribe": fake_transcribe})()

        async def fake_to_thread(fn, *args, **kwargs):
            return fn()

        with patch.object(provider, "_get_model", return_value=model), \
             patch("app.services.transcription_service.asyncio.to_thread", side_effect=fake_to_thread):
            result = await provider.transcribe_audio(str(fake_audio))
        assert isinstance(result, TranscriptionResult)
        assert result.transcript == "hello world"
        assert result.detected_language == "ar"
        assert result.confidence == 0.87
