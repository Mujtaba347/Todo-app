from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Priority = Literal["low", "medium", "high"]
Role = Literal["user", "admin"]


# ---------- Auth / users ----------
class RegisterIn(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    identifier: str  # email or username
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime


class AdminUserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=6, max_length=128)
    role: Role = "user"
    is_active: bool = True


class AdminUserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = Field(default=None, min_length=3, max_length=80)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    role: Role | None = None
    is_active: bool | None = None


# ---------- Todos ----------
class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    priority: Priority = "medium"
    due_date: date | None = None
    completed: bool = False


class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    priority: Priority | None = None
    due_date: date | None = None
    completed: bool | None = None


class AdminTodoCreate(TodoCreate):
    owner_id: int


class TodoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    completed: bool
    priority: str
    due_date: date | None
    owner_id: int
    created_at: datetime
    updated_at: datetime


class AdminTodoOut(TodoOut):
    owner_username: str


# ---------- Chat ----------
class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatTurn] = []


class ChatAction(BaseModel):
    tool: str
    args: dict
    ok: bool


class ChatResponse(BaseModel):
    reply: str
    actions: list[ChatAction] = []
