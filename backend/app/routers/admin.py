from sqlalchemy import select
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from .. import services
from ..database import get_db
from ..deps import require_admin
from ..models import AuditLog, User
from ..schemas import (
    AdminTodoCreate,
    AdminTodoOut,
    AdminUserCreate,
    AdminUserUpdate,
    TodoUpdate,
    UserOut,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _http(e: services.ServiceError) -> HTTPException:
    return HTTPException(e.status_code, e.message)


def _todo_out(t) -> dict:
    return services.todo_to_dict(t, include_owner=True)


# ----------------------------------------------------------------- overview
@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    return services.platform_stats(db)


# -------------------------------------------------------------------- users
@router.get("/users", response_model=list[UserOut])
def list_users(search: str | None = None, role: str | None = None, db: Session = Depends(get_db)):
    return services.list_users(db, search=search, role=role)


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(data: AdminUserCreate, db: Session = Depends(get_db)):
    try:
        return services.create_user(db, **data.model_dump())
    except services.ServiceError as e:
        raise _http(e)


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int, data: AdminUserUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    try:
        return services.update_user(db, user_id, admin, **data.model_dump(exclude_unset=True))
    except services.ServiceError as e:
        raise _http(e)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    try:
        services.delete_user(db, user_id, admin)
    except services.ServiceError as e:
        raise _http(e)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# -------------------------------------------------------------------- todos
@router.get("/todos", response_model=list[AdminTodoOut])
def list_all_todos(
    owner_id: int | None = None,
    completed: bool | None = None,
    priority: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    todos = services.list_todos(
        db, owner_id=owner_id, completed=completed, priority=priority, search=search, limit=500
    )
    return [_todo_out(t) for t in todos]


@router.post("/todos", response_model=AdminTodoOut, status_code=status.HTTP_201_CREATED)
def create_todo(data: AdminTodoCreate, db: Session = Depends(get_db)):
    payload = data.model_dump()
    owner_id = payload.pop("owner_id")
    try:
        return _todo_out(services.create_todo(db, owner_id, **payload))
    except services.ServiceError as e:
        raise _http(e)


@router.put("/todos/{todo_id}", response_model=AdminTodoOut)
def update_todo(todo_id: int, data: TodoUpdate, db: Session = Depends(get_db)):
    try:
        return _todo_out(services.update_todo(db, todo_id, None, **data.model_dump(exclude_unset=True)))
    except services.ServiceError as e:
        raise _http(e)


@router.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    try:
        services.delete_todo(db, todo_id, None)
    except services.ServiceError as e:
        raise _http(e)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ----------------------------------------------------------------- audit log
@router.get("/audit")
def audit_log(limit: int = 100, kind: str | None = None, db: Session = Depends(get_db)):
    """Recent chatbot messages and actions (who asked what, what the bot did)."""
    q = select(AuditLog).order_by(AuditLog.id.desc()).limit(min(max(limit, 1), 500))
    if kind in ("chat", "tool"):
        q = q.where(AuditLog.kind == kind)
    return [
        {
            "id": a.id,
            "user_id": a.user_id,
            "username": a.username,
            "kind": a.kind,
            "tool": a.tool,
            "detail": a.detail,
            "ok": a.ok,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in db.scalars(q)
    ]
