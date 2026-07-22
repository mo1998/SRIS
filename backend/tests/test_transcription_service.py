"""
Tests for the transcription service provider abstraction
"""

import os
import json
from unittest.mock import patch

from app.services.transcription_service import (
    FakeTranscriptionProvider,
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
        provider = get_transcription_provider()
        assert provider.name == "fake_transcriber"
