"""
Reviewer decision and scorecard routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import User, CandidateResponse, ReviewerScorecard, TeamMembership, TeamRole, UserRole, ReviewerDecision
from app.schemas import ReviewerDecisionUpdate, ReviewerScorecardCreate, ReviewerScorecardResponse
from app.api.auth import get_current_user
from app.services.audit_service import create_audit_log

router = APIRouter()


def require_decision_management(response: CandidateResponse, user: User, db: Session) -> None:
    interview = response.interview
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    if user.role == UserRole.ADMIN:
        return

    membership = (
        db.query(TeamMembership)
        .filter(
            TeamMembership.user_id == user.id,
            TeamMembership.organization_id == interview.organization_id,
        )
        .first()
    )
    if not membership or membership.role not in {TeamRole.OWNER, TeamRole.ADMIN, TeamRole.REVIEWER, TeamRole.RECRUITER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to manage decisions")


@router.put("/{response_id}/decision", response_model=dict)
async def set_reviewer_decision(
    response_id: int,
    decision_data: ReviewerDecisionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set the reviewer decision for a candidate response."""
    candidate_response = db.query(CandidateResponse).filter(CandidateResponse.id == response_id).first()
    if not candidate_response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")

    require_decision_management(candidate_response, current_user, db)

    old_decision = candidate_response.reviewer_decision.value if candidate_response.reviewer_decision else "pending"
    new_decision = decision_data.decision.value

    candidate_response.reviewer_decision = ReviewerDecision(decision_data.decision.value)
    candidate_response.reviewer_decision_at = datetime.utcnow()
    candidate_response.reviewer_decision_by = current_user.id

    create_audit_log(
        db,
        actor=current_user,
        action="reviewer.decision_set",
        target_type="candidate_response",
        target_id=candidate_response.id,
        organization_id=candidate_response.interview.organization_id if candidate_response.interview else None,
        details={
            "interview_id": candidate_response.interview_id,
            "old_decision": old_decision,
            "new_decision": new_decision,
        },
    )

    db.commit()

    return {
        "response_id": response_id,
        "reviewer_decision": new_decision,
        "set_by": current_user.id,
        "set_at": candidate_response.reviewer_decision_at,
    }


@router.post("/{response_id}/scorecard", response_model=ReviewerScorecardResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_scorecard(
    response_id: int,
    scorecard_data: ReviewerScorecardCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update a reviewer scorecard for a candidate response."""
    candidate_response = db.query(CandidateResponse).filter(CandidateResponse.id == response_id).first()
    if not candidate_response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")

    require_decision_management(candidate_response, current_user, db)

    existing = db.query(ReviewerScorecard).filter(ReviewerScorecard.response_id == response_id).first()
    if existing:
        existing.reviewer_id = current_user.id
        existing.overall_score = scorecard_data.overall_score
        existing.strengths = scorecard_data.strengths
        existing.weaknesses = scorecard_data.weaknesses
        existing.overall_comment = scorecard_data.overall_comment
        existing.updated_at = datetime.utcnow()
        scorecard = existing
    else:
        scorecard = ReviewerScorecard(
            response_id=response_id,
            reviewer_id=current_user.id,
            overall_score=scorecard_data.overall_score,
            strengths=scorecard_data.strengths,
            weaknesses=scorecard_data.weaknesses,
            overall_comment=scorecard_data.overall_comment,
        )
        db.add(scorecard)

    create_audit_log(
        db,
        actor=current_user,
        action="reviewer.scorecard_saved",
        target_type="candidate_response",
        target_id=candidate_response.id,
        organization_id=candidate_response.interview.organization_id if candidate_response.interview else None,
        details={"interview_id": candidate_response.interview_id, "has_existing": existing is not None},
    )

    db.commit()
    db.refresh(scorecard)
    return scorecard


@router.get("/{response_id}/scorecard", response_model=ReviewerScorecardResponse)
async def get_scorecard(
    response_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the reviewer scorecard for a candidate response."""
    candidate_response = db.query(CandidateResponse).filter(CandidateResponse.id == response_id).first()
    if not candidate_response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")

    require_decision_management(candidate_response, current_user, db)

    scorecard = db.query(ReviewerScorecard).filter(ReviewerScorecard.response_id == response_id).first()
    if not scorecard:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scorecard not found")

    return scorecard
