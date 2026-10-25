from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from . import models, services
from .config import settings
from .database import Base, SessionLocal, engine
from .routers import admin, auth, chat, todos


def seed_admin() -> None:
    with SessionLocal() as db:
        exists = db.scalar(select(models.User).where(models.User.role == "admin"))
        if exists:
            return
        services.create_user(
            db,
            email=settings.admin_email,
            username=settings.admin_username,
            password=settings.admin_password,
            role="admin",
        )
        print(f"[startup] Created default admin '{settings.admin_username}' / {settings.admin_email}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_admin()
    yield


app = FastAPI(title="Todo App API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (auth.router, todos.router, admin.router, chat.router):
    app.include_router(router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "ai_configured": bool(settings.openrouter_api_key)}
