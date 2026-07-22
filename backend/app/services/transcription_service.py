"""
Transcription service - audio file transcription with provider abstraction
"""

from dataclasses import dataclass
from typing import Optional, Protocol
import asyncio
import os

import redis
from fastapi import BackgroundTasks
from rq import Queue
from sqlalchemy.orm import Session

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


fake_transcription_provider = FakeTranscriptionProvider()


def get_transcription_provider() -> TranscriptionProvider:
    provider_name = settings.TRANSCRIPTION_PROVIDER
    if provider_name == "fake":
        return fake_transcription_provider
    return fake_transcription_provider


async def transcribe_answer(answer_id: int, db: Session) -> None:
    answer = db.query(QuestionAnswer).filter(QuestionAnswer.id == answer_id).first()
    if not answer or not answer.audio_file_path:
        return

    if not os.path.exists(answer.audio_file_path):
        return

    provider = get_transcription_provider()
    result = await provider.transcribe_audio(answer.audio_file_path)

    from datetime import datetime

    answer.transcript = result.transcript
    answer.transcript_updated_at = datetime.utcnow()
    db.commit()


async def transcribe_response_answers_background(response_id: int) -> None:
    db = SessionLocal()
    try:
        answers = db.query(QuestionAnswer).filter(
            QuestionAnswer.response_id == response_id,
            QuestionAnswer.audio_file_path.isnot(None),
        ).all()
        for answer in answers:
            await transcribe_answer(answer.id, db)
    finally:
        db.close()


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
