from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..chatbot import run_chat
from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import User
from ..schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/user", response_model=ChatResponse)
def chat_as_user(req: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The personal assistant: scoped to the caller's own todos."""
    reply, actions = run_chat(
        db, user, req.message, [h.model_dump() for h in req.history], is_admin=False
    )
    return ChatResponse(reply=reply, actions=actions)


@router.post("/admin", response_model=ChatResponse)
def chat_as_admin(req: ChatRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """The admin assistant: full access to users, todos and the database."""
    reply, actions = run_chat(
        db, admin, req.message, [h.model_dump() for h in req.history], is_admin=True
    )
    return ChatResponse(reply=reply, actions=actions)
