"""
Evaluation service - AI-powered answer scoring and candidate evaluation
"""

import json
from typing import List, Dict
from sqlalchemy.orm import Session
from datetime import datetime

from app.models import CandidateResponse, QuestionAnswer, InterviewQuestion, Interview
from app.config import settings


async def evaluate_answer_similarity(answer_text: str, expected_answer: str) -> float:
    """
    Evaluate answer similarity using OpenAI or fallback to basic string matching
    Returns a score between 0 and 100
    """
    if not answer_text or not expected_answer:
        return 0.0
    
    if settings.OPENAI_API_KEY:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an interview evaluator. Compare the candidate's answer to the expected answer.
                        Consider: key points covered, accuracy, completeness, and clarity.
                        Return ONLY a JSON object with "score" (0-100) and "feedback" (brief explanation)."""
                    },
                    {
                        "role": "user",
                        "content": f"""Expected Answer: {expected_answer}
                        
                        Candidate's Answer: {answer_text}
                        
                        Evaluate the candidate's answer."""
                    }
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            result = json.loads(response.choices[0].message.content)
            return min(100.0, max(0.0, float(result.get("score", 50.0)))), result.get("feedback", "")
            
        except Exception as e:
            print(f"OpenAI evaluation failed: {e}")
    
    # Fallback: Basic keyword matching
    expected_words = set(expected_answer.lower().split())
    answer_words = set(answer_text.lower().split())
    common_words = expected_words.intersection(answer_words)
    
    if len(expected_words) == 0:
        return 50.0, "No expected answer provided"
    
    similarity = (len(common_words) / len(expected_words)) * 100
    feedback = f"Matched {len(common_words)} out of {len(expected_words)} key concepts"
    
    return min(100.0, similarity), feedback


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
    
    total_score = 0.0
    total_weight = 0.0
    
    # Evaluate each answer
    for answer in answers:
        question = db.query(InterviewQuestion).filter(InterviewQuestion.id == answer.question_id).first()
        if not question:
            continue
        
        # Score the answer
        if answer.answer_text and question.expected_answer:
            score, feedback = await evaluate_answer_similarity(answer.answer_text, question.expected_answer)
            answer.score = score
            answer.feedback = feedback
        else:
            answer.score = 0.0
            answer.feedback = "No answer provided"
        
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
    
    db.commit()
    
    # Send completion email
    if response.candidate_email:
        from app.services.email_service import send_completion_email
        interview_title = interview.title if interview else "Interview"
        await send_completion_email(
            to_email=response.candidate_email,
            candidate_name=response.candidate_name,
            interview_title=interview_title,
            score=response.total_score or 0.0,
            passed=response.passed or False
        )


def generate_candidate_report(response_id: int, db: Session) -> Dict:
    """Generate detailed report for a candidate"""
    response = db.query(CandidateResponse).filter(CandidateResponse.id == response_id).first()
    if not response:
        return {}
    
    interview = db.query(Interview).filter(Interview.id == response.interview_id).first()
    answers = db.query(QuestionAnswer).filter(QuestionAnswer.response_id == response_id).all()
    
    answer_details = []
    for answer in answers:
        question = db.query(InterviewQuestion).filter(InterviewQuestion.id == answer.question_id).first()
        answer_details.append({
            "question": question.question_text if question else "Unknown",
            "expected_answer": question.expected_answer if question else "",
            "candidate_answer": answer.answer_text,
            "score": answer.score,
            "feedback": answer.feedback,
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
        "started_at": response.started_at,
        "completed_at": response.completed_at
    }


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
