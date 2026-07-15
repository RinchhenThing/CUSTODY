"""
User Management Router
Exposes granular administrative operations over console operators and auditors.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session
from database import get_db
from models.models import User, Role
from schemas.schemas import UserResponse, UserCreate, UserUpdate, PasswordResetRequest
from auth.security import get_password_hash
from dependencies import require_permission, get_current_user

router = APIRouter(prefix="/users", tags=["User Management"])

@router.get("", response_model=List[UserResponse], dependencies=[require_permission("users.view")])
def get_all_users(db: Session = Depends(get_db)):
    """Retrieves all registered terminal operators and system profiles."""
    return db.query(User).all()

@router.post("", response_model=UserResponse, dependencies=[require_permission("users.create")])
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    """Registers a new console profile with custom-assigned operational roles."""
    existing_user = db.query(User).filter(User.username == payload.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
        
    role_check = db.query(Role).filter(Role.id == payload.role_id).first()
    if not role_check:
        raise HTTPException(status_code=404, detail="Assigned Role ID does not exist")
        
    new_user = User(
        username=payload.username,
        hashed_password=get_password_hash(payload.password),
        role_id=payload.role_id,
        is_active=payload.is_active,
        is_locked=payload.is_locked
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.patch("/{user_id}", response_model=UserResponse, dependencies=[require_permission("users.edit")])
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    """Updates operational state toggles or role properties for a target profile."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User target not found")
        
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
        
    db.commit()
    db.refresh(user)
    return user

@router.post("/{user_id}/lock", dependencies=[require_permission("users.lock")])
def lock_user(user_id: int, db: Session = Depends(get_db)):
    """Immediately locks out an active profile session to block security threats."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User target not found")
    user.is_locked = True
    db.commit()
    return {"message": f"User account '{user.username}' has been locked out"}

@router.post("/{user_id}/unlock", dependencies=[require_permission("users.lock")])
def unlock_user(user_id: int, db: Session = Depends(get_db)):
    """Restores programmatic access for an administratively isolated profile."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User target not found")
    user.is_locked = False
    db.commit()
    return {"message": f"User account '{user.username}' successfully unlocked"}

@router.post("/{user_id}/reset-password", dependencies=[require_permission("users.edit")])
def reset_password(user_id: int, payload: PasswordResetRequest, db: Session = Depends(get_db)):
    """Overwrites password hashes directly following enterprise password updates."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User target not found")
    user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    return {"message": f"Password reset for '{user.username}' executed successfully"}