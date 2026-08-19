"""
User management routes
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import TeamMembership, TeamRole, User
from app.schemas import OrganizationProvidersResponse, OrganizationResponse, OrganizationSettingsUpdate, PasswordChange, TeamMemberResponse, TeamMembershipCreate, TeamMembershipResponse, UserResponse, UserUpdate
from app.api.auth import get_current_user, get_password_hash, require_role, UserRole, verify_password
from app.services.audit_service import create_audit_log

router = APIRouter()


def get_primary_membership(user: User, db: Session) -> TeamMembership:
    membership = (
        db.query(TeamMembership)
        .filter(TeamMembership.user_id == user.id)
        .order_by(TeamMembership.created_at.asc())
        .first()
    )

    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    return membership


def require_membership_admin(membership: TeamMembership) -> None:
    if membership.role not in {TeamRole.OWNER, TeamRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient organization permissions")


def validate_assignable_role(actor_role: TeamRole, requested_role: TeamRole) -> None:
    if actor_role != TeamRole.OWNER and requested_role in {TeamRole.OWNER, TeamRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only organization owners can assign owner or admin roles")


@router.get("/me/organization", response_model=OrganizationResponse)
async def get_my_organization(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current user's primary organization"""
    membership = (
        db.query(TeamMembership)
        .filter(TeamMembership.user_id == current_user.id)
        .order_by(TeamMembership.created_at.asc())
        .first()
    )

    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    return membership.organization


@router.get("/me/organization/providers", response_model=OrganizationProvidersResponse)
async def get_organization_evaluation_providers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List evaluation providers the organization can select and its current
    selection. Any organization member can read; changes require owner/admin."""
    membership = get_primary_membership(current_user, db)

    from app.services.evaluation_service import get_available_providers, get_organization_provider_config, organization_llm_configured

    return {
        "organization_id": membership.organization_id,
        "selected": membership.organization.evaluation_provider,
        "configured": organization_llm_configured(get_organization_provider_config(db, membership.organization_id)),
        "role": membership.role.value,
        "providers": get_available_providers(),
    }


@router.patch("/me/organization/settings", response_model=OrganizationResponse)
async def update_organization_evaluation_settings(
    settings_update: OrganizationSettingsUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Replace the organization's evaluation provider settings (owner/admin only).

    The payload is a full replacement: omitted or empty fields clear the
    setting. The provider is configured entirely from the UI — no .env or
    deployment changes required. When a working provider is configured, any
    held (pending) evaluation runs are dispatched in the background.
    """
    membership = get_primary_membership(current_user, db)
    require_membership_admin(membership)

    org = membership.organization
    changed = {
        "evaluation_provider": settings_update.evaluation_provider,
        "evaluation_model": settings_update.evaluation_model,
        "evaluation_base_url": settings_update.evaluation_base_url,
        "evaluation_api_key_set": bool(settings_update.evaluation_api_key),
    }
    org.evaluation_provider = settings_update.evaluation_provider
    org.evaluation_model = settings_update.evaluation_model
    org.evaluation_base_url = settings_update.evaluation_base_url
    org.evaluation_api_key = settings_update.evaluation_api_key

    create_audit_log(
        db,
        actor=current_user,
        action="organization.evaluation_settings_updated",
        target_type="organization",
        target_id=org.id,
        organization_id=org.id,
        details={k: ("***" if (isinstance(v, str) and "api_key" in k) else v) for k, v in changed.items()},
    )
    db.commit()
    db.refresh(org)

    from app.services.evaluation_service import redispatch_pending_evaluations

    await redispatch_pending_evaluations(db, org.id, background_tasks)
    return org


@router.get("/me/organization/members", response_model=List[TeamMemberResponse])
async def list_organization_members(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List members of the current user's primary organization (owner/admin only)"""
    current_membership = get_primary_membership(current_user, db)
    require_membership_admin(current_membership)

    memberships = (
        db.query(TeamMembership)
        .filter(TeamMembership.organization_id == current_membership.organization_id)
        .order_by(TeamMembership.created_at.asc())
        .all()
    )
    return [
        {
            "user_id": membership.user_id,
            "email": membership.user.email,
            "full_name": membership.user.full_name,
            "role": membership.role.value,
            "created_at": membership.created_at,
        }
        for membership in memberships
    ]


@router.get("/me/memberships", response_model=List[TeamMembershipResponse])
async def get_my_memberships(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List organization memberships for the current user"""
    return (
        db.query(TeamMembership)
        .filter(TeamMembership.user_id == current_user.id)
        .order_by(TeamMembership.created_at.asc())
        .all()
    )


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the current user's profile"""
    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name
    if user_data.phone is not None:
        current_user.phone = user_data.phone

    db.commit()
    db.refresh(current_user)

    return current_user


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_current_user_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change the current user's password"""
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    current_user.hashed_password = get_password_hash(password_data.new_password)
    current_user.token_version = (current_user.token_version or 0) + 1
    create_audit_log(
        db,
        actor=current_user,
        action="user.password_changed",
        target_type="user",
        target_id=current_user.id,
        details={"email": current_user.email},
    )
    db.commit()


@router.post("/me/memberships", response_model=TeamMembershipResponse, status_code=status.HTTP_201_CREATED)
async def add_organization_member(
    membership_data: TeamMembershipCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add an existing user to the current user's primary organization"""
    current_membership = get_primary_membership(current_user, db)
    require_membership_admin(current_membership)

    requested_role = TeamRole(membership_data.role.value)
    validate_assignable_role(current_membership.role, requested_role)

    target_user = db.query(User).filter(User.email == membership_data.email).first()
    if not target_user or not target_user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing_membership = (
        db.query(TeamMembership)
        .filter(
            TeamMembership.organization_id == current_membership.organization_id,
            TeamMembership.user_id == target_user.id,
        )
        .first()
    )
    if existing_membership:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already a member of this organization")

    new_membership = TeamMembership(
        organization_id=current_membership.organization_id,
        user_id=target_user.id,
        role=requested_role,
    )
    db.add(new_membership)
    create_audit_log(
        db,
        actor=current_user,
        action="team_membership.created",
        target_type="team_membership",
        organization_id=current_membership.organization_id,
        details={"target_user_id": target_user.id, "target_email": target_user.email, "role": requested_role.value},
    )
    db.commit()
    db.refresh(new_membership)

    return new_membership


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """List all users (admin only)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user by ID"""
    # Users can only view their own profile unless they're admin
    if current_user.role.value != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    full_name: str = None,
    phone: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    # Users can only update their own profile unless they're admin
    if current_user.role.value != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if full_name:
        user.full_name = full_name
    if phone:
        user.phone = phone
    
    db.commit()
    db.refresh(user)
    
    return user
