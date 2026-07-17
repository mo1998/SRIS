"""
User management routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import TeamMembership, TeamRole, User
from app.schemas import OrganizationResponse, TeamMembershipCreate, TeamMembershipResponse, UserResponse
from app.api.auth import get_current_user, require_role, UserRole

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
