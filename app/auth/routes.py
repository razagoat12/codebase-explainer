import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import datetime, timedelta, timezone

from app.auth.models import TIER_QUOTAS, PlanTier, User
from app.auth.utils import create_access_token, decode_token, hash_password, verify_password
from app.config import settings
from app.database import get_db
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def _verify_turnstile(token: str | None) -> None:
    """Abuse guard on registration. A no-op unless TURNSTILE_SECRET_KEY is
    configured, so registration works with no CAPTCHA in local dev / until the
    operator sets up a Cloudflare Turnstile site."""
    if not settings.turnstile_secret_key:
        return
    if not token:
        raise HTTPException(status_code=400, detail="Missing CAPTCHA verification")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            TURNSTILE_VERIFY_URL,
            data={"secret": settings.turnstile_secret_key, "response": token},
        )
    if not resp.json().get("success"):
        raise HTTPException(status_code=400, detail="CAPTCHA verification failed")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    turnstile_token: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    user_id: str
    email: str


class MeResponse(BaseModel):
    user_id: str
    email: str
    plan_tier: str
    monthly_usage: int
    monthly_quota: int


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    await _verify_turnstile(body.turnstile_token)
    email = body.email.lower()
    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    user = User(email=email, hashed_password=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse(user_id=user.id, email=user.email)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user.id))


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    try:
        user_id = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def _quota_for(user: User) -> int:
    return TIER_QUOTAS.get(PlanTier(user.plan_tier), TIER_QUOTAS[PlanTier.free])


async def enforce_quota(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency that resets monthly counters and blocks if over quota."""
    now = datetime.now(timezone.utc)
    reset_at = current_user.usage_reset_at
    if reset_at.tzinfo is None:
        reset_at = reset_at.replace(tzinfo=timezone.utc)

    # Reset usage every 30 days
    if now - reset_at > timedelta(days=30):
        current_user.monthly_usage = 0
        current_user.usage_reset_at = now
        await db.commit()

    if current_user.monthly_usage >= _quota_for(current_user):
        raise HTTPException(
            status_code=402,
            detail=f"Monthly quota exceeded ({_quota_for(current_user)} analyses). Upgrade to Pro to continue.",
        )
    return current_user


@router.get("/me", response_model=MeResponse)
async def me(current_user: User = Depends(get_current_user)):
    return MeResponse(
        user_id=current_user.id,
        email=current_user.email,
        plan_tier=current_user.plan_tier,
        monthly_usage=current_user.monthly_usage,
        monthly_quota=_quota_for(current_user),
    )
