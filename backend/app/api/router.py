"""
API Router configuration
"""

from fastapi import APIRouter
from app.api import audit, auth, users, interviews, invitations, responses, reports

api_router = APIRouter()

# Include routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(interviews.router, prefix="/interviews", tags=["Interviews"])
api_router.include_router(invitations.router, prefix="/invitations", tags=["Invitations"])
api_router.include_router(responses.router, prefix="/responses", tags=["Candidate Responses"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(audit.router, prefix="/audit-logs", tags=["Audit Logs"])
