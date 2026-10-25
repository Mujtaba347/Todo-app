from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from . import models, services
from .config import DEFAULT_SECRET, settings
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


def check_production_settings() -> None:
    """Refuse to start in production with unsafe defaults."""
    if not settings.is_production:
        return
    problems = []
    if settings.secret_key == DEFAULT_SECRET or len(settings.secret_key) < 32:
        problems.append("SECRET_KEY must be a random string of at least 32 characters")
    if settings.admin_password in ("admin12345", "ChangeMe123!") or len(settings.admin_password) < 10:
        problems.append("ADMIN_PASSWORD must be changed (at least 10 characters, not the default)")
    if any("localhost" in o or "127.0.0.1" in o for o in settings.cors_origin_list):
        print("[startup] WARNING: CORS_ORIGINS still contains localhost")
    if problems:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_production_settings()
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

@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


for router in (auth.router, todos.router, admin.router, chat.router):
    app.include_router(router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "ai_configured": bool(settings.openrouter_api_key)}
