from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from .. import services
from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import TodoCreate, TodoOut, TodoUpdate

router = APIRouter(prefix="/todos", tags=["todos"])


def _http(e: services.ServiceError) -> HTTPException:
    return HTTPException(e.status_code, e.message)


@router.get("", response_model=list[TodoOut])
def list_my_todos(
    completed: bool | None = None,
    priority: str | None = None,
    search: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return services.list_todos(db, owner_id=user.id, completed=completed, priority=priority, search=search)


@router.get("/stats")
def my_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.todo_stats(db, owner_id=user.id)


@router.post("", response_model=TodoOut, status_code=status.HTTP_201_CREATED)
def create_my_todo(data: TodoCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return services.create_todo(db, user.id, **data.model_dump())
    except services.ServiceError as e:
        raise _http(e)


@router.get("/{todo_id}", response_model=TodoOut)
def get_my_todo(todo_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return services.get_todo(db, todo_id, user.id)
    except services.ServiceError as e:
        raise _http(e)


@router.put("/{todo_id}", response_model=TodoOut)
def update_my_todo(
    todo_id: int, data: TodoUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        return services.update_todo(db, todo_id, user.id, **data.model_dump(exclude_unset=True))
    except services.ServiceError as e:
        raise _http(e)


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_todo(todo_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        services.delete_todo(db, todo_id, user.id)
    except services.ServiceError as e:
        raise _http(e)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
