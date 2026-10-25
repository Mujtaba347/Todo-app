from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..chatbot import audit, run_chat
from ..config import settings
from ..database import get_db
from ..deps import get_current_user, require_admin
from ..guardrails import limiter
from ..models import AuditLog, User
from ..schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


def _guard(db: Session, user: User, is_admin: bool, message: str) -> None:
    """Rate limit + daily quota. Protects the OpenRouter credit from abuse."""
    limiter.check(f"chat:{user.id}", settings.chat_per_minute, 60, "You are sending messages too fast")

    daily_limit = settings.chat_daily_limit_admin if is_admin else settings.chat_daily_limit_user
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    used = db.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.user_id == user.id, AuditLog.kind == "chat", AuditLog.created_at >= start
        )
    ) or 0
    if used >= daily_limit:
        raise HTTPException(429, f"Daily assistant limit reached ({daily_limit} messages). It resets at midnight UTC.")
    audit(db, user, "chat", "", message[:300], True)


@router.post("/user", response_model=ChatResponse)
def chat_as_user(req: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The personal assistant: scoped to the caller's own todos."""
    _guard(db, user, False, req.message)
    reply, actions = run_chat(
        db, user, req.message, [h.model_dump() for h in req.history], is_admin=False
    )
    return ChatResponse(reply=reply, actions=actions)


@router.post("/admin", response_model=ChatResponse)
def chat_as_admin(req: ChatRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """The admin assistant: full access to users, todos and the database."""
    _guard(db, admin, True, req.message)
    reply, actions = run_chat(
        db, admin, req.message, [h.model_dump() for h in req.history], is_admin=True
    )
    return ChatResponse(reply=reply, actions=actions)
