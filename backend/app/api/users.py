"""
User management routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User
from app.schemas import UserResponse
from app.api.auth import get_current_user, require_role, UserRole

router = APIRouter()


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
