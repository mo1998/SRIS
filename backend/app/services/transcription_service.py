"""
Transcription service - audio file transcription with provider abstraction
"""

from dataclasses import dataclass
from typing import Optional, Protocol
import asyncio
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

import redis
from fastapi import BackgroundTasks
from rq import Queue
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.config import settings
from app.database import SessionLocal
from app.models import QuestionAnswer


@dataclass
class TranscriptionResult:
    transcript: str
    detected_language: Optional[str] = None
    confidence: float = 0.0


class TranscriptionProvider(Protocol):
    name: str
    version: str

    async def transcribe_audio(self, audio_path: str) -> TranscriptionResult:
        ...


class FakeTranscriptionProvider:
    name = "fake_transcriber"
    version = "1.0.0"

    async def transcribe_audio(self, audio_path: str) -> TranscriptionResult:
        filename = os.path.basename(audio_path)
        return TranscriptionResult(
            transcript=f"[Fake transcription of {filename}] This is a simulated transcription of the candidate's audio response.",
            detected_language="en",
            confidence=0.95,
        )


class WhisperTranscriptionProvider:
    """Real speech-to-text using faster-whisper (CTranslate2).

    Multilingual Whisper model supports 99 languages including Arabic and
    English. Runs on CPU with int8 quantization. Heavy imports are lazy so the
    API server stays fast and tests without the dependency still run.
    """

    name = "whisper"
    version = "1.0.0"

    def __init__(self) -> None:
        self._model = None

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                settings.WHISPER_MODEL_SIZE,
                device=settings.WHISPER_DEVICE,
                compute_type=settings.WHISPER_COMPUTE_TYPE,
            )
        return self._model

    async def transcribe_audio(self, audio_path: str) -> TranscriptionResult:
        model = await asyncio.to_thread(self._get_model)

        def _run() -> TranscriptionResult:
            segments, info = model.transcribe(
                audio_path,
                language=None,
                vad_filter=settings.WHISPER_VAD_FILTER,
            )
            text = " ".join(segment.text.strip() for segment in segments if segment.text and segment.text.strip()).strip()
            detected_language = getattr(info, "language", None)
            confidence = float(getattr(info, "language_probability", 0.0) or 0.0)
            return TranscriptionResult(
                transcript=text,
                detected_language=detected_language,
                confidence=round(confidence, 3),
            )

        try:
            return await asyncio.to_thread(_run)
        except Exception as exc:
            return TranscriptionResult(
                transcript="",
                detected_language=None,
                confidence=0.0,
            )


fake_transcription_provider = FakeTranscriptionProvider()
whisper_transcription_provider = WhisperTranscriptionProvider()


def get_transcription_provider() -> TranscriptionProvider:
    provider_name = settings.TRANSCRIPTION_PROVIDER
    if provider_name == "whisper":
        return whisper_transcription_provider
    return fake_transcription_provider


async def transcribe_answer(answer_id: int, db: Session) -> TranscriptionResult:
    answer = db.query(QuestionAnswer).filter(QuestionAnswer.id == answer_id).first()
    if not answer:
        return TranscriptionResult(transcript="", detected_language=None, confidence=0.0)

    # Audio file preferred; fall back to video file (video recordings capture
    # the audio track too, so spoken answers can still be transcribed).
    media_path = None
    for candidate in (answer.audio_file_path, answer.video_file_path):
        if candidate and os.path.exists(candidate):
            media_path = candidate
            break
    if not media_path:
        return TranscriptionResult(transcript="", detected_language=None, confidence=0.0)

    provider = get_transcription_provider()
    result = await provider.transcribe_audio(media_path)

    from datetime import datetime

    answer.transcript = result.transcript
    answer.transcript_updated_at = datetime.utcnow()
    db.commit()
    return result


async def transcribe_response_answers_background(response_id: int) -> None:
    db = SessionLocal()
    failed = 0
    total = 0
    try:
        answers = db.query(QuestionAnswer).filter(
            QuestionAnswer.response_id == response_id,
            or_(
                QuestionAnswer.audio_file_path.isnot(None),
                QuestionAnswer.video_file_path.isnot(None),
            ),
        ).all()
        for answer in answers:
            total += 1
            try:
                await transcribe_answer(answer.id, db)
            except Exception as exc:
                failed += 1
                logger.error("Background transcription failed for answer %s of response %s: %s", answer.id, response_id, exc)
    finally:
        db.close()

    if failed:
        logger.error("Background transcription completed with failures: %d/%d answers failed for response %s", failed, total, response_id)
    elif total:
        logger.info("Background transcription completed for response %s: %d answers", response_id, total)


def run_transcription_job(response_id: int) -> None:
    asyncio.run(transcribe_response_answers_background(response_id))


def enqueue_transcription(response_id: int, background_tasks: BackgroundTasks) -> str:
    if settings.TRANSCRIPTION_QUEUE_BACKEND == "rq":
        redis_connection = redis.from_url(settings.REDIS_URL)
        queue = Queue(settings.TRANSCRIPTION_QUEUE_NAME, connection=redis_connection)
        queue.enqueue(run_transcription_job, response_id, job_timeout=300)
        return "rq"

    background_tasks.add_task(transcribe_response_answers_background, response_id)
    return "background"


async def get_transcription_health() -> dict:
    provider = get_transcription_provider()
    healthy = True
    status = "available"
    last_error = None

    if provider.name == "whisper":
        try:
            await asyncio.wait_for(
                asyncio.to_thread(provider._get_model),
                timeout=max(10, min(settings.EMOTION_ANALYSIS_TIMEOUT_SECONDS, 60)),
            )
            status = "whisper_available"
        except asyncio.TimeoutError:
            healthy = False
            status = "whisper_unavailable"
            last_error = "Model load timed out"
        except Exception as exc:
            healthy = False
            status = "whisper_unavailable"
            last_error = str(exc)

    return {
        "provider": provider.name,
        "provider_version": getattr(provider, "version", None),
        "model_name": settings.WHISPER_MODEL_SIZE if provider.name == "whisper" else None,
        "queue_backend": settings.TRANSCRIPTION_QUEUE_BACKEND,
        "healthy": healthy,
        "status": status,
        "last_error": last_error,
        "checked_at": datetime.utcnow(),
    }
