from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.api.deps import DbSession
from app.core.auth import create_access_token, hash_password, verify_password
from app.models.invitation import Invitation
from app.models.user import User

router = APIRouter()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_admin: bool


class RegisterRequest(BaseModel):
    username: str
    password: str
    invite_token: str


@router.post("/login", response_model=TokenResponse)
def login(
    db: DbSession,
    form: OAuth2PasswordRequestForm = Depends(),
):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return TokenResponse(access_token=create_access_token(user.username), is_admin=user.is_admin)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, db: DbSession):
    """Register a new user using a valid invite token."""
    invitation = db.query(Invitation).filter(Invitation.token == body.invite_token).first()
    if not invitation:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid invite token")
    if invitation.used:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite token already used")
    if invitation.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite token has expired")

    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

    user = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        is_admin=False,
        invited_by_id=invitation.invited_by_id,
    )
    db.add(user)
    invitation.used = True
    db.commit()
    db.refresh(user)

    return TokenResponse(access_token=create_access_token(user.username), is_admin=user.is_admin)
