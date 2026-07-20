"""
Evaluation service - deterministic answer scoring and candidate evaluation
"""

from dataclasses import dataclass
import json
import re
import hashlib
from typing import Dict, List, Protocol
import httpx
from sqlalchemy.orm import Session
from datetime import datetime

from app.config import settings
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

    async def evaluate_answer(self, answer_text: str, expected_answer: str) -> EvaluationResult:
        ...


class BaselineEvaluationProvider:
    name = "deterministic_baseline"
    version = "1.0.0"

    async def evaluate_answer(self, answer_text: str, expected_answer: str) -> EvaluationResult:
        answer_tokens = normalize_tokens(answer_text)
        expected_tokens = normalize_tokens(expected_answer)

        if not answer_tokens:
            return EvaluationResult(
                score=0.0,
                feedback="No answer provided. Evidence: empty candidate response.",
                evidence={"matched_keywords": [], "missing_keywords": expected_tokens, "keyword_coverage": 0.0, "length_score": 0.0},
            )

        if not expected_tokens:
            length_score = score_answer_length(answer_tokens, minimum_tokens=8)
            return EvaluationResult(
                score=round(length_score * 0.7, 1),
                feedback="No expected answer was configured; scored using answer completeness only.",
                evidence={"matched_keywords": [], "missing_keywords": [], "keyword_coverage": None, "length_score": round(length_score, 1)},
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
            },
        )


class LocalVLLMEvaluationProvider:
    name = "local_vllm"
    version = "1.0.0"

    def __init__(self, fallback_provider: EvaluationProvider):
        self.fallback_provider = fallback_provider

    async def evaluate_answer(self, answer_text: str, expected_answer: str) -> EvaluationResult:
        if not answer_text.strip():
            return await self.fallback_provider.evaluate_answer(answer_text, expected_answer)

        try:
            payload = {
                "model": settings.LOCAL_LLM_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "/no_think You evaluate structured interview answers. Do not show reasoning. "
                            "Return valid compact JSON only with keys: score, feedback_en, feedback_ar, "
                            "matched_criteria, missing_criteria, evidence. Score must be 0-100."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Expected answer: {expected_answer}\nCandidate answer: {answer_text}",
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
                "matched_criteria": parsed.get("matched_criteria", []),
                "missing_criteria": parsed.get("missing_criteria", []),
                "evidence": parsed.get("evidence", ""),
            }
            return EvaluationResult(
                score=score,
                feedback=f"{self.name} {settings.LOCAL_LLM_MODEL}: {feedback_en} Arabic feedback: {feedback_ar}",
                evidence=evidence,
            )
        except Exception as exc:
            fallback = await self.fallback_provider.evaluate_answer(answer_text, expected_answer)
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


baseline_provider = BaselineEvaluationProvider()
local_vllm_provider = LocalVLLMEvaluationProvider(baseline_provider)


def get_evaluation_provider() -> EvaluationProvider:
    if settings.EVALUATION_PROVIDER == "deterministic_baseline":
        return baseline_provider
    return local_vllm_provider


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
        
        # Positive emotions that indicate confidence
        positive_emotions = ["happy", "neutral", "surprise"]
        negative_emotions = ["fear", "disgust", "sad"]
        
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
        print(f"Error calculating emotion score: {e}")
        return 50.0


async def evaluate_candidate_response(response_id: int, db: Session):
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
    evaluation_run = EvaluationRun(
        response_id=response.id,
        provider=provider.name,
        provider_version=getattr(provider, "version", None),
        model_name=settings.LOCAL_LLM_MODEL if provider.name == "local_vllm" else None,
        config_hash=get_evaluation_config_hash(provider),
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(evaluation_run)
    db.flush()
    
    total_score = 0.0
    total_weight = 0.0

    try:
        # Evaluate each answer
        for answer in answers:
            question = db.query(InterviewQuestion).filter(InterviewQuestion.id == answer.question_id).first()
            if not question:
                continue

            # Score the answer
            if answer.answer_text and question.expected_answer:
                result = await provider.evaluate_answer(answer.answer_text, question.expected_answer)
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

            # Calculate emotion during this answer
            if response.emotion_timeline:
                try:
                    timeline = json.loads(response.emotion_timeline)
                    if timeline:
                        # Get most common emotion during answer time
                        emotions = [r.get("emotion", "neutral") for r in timeline]
                        answer.emotion_during_answer = max(set(emotions), key=emotions.count)
                except:
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
    if response.emotion_timeline:
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
        try:
            await send_completion_email(
                to_email=response.candidate_email,
                candidate_name=response.candidate_name,
                interview_title=interview_title,
                score=response.total_score or 0.0,
                passed=response.passed or False
            )
        except Exception as exc:
            print(f"Completion email failed: {exc}")


def get_evaluation_config_hash(provider: EvaluationProvider) -> str:
    payload = {
        "provider": provider.name,
        "provider_version": getattr(provider, "version", None),
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
            "score": answer.score,
            "feedback": answer.feedback,
            "feedback_en": evaluation_score.feedback_en if evaluation_score else None,
            "feedback_ar": evaluation_score.feedback_ar if evaluation_score else None,
            "evidence": parse_evidence_json(evaluation_score.evidence_json) if evaluation_score else None,
            "emotion": answer.emotion_during_answer
        })
    
    return {
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
        candidates.append({
            "rank": len(candidates) + 1,
            "name": response.candidate_name,
            "email": response.candidate_email,
            "total_score": response.total_score or 0.0,
            "passed": response.passed or False,
            "confidence_score": response.confidence_score or 50.0,
            "voice_quality": response.voice_quality_score or 0.0,
            "face_visibility": response.face_visibility_score or 0.0,
            "dominant_emotion": response.dominant_emotion or "neutral",
            "completed_at": response.completed_at
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
