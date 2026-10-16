"""
Authentication routes — register, login, profile, logout.
Works with Supabase Auth when configured, falls back to local JWT.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from jose import jwt
import bcrypt

from app.core.config import get_settings
from app.core.auth import get_current_user
from app.db.database import get_db
from app.db.models import UserProfile, Organization, UserRole

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode("utf-8")[:72]
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
    except Exception:
        return False


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    organization_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None


def _create_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user with a local workspace."""
    # Check if email already used
    existing = db.query(UserProfile).filter(UserProfile.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    # Create organization
    org_name = req.organization_name or f"{req.full_name}'s Workspace"
    slug = req.email.split("@")[0].replace(".", "-").lower() + "-ws"
    # Ensure slug uniqueness
    base_slug = slug
    count = 1
    while db.query(Organization).filter(Organization.slug == slug).first():
        slug = f"{base_slug}-{count}"
        count += 1

    org = Organization(name=org_name, slug=slug)
    db.add(org)
    db.flush()

    # Create user
    user_id = f"local-{req.email.replace('@', '-').replace('.', '-')}"
    hashed = hash_password(req.password)
    user = UserProfile(
        supabase_user_id=user_id,
        organization_id=org.id,
        email=req.email,
        full_name=req.full_name,
        hashed_password=hashed,
        role=UserRole.ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = _create_token(user_id, req.email)
    return TokenResponse(
        access_token=token,
        user=_user_dict(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password."""
    user = db.query(UserProfile).filter(UserProfile.email == req.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if user.hashed_password:
        if not verify_password(req.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive.")

    token = _create_token(user.supabase_user_id, user.email)
    return TokenResponse(
        access_token=token,
        user=_user_dict(user),
    )


@router.get("/me")
def get_me(current_user: UserProfile = Depends(get_current_user)):
    """Get current user profile."""
    return _user_dict(current_user)


@router.patch("/me")
def update_profile(
    req: ProfileUpdate,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user profile."""
    if req.full_name:
        current_user.full_name = req.full_name
    db.commit()
    db.refresh(current_user)
    return _user_dict(current_user)


def _user_dict(user: UserProfile) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value if user.role else "consultant",
        "organization_id": user.organization_id,
        "is_active": user.is_active,
    }
