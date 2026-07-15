"""
Authentication Router
Manages user registration, login, logout, and JWT token issuance.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import datetime

from database import get_db
from models.models import User, Role, Session as UserSession
from schemas.schemas import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from auth.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
def register_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
):
    """
    Public registration endpoint.
    Creates a new user account with a selected role.
    """

    existing_user = (
        db.query(User)
        .filter(User.username == payload.username)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username is already registered.",
        )

    role = (
        db.query(Role)
        .filter(Role.id == payload.role_id)
        .first()
    )

    if not role:
        raise HTTPException(
            status_code=404,
            detail="Selected role is invalid.",
        )

    new_user = User(
        username=payload.username,
        hashed_password=get_password_hash(payload.password),
        role_id=payload.role_id,
        is_active=True,
        is_locked=False,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Verifies credentials and generates JWT tokens.
    """

    user = (
        db.query(User)
        .filter(User.username == payload.username)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    if user.is_locked:
        raise HTTPException(
            status_code=403,
            detail="Account is administratively locked",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Account is deactivated",
        )

    if not verify_password(
        payload.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    access_token = create_access_token(
        subject=user.username,
        role=user.role.name,
    )

    refresh_token = create_refresh_token(
        subject=user.username,
        role=user.role.name,
    )

    session = UserSession(
        user_id=user.id,
        token=access_token,
        expires_at=datetime.datetime.utcnow()
        + datetime.timedelta(hours=1),
    )

    db.add(session)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout")
def logout(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Invalidates the current session token.
    """

    session = (
        db.query(UserSession)
        .filter(UserSession.token == token)
        .first()
    )

    if session:
        db.delete(session)
        db.commit()

    return {
        "message": "Session successfully terminated"
    }