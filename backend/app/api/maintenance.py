"""
Maintenance endpoints for manually triggering scheduled jobs.
"""

from fastapi import APIRouter, Depends

from app.api.auth import get_current_user, require_role
from app.models import User, UserRole
from app.services.maintenance_service import run_maintenance

router = APIRouter()


@router.post("/run")
async def trigger_maintenance(
    current_user: User = Depends(require_role(UserRole.EMPLOYER)),
):
    """Manually run invitation expiry sweep and reminder jobs."""
    return run_maintenance()
