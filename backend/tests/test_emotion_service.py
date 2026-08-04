"""
Tests for the emotion analysis service provider abstraction
"""

import asyncio
from unittest.mock import patch

from app.services.emotion_service import (
    DisabledEmotionAnalysisProvider,
    FakeEmotionAnalysisProvider,
    DeepFaceEmotionAnalysisProvider,
    EmotionAnalysisResult,
    get_emotion_provider,
    serialize_timeline,
)


async def _fake_result():
    return await FakeEmotionAnalysisProvider().analyze_video("/tmp/test.webm")


class TestFakeEmotionAnalysisProvider:

    def test_provider_attributes(self):
        provider = FakeEmotionAnalysisProvider()
        assert provider.name == "fake"
        assert provider.version == "1.0.0"

    async def test_analyze_video_returns_result(self):
        provider = FakeEmotionAnalysisProvider()
        result = await provider.analyze_video("/tmp/test_video.webm")
        assert isinstance(result, EmotionAnalysisResult)
        assert result.dominant_emotion == "neutral"
        assert result.confidence == 50.0
        assert len(result.timeline) == 2


class TestDisabledEmotionAnalysisProvider:

    async def test_returns_none(self):
        provider = DisabledEmotionAnalysisProvider()
        result = await provider.analyze_video("/tmp/test_video.webm")
        assert result is None


class TestDeepFaceEmotionAnalysisProvider:

    def test_provider_attributes(self):
        provider = DeepFaceEmotionAnalysisProvider()
        assert provider.name == "deepface"
        assert provider.version == "1.0.0"

    async def test_missing_video_returns_none(self):
        provider = DeepFaceEmotionAnalysisProvider()
        result = await provider.analyze_video("/tmp/nonexistent_video_xyz.webm")
        assert result is None

    async def test_unreadable_video_returns_none(self, tmp_path):
        provider = DeepFaceEmotionAnalysisProvider()
        bogus = tmp_path / "bogus.webm"
        bogus.write_bytes(b"not a real video")
        result = await provider.analyze_video(str(bogus))
        assert result is None

    async def test_missing_deps_returns_none(self, tmp_path):
        provider = DeepFaceEmotionAnalysisProvider()
        fake_video = tmp_path / "fake.webm"
        fake_video.write_bytes(b"data")
        with patch.dict("sys.modules", {"cv2": None, "deepface": None}):
            result = await provider.analyze_video(str(fake_video))
        assert result is None


class TestGetEmotionProvider:

    def test_default_disabled(self):
        with patch("app.services.emotion_service.settings.EMOTION_ANALYSIS_PROVIDER", "disabled"):
            provider = get_emotion_provider()
            assert provider.name == "disabled"

    def test_fake(self):
        with patch("app.services.emotion_service.settings.EMOTION_ANALYSIS_PROVIDER", "fake"):
            provider = get_emotion_provider()
            assert provider.name == "fake"

    def test_deepface(self):
        with patch("app.services.emotion_service.settings.EMOTION_ANALYSIS_PROVIDER", "deepface"):
            provider = get_emotion_provider()
            assert provider.name == "deepface"


class TestSerializeTimeline:

    def test_serializes_samples(self):
        timeline = asyncio.run(_fake_result()).timeline
        serialized = serialize_timeline(timeline)
        assert len(serialized) == 2
        assert serialized[0]["emotion"] == "neutral"
        assert "confidence" in serialized[0]
        assert "timestamp" in serialized[0]
