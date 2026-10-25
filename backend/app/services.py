"""Business logic shared by the REST routers and the AI chatbot tools.

Everything here raises ServiceError on a problem so callers can turn it into
an HTTP error (routers) or a tool error message (chatbot).
"""
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from .models import Todo, User
from .security import hash_password

PRIORITIES = {"low", "medium", "high"}
ROLES = {"user", "admin"}


class ServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ---------------------------------------------------------------- serializers
def user_to_dict(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "username": u.username,
        "role": u.role,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


def todo_to_dict(t: Todo, include_owner: bool = False) -> dict:
    data = {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "completed": t.completed,
        "priority": t.priority,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "owner_id": t.owner_id,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }
    if include_owner:
        data["owner_username"] = t.owner.username if t.owner else None
    return data


# ---------------------------------------------------------------------- users
def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise ServiceError(f"User {user_id} not found", 404)
    return user


def find_user_by_identifier(db: Session, identifier: str) -> User | None:
    ident = identifier.strip().lower()
    return db.scalar(
        select(User).where(or_(func.lower(User.email) == ident, func.lower(User.username) == ident))
    )


def _ensure_unique(db: Session, email: str | None, username: str | None, exclude_id: int | None = None):
    if email:
        q = select(User.id).where(func.lower(User.email) == email.lower())
        if exclude_id:
            q = q.where(User.id != exclude_id)
        if db.scalar(q):
            raise ServiceError("Email is already registered", 409)
    if username:
        q = select(User.id).where(func.lower(User.username) == username.lower())
        if exclude_id:
            q = q.where(User.id != exclude_id)
        if db.scalar(q):
            raise ServiceError("Username is already taken", 409)


def create_user(
    db: Session, *, email: str, username: str, password: str, role: str = "user", is_active: bool = True
) -> User:
    if role not in ROLES:
        raise ServiceError("role must be 'user' or 'admin'")
    if len(password) < 6:
        raise ServiceError("Password must be at least 6 characters")
    email = email.strip().lower()
    username = username.strip()
    if len(username) < 3:
        raise ServiceError("Username must be at least 3 characters")
    _ensure_unique(db, email, username)
    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: int, acting_user: User, **changes) -> User:
    user = get_user(db, user_id)
    changes = {k: v for k, v in changes.items() if v is not None}

    if user.id == acting_user.id:
        if changes.get("role", user.role) != "admin":
            raise ServiceError("You cannot remove your own admin role")
        if changes.get("is_active", True) is False:
            raise ServiceError("You cannot deactivate your own account")
    if "role" in changes and changes["role"] not in ROLES:
        raise ServiceError("role must be 'user' or 'admin'")

    if "email" in changes:
        changes["email"] = changes["email"].strip().lower()
    if "username" in changes:
        changes["username"] = changes["username"].strip()
        if len(changes["username"]) < 3:
            raise ServiceError("Username must be at least 3 characters")
    _ensure_unique(db, changes.get("email"), changes.get("username"), exclude_id=user.id)

    if "password" in changes:
        if len(changes["password"]) < 6:
            raise ServiceError("Password must be at least 6 characters")
        user.hashed_password = hash_password(changes.pop("password"))
    for key, value in changes.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int, acting_user: User) -> None:
    user = get_user(db, user_id)
    if user.id == acting_user.id:
        raise ServiceError("You cannot delete your own account")
    db.delete(user)  # todos are removed through the cascade
    db.commit()


def list_users(db: Session, search: str | None = None, role: str | None = None, limit: int = 200) -> list[User]:
    q = select(User).order_by(User.id).limit(limit)
    if search:
        like = f"%{search.lower()}%"
        q = q.where(or_(func.lower(User.email).like(like), func.lower(User.username).like(like)))
    if role:
        q = q.where(User.role == role)
    return list(db.scalars(q))


# ---------------------------------------------------------------------- todos
def get_todo(db: Session, todo_id: int, owner_id: int | None = None) -> Todo:
    q = select(Todo).options(joinedload(Todo.owner)).where(Todo.id == todo_id)
    if owner_id is not None:
        q = q.where(Todo.owner_id == owner_id)
    todo = db.scalar(q)
    if not todo:
        raise ServiceError(f"Todo {todo_id} not found", 404)
    return todo


def list_todos(
    db: Session,
    owner_id: int | None = None,
    completed: bool | None = None,
    priority: str | None = None,
    search: str | None = None,
    limit: int = 200,
) -> list[Todo]:
    q = select(Todo).options(joinedload(Todo.owner)).order_by(Todo.completed, Todo.id.desc()).limit(limit)
    if owner_id is not None:
        q = q.where(Todo.owner_id == owner_id)
    if completed is not None:
        q = q.where(Todo.completed == completed)
    if priority:
        q = q.where(Todo.priority == priority)
    if search:
        like = f"%{search.lower()}%"
        q = q.where(or_(func.lower(Todo.title).like(like), func.lower(Todo.description).like(like)))
    return list(db.scalars(q))


def create_todo(
    db: Session,
    owner_id: int,
    *,
    title: str,
    description: str = "",
    priority: str = "medium",
    due_date: date | None = None,
    completed: bool = False,
) -> Todo:
    title = (title or "").strip()
    if not title:
        raise ServiceError("Title is required")
    if priority not in PRIORITIES:
        raise ServiceError("priority must be low, medium or high")
    get_user(db, owner_id)  # make sure the owner exists
    todo = Todo(
        title=title,
        description=description or "",
        priority=priority,
        due_date=due_date,
        completed=completed,
        owner_id=owner_id,
    )
    db.add(todo)
    db.commit()
    return get_todo(db, todo.id)


def update_todo(db: Session, todo_id: int, owner_id: int | None = None, **changes) -> Todo:
    todo = get_todo(db, todo_id, owner_id)
    for key, value in changes.items():
        if key == "due_date":
            todo.due_date = value  # None clears the date
        elif value is None:
            continue
        elif key == "title":
            if not value.strip():
                raise ServiceError("Title cannot be empty")
            todo.title = value.strip()
        elif key == "priority":
            if value not in PRIORITIES:
                raise ServiceError("priority must be low, medium or high")
            todo.priority = value
        elif key in {"description", "completed"}:
            setattr(todo, key, value)
        elif key == "owner_id":
            get_user(db, value)
            todo.owner_id = value
    db.commit()
    return get_todo(db, todo.id)


def delete_todo(db: Session, todo_id: int, owner_id: int | None = None) -> None:
    todo = get_todo(db, todo_id, owner_id)
    db.delete(todo)
    db.commit()


def delete_completed(db: Session, owner_id: int | None = None) -> int:
    q = select(Todo).where(Todo.completed.is_(True))
    if owner_id is not None:
        q = q.where(Todo.owner_id == owner_id)
    todos = list(db.scalars(q))
    for t in todos:
        db.delete(t)
    db.commit()
    return len(todos)


# ---------------------------------------------------------------------- stats
def todo_stats(db: Session, owner_id: int | None = None) -> dict:
    def count(*conds) -> int:
        q = select(func.count(Todo.id))
        if owner_id is not None:
            q = q.where(Todo.owner_id == owner_id)
        for c in conds:
            q = q.where(c)
        return db.scalar(q) or 0

    today = date.today()
    return {
        "total": count(),
        "completed": count(Todo.completed.is_(True)),
        "pending": count(Todo.completed.is_(False)),
        "overdue": count(Todo.completed.is_(False), Todo.due_date.is_not(None), Todo.due_date < today),
        "high_priority_pending": count(Todo.completed.is_(False), Todo.priority == "high"),
    }


def platform_stats(db: Session) -> dict:
    stats = todo_stats(db)
    stats["users"] = db.scalar(select(func.count(User.id))) or 0
    stats["admins"] = db.scalar(select(func.count(User.id)).where(User.role == "admin")) or 0
    stats["active_users"] = db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0
    return stats
