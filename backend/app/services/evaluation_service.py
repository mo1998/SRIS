"""
Evaluation service - deterministic answer scoring and candidate evaluation
"""

from dataclasses import dataclass
import asyncio
import json
import logging
import os
import re
import hashlib
from typing import Dict, List, Optional, Protocol
import httpx
import redis
from fastapi import BackgroundTasks
from rq import Queue
from sqlalchemy.orm import Session
from datetime import datetime

logger = logging.getLogger(__name__)

from app.config import settings
from app.database import SessionLocal
from app.models import CandidateResponse, EvaluationRun, EvaluationScore, QuestionAnswer, InterviewQuestion, Interview


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have", "how", "in", "is", "it", "of",
    "on", "or", "that", "the", "their", "this", "to", "up", "uses", "with", "you", "your",
}


@dataclass
class EvaluationResult:
    score: float
    feedback: str
    evidence: Dict[str, object]


class EvaluationProvider(Protocol):
    name: str
    version: str

    async def evaluate_answer(self, answer_text: str, expected_answer: str, rubric_criteria: Optional[List[Dict[str, object]]] = None) -> EvaluationResult:
        ...


class BaselineEvaluationProvider:
    name = "deterministic_baseline"
    version = "1.0.0"

    async def evaluate_answer(self, answer_text: str, expected_answer: str, rubric_criteria: Optional[List[Dict[str, object]]] = None) -> EvaluationResult:
        answer_tokens = normalize_tokens(answer_text)
        rubric_text = build_rubric_text(rubric_criteria or [])
        expected_tokens = normalize_tokens(" ".join([expected_answer or "", rubric_text]))

        if not answer_tokens:
            return EvaluationResult(
                score=0.0,
                feedback="No answer provided. Evidence: empty candidate response.",
                evidence={"matched_keywords": [], "missing_keywords": expected_tokens, "keyword_coverage": 0.0, "length_score": 0.0, "rubric_criteria": rubric_criteria or []},
            )

        if not expected_tokens:
            length_score = score_answer_length(answer_tokens, minimum_tokens=8)
            return EvaluationResult(
                score=round(length_score * 0.7, 1),
                feedback="No expected answer was configured; scored using answer completeness only.",
                evidence={"matched_keywords": [], "missing_keywords": [], "keyword_coverage": None, "length_score": round(length_score, 1), "rubric_criteria": rubric_criteria or []},
            )

        expected_set = set(expected_tokens)
        answer_set = set(answer_tokens)
        matched_keywords = sorted(expected_set.intersection(answer_set))
        missing_keywords = sorted(expected_set.difference(answer_set))
        keyword_coverage = len(matched_keywords) / len(expected_set)
        length_score = score_answer_length(answer_tokens, minimum_tokens=max(8, int(len(expected_tokens) * 0.75))) / 100
        final_score = round(((keyword_coverage * 0.8) + (length_score * 0.2)) * 100, 1)
        feedback = (
            f"{self.name} v{self.version}: matched {len(matched_keywords)} of {len(expected_set)} expected key concepts "
            f"({', '.join(matched_keywords) if matched_keywords else 'none'})."
        )
        if missing_keywords:
            feedback += f" Missing concepts: {', '.join(missing_keywords[:6])}."

        return EvaluationResult(
            score=min(100.0, max(0.0, final_score)),
            feedback=feedback,
            evidence={
                "provider": self.name,
                "provider_version": self.version,
                "matched_keywords": matched_keywords,
                "missing_keywords": missing_keywords,
                "keyword_coverage": round(keyword_coverage * 100, 1),
                "length_score": round(length_score * 100, 1),
                "rubric_criteria": rubric_criteria or [],
            },
        )


class LocalVLLMEvaluationProvider:
    name = "local_vllm"
    version = "1.0.0"

    def __init__(self, fallback_provider: EvaluationProvider):
        self.fallback_provider = fallback_provider

    async def evaluate_answer(self, answer_text: str, expected_answer: str, rubric_criteria: Optional[List[Dict[str, object]]] = None) -> EvaluationResult:
        if not answer_text.strip():
            return await self.fallback_provider.evaluate_answer(answer_text, expected_answer, rubric_criteria)

        try:
            payload = {
                "model": settings.LOCAL_LLM_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "/no_think You evaluate structured interview answers. Do not show reasoning. "
                            "Use the expected answer and rubric criteria as the scoring contract. "
                            "Return valid compact JSON only with keys: score, feedback_en, feedback_ar, "
                            "matched_criteria, missing_criteria, evidence. Score must be 0-100."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Expected answer: {expected_answer}\n"
                            f"Rubric criteria JSON: {json.dumps(rubric_criteria or [], ensure_ascii=False)}\n"
                            f"Candidate answer: {answer_text}"
                        ),
                    },
                ],
                "temperature": 0,
                "max_tokens": 512,
            }
            async with httpx.AsyncClient(timeout=settings.LOCAL_LLM_TIMEOUT_SECONDS) as client:
                response = await client.post(f"{settings.LOCAL_LLM_BASE_URL.rstrip('/')}/chat/completions", json=payload)
                response.raise_for_status()
            completion = response.json()["choices"][0]["message"]["content"]
            parsed = parse_llm_json(completion)
            score = normalize_llm_score(parsed.get("score", 0))
            feedback_en = str(parsed.get("feedback_en") or "No English feedback returned.")
            feedback_ar = str(parsed.get("feedback_ar") or "No Arabic feedback returned.")
            evidence = {
                "provider": self.name,
                "provider_version": self.version,
                "model": settings.LOCAL_LLM_MODEL,
                "prompt_version": settings.EVALUATION_PROMPT_VERSION,
                "matched_criteria": parsed.get("matched_criteria", []),
                "missing_criteria": parsed.get("missing_criteria", []),
                "evidence": parsed.get("evidence", ""),
                "rubric_criteria": rubric_criteria or [],
            }
            return EvaluationResult(
                score=score,
                feedback=f"{self.name} {settings.LOCAL_LLM_MODEL}: {feedback_en} Arabic feedback: {feedback_ar}",
                evidence=evidence,
            )
        except Exception as exc:
            fallback = await self.fallback_provider.evaluate_answer(answer_text, expected_answer, rubric_criteria)
            fallback.evidence.update({
                "provider_fallback_from": self.name,
                "provider_fallback_reason": str(exc),
                "requested_model": settings.LOCAL_LLM_MODEL,
            })
            fallback.feedback = f"LLM evaluation unavailable; used deterministic fallback. {fallback.feedback}"
            return fallback


def normalize_tokens(text: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [token for token in tokens if token not in STOPWORDS and len(token) > 1]


def score_answer_length(answer_tokens: List[str], minimum_tokens: int) -> float:
    if minimum_tokens <= 0:
        return 100.0
    return min(100.0, (len(answer_tokens) / minimum_tokens) * 100)


def build_rubric_text(rubric_criteria: List[Dict[str, object]]) -> str:
    return " ".join(
        " ".join(str(criterion.get(key) or "") for key in ("name", "description"))
        for criterion in rubric_criteria
    )


def serialize_rubric_criteria(question: InterviewQuestion) -> List[Dict[str, object]]:
    return [
        {
            "name": criterion.name,
            "description": criterion.description,
            "weight": criterion.weight,
        }
        for criterion in sorted(question.rubric_criteria, key=lambda item: item.order_index or 0)
    ]


baseline_provider = BaselineEvaluationProvider()
local_vllm_provider = LocalVLLMEvaluationProvider(baseline_provider)


def get_evaluation_provider() -> EvaluationProvider:
    if settings.EVALUATION_PROVIDER == "deterministic_baseline":
        return baseline_provider
    return local_vllm_provider


def get_emotion_provider_name() -> str:
    from app.services.emotion_service import get_emotion_provider
    return get_emotion_provider().name


def parse_llm_json(content: str) -> Dict[str, object]:
    cleaned = re.sub(r"<think>.*?</think>", "", content or "", flags=re.DOTALL).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM response did not contain a JSON object")
    return json.loads(cleaned[start:end + 1])


def normalize_llm_score(raw_score: object) -> float:
    score = float(raw_score)
    if 0 <= score <= 10:
        score *= 10
    return min(100.0, max(0.0, round(score, 1)))


async def evaluate_answer_similarity(answer_text: str, expected_answer: str) -> tuple[float, str]:
    """Evaluate an answer using the configured local evaluation provider."""
    result = await get_evaluation_provider().evaluate_answer(answer_text, expected_answer)
    return result.score, result.feedback


async def calculate_emotion_score(emotion_timeline: str) -> float:
    """
    Calculate confidence score based on emotion timeline
    Returns a score between 0 and 100
    """
    if not emotion_timeline:
        return 50.0  # Default if no emotion data
    
    try:
        timeline = json.loads(emotion_timeline)
        
        positive_emotions = ["happy", "neutral", "surprise"]
        positive_count = 0
        total_count = len(timeline)
        
        for record in timeline:
            emotion = record.get("emotion", "").lower()
            if emotion in positive_emotions:
                positive_count += 1
        
        # Calculate confidence based on positive emotion ratio
        confidence = (positive_count / total_count) * 100 if total_count > 0 else 50.0
        return confidence
        
    except Exception as e:
        logger.warning("Error calculating emotion score: %s", e)
        return 50.0


async def evaluate_candidate_response(response_id: int, db: Session, evaluation_run_id: Optional[int] = None):
    """
    Complete evaluation of a candidate's interview response
    """
    # Get response and answers
    response = db.query(CandidateResponse).filter(CandidateResponse.id == response_id).first()
    if not response:
        return
    
    answers = db.query(QuestionAnswer).filter(QuestionAnswer.response_id == response_id).all()
    
    if not answers:
        return

    provider = get_evaluation_provider()
    if evaluation_run_id:
        evaluation_run = db.query(EvaluationRun).filter(EvaluationRun.id == evaluation_run_id).first()
        if not evaluation_run:
            return
        evaluation_run.status = "running"
        evaluation_run.started_at = evaluation_run.started_at or datetime.utcnow()
    else:
        evaluation_run = create_evaluation_run(response_id, db, status="running")
    
    total_score = 0.0
    total_weight = 0.0

    emotion_samples_by_answer = {}

    try:
        # Analyze facial emotion from recorded videos. Runs as a parallel
        # pre-pass (bounded by asyncio.semaphore) so DeepFace latency does not
        # serialize the whole evaluation; results are keyed by answer id.
        emotion_results = {}
        video_answers = [a for a in answers if a.video_file_path]
        if video_answers:
            from app.services.emotion_service import get_emotion_provider, serialize_timeline
            emotion_provider = get_emotion_provider()
            concurrency = min(len(video_answers), 4) if settings.EMOTION_ANALYSIS_PARALLEL else 1
            semaphore = asyncio.Semaphore(concurrency)

            async def _analyze(answer: QuestionAnswer) -> None:
                async with semaphore:
                    emotion_result = await emotion_provider.analyze_video(answer.video_file_path)
                    if emotion_result and emotion_result.timeline:
                        emotion_results[answer.id] = (emotion_result, serialize_timeline(emotion_result.timeline))

            await asyncio.gather(*(_analyze(a) for a in video_answers))

        # Evaluate each answer
        for answer in answers:
            question = db.query(InterviewQuestion).filter(InterviewQuestion.id == answer.question_id).first()
            if not question:
                continue

            # Apply emotion analysis result (if any)
            emotion_result = emotion_results.get(answer.id)
            if emotion_result:
                result, timeline = emotion_result
                answer.emotion_during_answer = result.dominant_emotion
                emotion_samples_by_answer[answer.id] = timeline

            # Ensure a transcript exists for recorded answers so spoken responses
            # can be scored. Transcription runs inline (not background) to avoid
            # racing the background transcription job.
            answer_text = answer.answer_text or ""
            if not answer_text.strip() and (answer.audio_file_path or answer.video_file_path):
                from app.services.transcription_service import transcribe_answer
                try:
                    await transcribe_answer(answer.id, db)
                    db.refresh(answer)
                    answer_text = answer.transcript or ""
                except Exception as exc:
                    logger.warning("Transcription failed for answer %s: %s", answer.id, exc)

            # Score the answer
            if answer_text and question.expected_answer:
                result = await provider.evaluate_answer(answer_text, question.expected_answer, serialize_rubric_criteria(question))
                answer.score = result.score
                answer.feedback = result.feedback
            else:
                result = EvaluationResult(
                    score=0.0,
                    feedback="No answer provided",
                    evidence={"provider": provider.name, "reason": "empty_answer"},
                )
                answer.score = 0.0
                answer.feedback = result.feedback

            db.add(EvaluationScore(
                evaluation_run_id=evaluation_run.id,
                question_answer_id=answer.id,
                question_id=question.id,
                score=result.score,
                feedback_en=extract_feedback(result.feedback, "en"),
                feedback_ar=extract_feedback(result.feedback, "ar"),
                evidence_json=json.dumps(result.evidence, ensure_ascii=False),
            ))

            # Calculate emotion during this answer (legacy frontend-submitted timeline,
            # only when video-based facial analysis produced no result)
            if response.emotion_timeline and answer.id not in emotion_samples_by_answer:
                try:
                    timeline = json.loads(response.emotion_timeline)
                    if timeline:
                        # Get most common emotion during answer time
                        emotions = [r.get("emotion", "neutral") for r in timeline]
                        answer.emotion_during_answer = max(set(emotions), key=emotions.count)
                except Exception:
                    pass

            # Weighted score
            total_score += (answer.score or 0.0) * question.weight
            total_weight += question.weight
    except Exception as exc:
        evaluation_run.status = "failed"
        evaluation_run.error = str(exc)
        evaluation_run.completed_at = datetime.utcnow()
        db.commit()
        raise
    
    # Calculate total score
    if total_weight > 0:
        response.total_score = (total_score / total_weight)
    else:
        response.total_score = 0.0
    
    # Calculate emotion/confidence score
    if emotion_samples_by_answer:
        # Aggregate per-answer facial emotion samples into a response timeline
        all_samples = []
        for answer_id in sorted(emotion_samples_by_answer):
            all_samples.extend(emotion_samples_by_answer[answer_id])
        if all_samples:
            response.emotion_timeline = json.dumps(all_samples, ensure_ascii=False)
            from collections import Counter
            dominant = Counter(s.get("emotion", "neutral") for s in all_samples).most_common(1)
            if dominant:
                response.dominant_emotion = dominant[0][0]
            response.confidence_score = await calculate_emotion_score(response.emotion_timeline)
    elif response.emotion_timeline:
        response.confidence_score = await calculate_emotion_score(response.emotion_timeline)
    
    # Calculate overall quality score
    quality_scores = []
    if response.voice_quality_score is not None:
        quality_scores.append(response.voice_quality_score)
    if response.background_quality_score is not None:
        quality_scores.append(response.background_quality_score)
    if response.face_visibility_score is not None:
        quality_scores.append(response.face_visibility_score)
    if response.lighting_score is not None:
        quality_scores.append(response.lighting_score)

    # Blend quality + emotion confidence into the total score so captured
    # metrics actually influence the outcome (configurable weights).
    base_score = response.total_score or 0.0
    if quality_scores:
        quality_avg = sum(quality_scores) / len(quality_scores)
        base_score = base_score * (1 - settings.SCORING_QUALITY_WEIGHT) + quality_avg * settings.SCORING_QUALITY_WEIGHT
    if response.confidence_score is not None:
        base_score = base_score * (1 - settings.SCORING_EMOTION_WEIGHT) + response.confidence_score * settings.SCORING_EMOTION_WEIGHT
    response.total_score = base_score

    # Get interview pass score
    interview = db.query(Interview).filter(Interview.id == response.interview_id).first()
    pass_score = interview.pass_score if interview else 70.0
    
    # Determine if passed
    response.passed = response.total_score >= pass_score if response.total_score else False
    evaluation_run.status = "completed"
    evaluation_run.raw_summary = json.dumps({
        "total_score": response.total_score,
        "passed": response.passed,
        "answer_count": len(answers),
    }, ensure_ascii=False)
    evaluation_run.completed_at = datetime.utcnow()
    
    db.commit()
    
    # Send completion email
    if response.candidate_email:
        from app.services.email_service import send_completion_email
        interview_title = interview.title if interview else "Interview"
        results_link = ""
        if response.invitation_id:
            from app.models import Invitation
            invitation = db.query(Invitation).filter(Invitation.id == response.invitation_id).first()
            if invitation and invitation.unique_token:
                results_link = f"{settings.FRONTEND_URL}/results/{invitation.unique_token}"
        try:
            await send_completion_email(
                to_email=response.candidate_email,
                candidate_name=response.candidate_name,
                interview_title=interview_title,
                score=response.total_score or 0.0,
                passed=response.passed or False,
                results_link=results_link,
            )
        except Exception as exc:
            logger.warning("Completion email failed: %s", exc)

    # Fire webhooks
    try:
        from app.services.webhook_service import fire_event, build_event_payload
        org_id = interview.organization_id if interview else None
        payload = build_event_payload(
            "evaluation.completed",
            evaluation_run.id,
            "evaluation_run",
            {
                "response_id": response.id,
                "interview_id": response.interview_id,
                "total_score": response.total_score,
                "passed": response.passed,
            },
        )
        await fire_event("evaluation.completed", payload, org_id)
    except Exception as exc:
        logger.warning("Webhook fire failed: %s", exc)


def create_evaluation_run(response_id: int, db: Session, status: str = "queued") -> EvaluationRun:
    provider = get_evaluation_provider()
    evaluation_run = EvaluationRun(
        response_id=response_id,
        provider=provider.name,
        provider_version=getattr(provider, "version", None),
        model_name=settings.LOCAL_LLM_MODEL,
        config_hash=get_evaluation_config_hash(provider),
        status=status,
        started_at=datetime.utcnow(),
    )
    db.add(evaluation_run)
    db.flush()
    return evaluation_run


async def evaluate_candidate_response_background(response_id: int, evaluation_run_id: int) -> None:
    db = SessionLocal()
    try:
        evaluation_run = db.query(EvaluationRun).filter(EvaluationRun.id == evaluation_run_id).first()
        if evaluation_run:
            evaluation_run.status = "running"
            db.commit()
        await evaluate_candidate_response(response_id, db, evaluation_run_id=evaluation_run_id)
    finally:
        db.close()


def run_evaluation_job(response_id: int, evaluation_run_id: int) -> None:
    asyncio.run(evaluate_candidate_response_background(response_id, evaluation_run_id))


def enqueue_evaluation_run(response_id: int, evaluation_run_id: int, background_tasks: BackgroundTasks) -> str:
    if settings.EVALUATION_QUEUE_BACKEND == "rq":
        redis_connection = redis.from_url(settings.REDIS_URL)
        queue = Queue(settings.EVALUATION_QUEUE_NAME, connection=redis_connection)
        queue.enqueue(run_evaluation_job, response_id, evaluation_run_id, job_timeout=600)
        return "rq"

    background_tasks.add_task(evaluate_candidate_response_background, response_id, evaluation_run_id)
    return "background"


def get_evaluation_config_hash(provider: EvaluationProvider) -> str:
    payload = {
        "provider": provider.name,
        "provider_version": getattr(provider, "version", None),
        "prompt_version": settings.EVALUATION_PROMPT_VERSION,
        "model": settings.LOCAL_LLM_MODEL if provider.name == "local_vllm" else None,
        "base_url": settings.LOCAL_LLM_BASE_URL if provider.name == "local_vllm" else None,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def extract_feedback(feedback: str, language: str) -> str:
    if language == "ar" and "Arabic feedback:" in feedback:
        return feedback.split("Arabic feedback:", 1)[1].strip()
    if language == "en" and "Arabic feedback:" in feedback:
        return feedback.split("Arabic feedback:", 1)[0].strip()
    return feedback


def generate_candidate_report(response_id: int, db: Session) -> Dict:
    """Generate detailed report for a candidate"""
    response = db.query(CandidateResponse).filter(CandidateResponse.id == response_id).first()
    if not response:
        return {}
    
    interview = db.query(Interview).filter(Interview.id == response.interview_id).first()
    answers = db.query(QuestionAnswer).filter(QuestionAnswer.response_id == response_id).all()
    evaluation_run = (
        db.query(EvaluationRun)
        .filter(EvaluationRun.response_id == response_id, EvaluationRun.status == "completed")
        .order_by(EvaluationRun.completed_at.desc(), EvaluationRun.id.desc())
        .first()
    )
    scores_by_answer_id = {}
    if evaluation_run:
        scores = db.query(EvaluationScore).filter(EvaluationScore.evaluation_run_id == evaluation_run.id).all()
        scores_by_answer_id = {score.question_answer_id: score for score in scores}
    
    answer_details = []
    for answer in answers:
        question = db.query(InterviewQuestion).filter(InterviewQuestion.id == answer.question_id).first()
        evaluation_score = scores_by_answer_id.get(answer.id)
        answer_details.append({
            "question_id": answer.question_id,
            "question": question.question_text if question else "Unknown",
            "expected_answer": question.expected_answer if question else "",
            "answer_text": answer.answer_text,
            "transcript": answer.transcript,
            "score": answer.score,
            "feedback": answer.feedback,
            "feedback_en": evaluation_score.feedback_en if evaluation_score else None,
            "feedback_ar": evaluation_score.feedback_ar if evaluation_score else None,
            "evidence": parse_evidence_json(evaluation_score.evidence_json) if evaluation_score else None,
            "emotion": answer.emotion_during_answer,
            "video_file_path": answer.video_file_path,
            "audio_file_path": answer.audio_file_path
        })
    
    disclosure_text = (
        "This report was generated with AI-assisted evaluation. "
        "Scores and feedback are subject to human review. "
        "Final hiring decisions are made by human reviewers."
    )

    return {
        "response_id": response.id,
        "candidate_name": response.candidate_name,
        "candidate_email": response.candidate_email,
        "interview_title": interview.title if interview else "Unknown",
        "total_score": response.total_score or 0.0,
        "passed": response.passed or False,
        "voice_quality": response.voice_quality_score or 0.0,
        "background_quality": response.background_quality_score or 0.0,
        "face_visibility": response.face_visibility_score or 0.0,
        "lighting": response.lighting_score or 0.0,
        "dominant_emotion": response.dominant_emotion or "neutral",
        "confidence_score": response.confidence_score or 50.0,
        "reviewer_decision": response.reviewer_decision.value if response.reviewer_decision else "pending",
        "ai_disclosure": disclosure_text,
        "answers": answer_details,
        "feedback": build_report_feedback(response),
        "started_at": response.started_at,
        "completed_at": response.completed_at,
        "evaluation_provider": evaluation_run.provider if evaluation_run else None,
        "evaluation_model": evaluation_run.model_name if evaluation_run else None,
        "evaluation_status": evaluation_run.status if evaluation_run else None,
        "evaluation_completed_at": evaluation_run.completed_at if evaluation_run else None,
        "generated_at": datetime.utcnow(),
    }


def parse_evidence_json(evidence_json: str) -> Dict[str, object]:
    if not evidence_json:
        return {}
    try:
        return json.loads(evidence_json)
    except json.JSONDecodeError:
        return {"raw": evidence_json}


def build_report_feedback(response: CandidateResponse) -> str:
    if response.passed:
        return "Candidate passed the interview based on the configured pass score."
    return "Candidate did not meet the configured pass score."


def generate_employer_report(interview_id: int, db: Session) -> Dict:
    """Generate ranked report of all candidates for an employer"""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        return {}
    
    responses = (
        db.query(CandidateResponse)
        .filter(
            CandidateResponse.interview_id == interview_id,
            CandidateResponse.status == "completed"
        )
        .order_by(CandidateResponse.total_score.desc())
        .all()
    )
    
    candidates = []
    for response in responses:
        evaluation_run = (
            db.query(EvaluationRun)
            .filter(EvaluationRun.response_id == response.id, EvaluationRun.status == "completed")
            .order_by(EvaluationRun.completed_at.desc(), EvaluationRun.id.desc())
            .first()
        )
        candidates.append({
            "response_id": response.id,
            "rank": len(candidates) + 1,
            "name": response.candidate_name,
            "email": response.candidate_email,
            "total_score": response.total_score or 0.0,
            "passed": response.passed or False,
            "confidence_score": response.confidence_score or 50.0,
            "voice_quality": response.voice_quality_score or 0.0,
            "face_visibility": response.face_visibility_score or 0.0,
            "dominant_emotion": response.dominant_emotion or "neutral",
            "reviewer_decision": response.reviewer_decision.value if response.reviewer_decision else "pending",
            "completed_at": response.completed_at,
            "evaluation_provider": evaluation_run.provider if evaluation_run else None,
            "evaluation_model": evaluation_run.model_name if evaluation_run else None,
            "evaluation_status": evaluation_run.status if evaluation_run else None,
            "evaluation_completed_at": evaluation_run.completed_at if evaluation_run else None,
        })
    
    # Calculate statistics
    total_candidates = len(responses)
    avg_score = sum(r.total_score or 0.0 for r in responses) / total_candidates if total_candidates > 0 else 0.0
    pass_count = sum(1 for r in responses if r.passed)
    pass_rate = (pass_count / total_candidates * 100) if total_candidates > 0 else 0.0
    
    return {
        "interview_id": interview_id,
        "interview_title": interview.title,
        "total_candidates": total_candidates,
        "average_score": avg_score,
        "pass_rate": pass_rate,
        "pass_score": interview.pass_score,
        "candidates": candidates,
        "generated_at": datetime.utcnow()
    }


def generate_candidate_evaluation_audit(response_id: int, db: Session) -> List[Dict]:
    runs = (
        db.query(EvaluationRun)
        .filter(EvaluationRun.response_id == response_id)
        .order_by(EvaluationRun.started_at.desc(), EvaluationRun.id.desc())
        .all()
    )

    audit_runs = []
    for run in runs:
        scores = (
            db.query(EvaluationScore)
            .filter(EvaluationScore.evaluation_run_id == run.id)
            .order_by(EvaluationScore.id.asc())
            .all()
        )
        audit_runs.append({
            "id": run.id,
            "response_id": run.response_id,
            "provider": run.provider,
            "provider_version": run.provider_version,
            "model_name": run.model_name,
            "config_hash": run.config_hash,
            "status": run.status,
            "raw_summary": parse_evidence_json(run.raw_summary),
            "error": run.error,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "scores": [
                {
                    "id": score.id,
                    "question_answer_id": score.question_answer_id,
                    "question_id": score.question_id,
                    "question": score.question.question_text if score.question else None,
                    "score": score.score,
                    "feedback_en": score.feedback_en,
                    "feedback_ar": score.feedback_ar,
                    "evidence": parse_evidence_json(score.evidence_json),
                    "created_at": score.created_at,
                }
                for score in scores
            ],
        })

    return audit_runs


def generate_interview_evaluation_analytics(interview_id: int, db: Session) -> Dict[str, object]:
    responses = (
        db.query(CandidateResponse)
        .filter(CandidateResponse.interview_id == interview_id, CandidateResponse.status == "completed")
        .all()
    )
    response_ids = [response.id for response in responses]
    runs = db.query(EvaluationRun).filter(EvaluationRun.response_id.in_(response_ids)).all() if response_ids else []

    provider_counts = {}
    fallback_count = 0
    for run in runs:
        provider_counts[run.provider] = provider_counts.get(run.provider, 0) + 1

    latest_scores = []
    for response in responses:
        latest_run = (
            db.query(EvaluationRun)
            .filter(EvaluationRun.response_id == response.id, EvaluationRun.status == "completed")
            .order_by(EvaluationRun.completed_at.desc(), EvaluationRun.id.desc())
            .first()
        )
        if latest_run and latest_run.raw_summary:
            summary = parse_evidence_json(latest_run.raw_summary)
            if summary.get("total_score") is not None:
                latest_scores.append(float(summary["total_score"]))
        latest_scores.extend([] if latest_run else [])

        if latest_run:
            scores = db.query(EvaluationScore).filter(EvaluationScore.evaluation_run_id == latest_run.id).all()
            for score in scores:
                evidence = parse_evidence_json(score.evidence_json)
                if evidence.get("provider_fallback_from"):
                    fallback_count += 1

    return {
        "interview_id": interview_id,
        "completed_responses": len(responses),
        "total_evaluation_runs": len(runs),
        "queued_runs": sum(1 for run in runs if run.status == "queued"),
        "running_runs": sum(1 for run in runs if run.status == "running"),
        "completed_runs": sum(1 for run in runs if run.status == "completed"),
        "failed_runs": sum(1 for run in runs if run.status == "failed"),
        "average_latest_score": sum(latest_scores) / len(latest_scores) if latest_scores else 0.0,
        "fallback_count": fallback_count,
        "provider_counts": provider_counts,
        "generated_at": datetime.utcnow(),
    }


def generate_candidate_profile(candidate_email: str, db: Session) -> Dict[str, object]:
    """Candidate database / CRM profile: all history across interviews."""
    from app.models import Interview

    responses = (
        db.query(CandidateResponse)
        .filter(CandidateResponse.candidate_email == candidate_email)
        .order_by(CandidateResponse.created_at.desc())
        .all()
    )

    history = []
    passed_count = 0
    for response in responses:
        interview = db.query(Interview).filter(Interview.id == response.interview_id).first()
        history.append({
            "response_id": response.id,
            "interview_id": response.interview_id,
            "interview_title": interview.title if interview else "Unknown",
            "status": response.status,
            "total_score": response.total_score,
            "passed": response.passed,
            "reviewer_decision": response.reviewer_decision.value if response.reviewer_decision else "pending",
            "dominant_emotion": response.dominant_emotion,
            "completed_at": response.completed_at,
            "created_at": response.created_at,
        })
        if response.passed:
            passed_count += 1

    completed = [h for h in history if h["status"] == "completed"]
    scores = [h["total_score"] for h in completed if h["total_score"] is not None]
    candidate_name = next((r.candidate_name for r in responses if r.candidate_email == candidate_email), None)

    return {
        "candidate_email": candidate_email,
        "candidate_name": candidate_name,
        "total_responses": len(history),
        "completed_responses": len(completed),
        "passed_count": passed_count,
        "average_score": sum(scores) / len(scores) if scores else None,
        "best_score": max(scores) if scores else None,
        "history": history,
        "generated_at": datetime.utcnow(),
    }


def generate_interview_question_analytics(interview_id: int, db: Session) -> Dict[str, object]:
    """Per-question analytics: difficulty and discrimination."""
    from app.models import CandidateResponse, QuestionAnswer, InterviewQuestion

    questions = (
        db.query(InterviewQuestion)
        .filter(InterviewQuestion.interview_id == interview_id)
        .order_by(InterviewQuestion.order_index, InterviewQuestion.id)
        .all()
    )
    responses = (
        db.query(CandidateResponse)
        .filter(CandidateResponse.interview_id == interview_id, CandidateResponse.status == "completed")
        .all()
    )
    response_ids = [response.id for response in responses]

    questions_analysis = []
    for question in questions:
        answers = (
            db.query(QuestionAnswer)
            .filter(
                QuestionAnswer.question_id == question.id,
                QuestionAnswer.response_id.in_(response_ids),
            )
            .all()
        ) if response_ids else []

        scores = [a.score for a in answers if a.score is not None]
        avg = sum(scores) / len(scores) if scores else None

        # Discrimination: correlation between this question's score and the
        # candidate's overall total score (point-biserial style).
        discrimination = None
        if len(scores) >= 2:
            total_by_response = {r.id: (r.total_score or 0.0) for r in responses}
            q_scores = []
            t_scores = []
            for a in answers:
                if a.score is not None and a.response_id in total_by_response:
                    q_scores.append(a.score)
                    t_scores.append(total_by_response[a.response_id])
            if q_scores and len(set(t_scores)) > 1:
                q_mean = sum(q_scores) / len(q_scores)
                t_mean = sum(t_scores) / len(t_scores)
                num = sum((q - q_mean) * (t - t_mean) for q, t in zip(q_scores, t_scores))
                denom = (sum((q - q_mean) ** 2 for q in q_scores) ** 0.5) * (sum((t - t_mean) ** 2 for t in t_scores) ** 0.5)
                if denom:
                    discrimination = round(num / denom, 3)

        questions_analysis.append({
            "question_id": question.id,
            "question": question.question_text,
            "expected_answer": question.expected_answer,
            "response_count": len(answers),
            "average_score": round(avg, 2) if avg is not None else None,
            "min_score": min(scores) if scores else None,
            "max_score": max(scores) if scores else None,
            "difficulty": "easy" if (avg is not None and avg >= 75) else "medium" if (avg is not None and avg >= 50) else "hard" if avg is not None else "unknown",
            "discrimination": discrimination,
        })

    return {
        "interview_id": interview_id,
        "question_count": len(questions),
        "response_count": len(responses),
        "questions": questions_analysis,
        "generated_at": datetime.utcnow(),
    }


def detect_answer_plagiarism(interview_id: int, db: Session, threshold: float = 0.8) -> Dict[str, object]:
    """Compare candidate answers against each other per question to detect
    near-duplicate submissions (cheating)."""
    from app.models import CandidateResponse, QuestionAnswer, InterviewQuestion

    questions = (
        db.query(InterviewQuestion)
        .filter(InterviewQuestion.interview_id == interview_id)
        .all()
    )
    responses = (
        db.query(CandidateResponse)
        .filter(CandidateResponse.interview_id == interview_id, CandidateResponse.status == "completed")
        .all()
    )
    response_ids = [response.id for response in responses]

    flags = []
    for question in questions:
        answers = (
            db.query(QuestionAnswer)
            .filter(
                QuestionAnswer.question_id == question.id,
                QuestionAnswer.response_id.in_(response_ids),
            )
            .all()
        ) if response_ids else []

        text_by_response = {}
        for a in answers:
            text = (a.answer_text or a.transcript or "").strip()
            if text:
                text_by_response[a.response_id] = (a.id, text)

        items = list(text_by_response.items())
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                r1, (a1_id, t1) = items[i]
                r2, (a2_id, t2) = items[j]
                similarity = text_similarity(t1, t2)
                if similarity >= threshold:
                    name1 = next((r.candidate_name for r in responses if r.id == r1), str(r1))
                    name2 = next((r.candidate_name for r in responses if r.id == r2), str(r2))
                    flags.append({
                        "question_id": question.id,
                        "question": question.question_text,
                        "response_a_id": r1,
                        "response_a_name": name1,
                        "response_b_id": r2,
                        "response_b_name": name2,
                        "similarity": round(similarity, 3),
                    })

    return {
        "interview_id": interview_id,
        "threshold": threshold,
        "flagged_pairs": flags,
        "flag_count": len(flags),
        "generated_at": datetime.utcnow(),
    }


def text_similarity(text_a: str, text_b: str) -> float:
    """Jaccard-style similarity over normalized tokens."""
    set_a = set(normalize_tokens(text_a))
    set_b = set(normalize_tokens(text_b))
    if not set_a and not set_b:
        return 1.0 if text_a == text_b else 0.0
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


async def get_evaluation_health() -> Dict[str, object]:
    provider = get_evaluation_provider()
    health = {
        "provider": provider.name,
        "provider_version": getattr(provider, "version", None),
        "prompt_version": settings.EVALUATION_PROMPT_VERSION,
        "config_hash": get_evaluation_config_hash(provider),
        "model_name": settings.LOCAL_LLM_MODEL if provider.name == "local_vllm" else None,
        "base_url": settings.LOCAL_LLM_BASE_URL if provider.name == "local_vllm" else None,
        "healthy": True,
        "status": "available",
        "fallback_provider": getattr(getattr(provider, "fallback_provider", None), "name", None),
        "last_error": None,
        "checked_at": datetime.utcnow(),
    }

    if provider.name != "local_vllm":
        return health

    try:
        async with httpx.AsyncClient(timeout=min(settings.LOCAL_LLM_TIMEOUT_SECONDS, 2.0)) as client:
            response = await client.get(f"{settings.LOCAL_LLM_BASE_URL.rstrip('/')}/models")
            response.raise_for_status()
        health["status"] = "local_vllm_available"
    except Exception as exc:
        health["healthy"] = False
        health["status"] = "local_vllm_unavailable_using_fallback"
        health["last_error"] = str(exc)

    return health


def get_ai_disclosure() -> Dict[str, object]:
    provider = get_evaluation_provider()
    from app.services.transcription_service import get_transcription_provider as get_trans_provider
    trans_provider = get_trans_provider()

    return {
        "evaluation": {
            "provider": provider.name,
            "provider_version": getattr(provider, "version", None),
            "purpose": "Automated scoring of candidate answers against rubric criteria and expected answers.",
            "model": settings.LOCAL_LLM_MODEL if provider.name == "local_vllm" else "deterministic (no ML model)",
            "human_review_available": True,
            "human_review_description": "Employers can override AI scores, set reviewer decisions (shortlist/reject/hire), and add manual scorecards per candidate.",
        },
        "transcription": {
            "provider": trans_provider.name,
            "provider_version": getattr(trans_provider, "version", None),
            "purpose": "Conversion of recorded audio responses to text for evaluation and review.",
            "model": "faster-whisper (multilingual, Arabic + English)" if trans_provider.name == "whisper" else "simulated (fake provider)",
        },
        "emotion_analysis": {
            "enabled": get_emotion_provider_name() != "disabled",
            "provider": get_emotion_provider_name(),
            "purpose": "Facial expression analysis of recorded interview video using DeepFace (open source). Emotion confidence may contribute a small configurable weight to the overall score.",
            "scoring_impact": "weighted" if settings.SCORING_EMOTION_WEIGHT > 0 else "none",
            "weight": settings.SCORING_EMOTION_WEIGHT,
        },
        "quality_analysis": {
            "enabled": True,
            "purpose": "Voice, background, face visibility, and lighting metrics from client-side device checks.",
            "scoring_impact": "weighted" if settings.SCORING_QUALITY_WEIGHT > 0 else "none",
            "weight": settings.SCORING_QUALITY_WEIGHT,
        },
        "disclosure": (
            "SRIS uses automated evaluation tools to assist employers in reviewing candidate responses. "
            "All AI-generated scores and feedback are subject to human review. "
            "Final hiring decisions are made by human reviewers. "
            "Emotion confidence and device-quality metrics may contribute a small, configurable "
            "weight to the overall score; these weights are disclosed to candidates and employers."

        ),
        "last_updated": datetime.utcnow(),
    }
