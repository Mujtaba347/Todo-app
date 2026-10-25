from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import services
from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..guardrails import client_ip, limiter
from ..models import User
from ..schemas import LoginIn, RegisterIn, Token, UserOut
from ..security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, request: Request, db: Session = Depends(get_db)):
    if not settings.allow_registration:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Self-registration is disabled. Ask an administrator for an account.")
    limiter.check(
        f"register:{client_ip(request)}", settings.register_per_hour_per_ip, 3600, "Too many sign-ups from this network"
    )
    try:
        return services.create_user(
            db, email=data.email, username=data.username, password=data.password, role="user"
        )
    except services.ServiceError as e:
        raise HTTPException(e.status_code, e.message)


@router.post("/login", response_model=Token)
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    # Temporary lock after repeated failures for the same account from the same IP
    key = f"login:{client_ip(request)}:{data.identifier.strip().lower()}"
    wait = limiter.retry_after(key, settings.login_max_failures, settings.login_lockout_seconds)
    if wait:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Too many failed attempts. Try again in {wait // 60 + 1} minute(s).",
            headers={"Retry-After": str(wait)},
        )

    user = services.find_user_by_identifier(db, data.identifier)
    if not user or not verify_password(data.password, user.hashed_password):
        limiter.add(key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is disabled")
    limiter.reset(key)
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
