"""
Emotion analysis service - facial emotion detection from recorded interview videos.

Uses DeepFace (MIT, open-source) to classify facial expressions into seven
emotion classes (angry, disgust, fear, happy, sad, surprise, neutral).
Language-independent, so it works for both Arabic and English interviews.

The heavy dependencies (deepface, tensorflow, opencv) are imported lazily so
the API server does not pay the startup cost and tests without them still run.
"""

from dataclasses import dataclass
from typing import List, Optional
import asyncio
import logging
import os

logger = logging.getLogger(__name__)

from app.config import settings


@dataclass
class EmotionSample:
    emotion: str
    confidence: float
    timestamp: float


@dataclass
class EmotionAnalysisResult:
    dominant_emotion: str
    confidence: float
    timeline: List[EmotionSample]


class EmotionAnalysisProvider:
    name: str = "none"
    version: str = "1.0.0"

    async def analyze_video(self, video_path: str) -> Optional[EmotionAnalysisResult]:
        raise NotImplementedError


class DisabledEmotionAnalysisProvider(EmotionAnalysisProvider):
    name = "disabled"

    async def analyze_video(self, video_path: str) -> Optional[EmotionAnalysisResult]:
        return None


class FakeEmotionAnalysisProvider(EmotionAnalysisProvider):
    """Deterministic provider used in tests and fallback scenarios."""

    name = "fake"
    version = "1.0.0"

    async def analyze_video(self, video_path: str) -> Optional[EmotionAnalysisResult]:
        return EmotionAnalysisResult(
            dominant_emotion="neutral",
            confidence=50.0,
            timeline=[
                EmotionSample(emotion="neutral", confidence=0.6, timestamp=0.0),
                EmotionSample(emotion="neutral", confidence=0.7, timestamp=1.0),
            ],
        )


class DeepFaceEmotionAnalysisProvider(EmotionAnalysisProvider):
    name = "deepface"
    version = "1.0.0"

    async def analyze_video(self, video_path: str) -> Optional[EmotionAnalysisResult]:
        if not video_path or not os.path.exists(video_path):
            logger.info("Emotion analysis skipped: video file not found (%s)", video_path)
            return None

        try:
            return await asyncio.to_thread(self._analyze_video_sync, video_path)
        except Exception as exc:
            logger.warning("DeepFace emotion analysis failed: %s", exc)
            return None

    def _analyze_video_sync(self, video_path: str) -> Optional[EmotionAnalysisResult]:
        try:
            import cv2
            from deepface import DeepFace
        except ImportError as exc:
            logger.warning("DeepFace/OpenCV not installed; emotion analysis unavailable: %s", exc)
            return None

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.warning("Cannot open video for emotion analysis: %s", video_path)
            return None

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        sample_seconds = max(1.0, float(settings.EMOTION_FRAME_SAMPLE_SECONDS))
        frame_interval = int(round(fps * sample_seconds))
        if frame_interval < 1:
            frame_interval = 1
        max_frames = max(1, settings.EMOTION_MAX_FRAMES)

        timeline: List[EmotionSample] = []
        frame_idx = 0
        samples_taken = 0
        video_time = 0.0

        while samples_taken < max_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ok, frame = cap.read()
            if not ok:
                break
            video_time = frame_idx / fps if fps > 0 else 0.0

            try:
                analysis = DeepFace.analyze(
                    img_path=frame,
                    actions=["emotion"],
                    enforce_detection=False,
                    detector_backend="opencv",
                    silent=True,
                )
            except Exception as exc:
                logger.debug("DeepFace analyze failed at frame %d: %s", frame_idx, exc)
                frame_idx += frame_interval
                continue

            if isinstance(analysis, list):
                analysis = analysis[0] if analysis else {}
            emotion = analysis.get("dominant_emotion", "neutral") or "neutral"
            emotion_scores = analysis.get("emotion", {}) or {}
            confidence = float(emotion_scores.get(emotion, 0.0) or 0.0) / 100.0

            timeline.append(EmotionSample(
                emotion=emotion,
                confidence=confidence,
                timestamp=round(video_time, 2),
            ))
            samples_taken += 1
            frame_idx += frame_interval

        cap.release()

        if not timeline:
            logger.info("No face samples extracted from %s", video_path)
            return None

        # Dominant emotion = most frequent label across samples
        from collections import Counter
        dominant = Counter(s.emotion for s in timeline).most_common(1)[0][0]

        # Confidence = average per-sample confidence, scaled 0-100
        avg_conf = sum(s.confidence for s in timeline) / len(timeline)

        return EmotionAnalysisResult(
            dominant_emotion=dominant,
            confidence=round(avg_conf * 100.0, 1),
            timeline=timeline,
        )


def get_emotion_provider() -> EmotionAnalysisProvider:
    provider_name = settings.EMOTION_ANALYSIS_PROVIDER or "disabled"
    if provider_name == "deepface":
        return DeepFaceEmotionAnalysisProvider()
    if provider_name == "fake":
        return FakeEmotionAnalysisProvider()
    return DisabledEmotionAnalysisProvider()


def serialize_timeline(timeline: List[EmotionSample]) -> List[dict]:
    return [
        {"emotion": sample.emotion, "confidence": sample.confidence, "timestamp": sample.timestamp}
        for sample in timeline
    ]
