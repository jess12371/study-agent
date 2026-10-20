# Entry point FastAPI — Study Agent API.

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, chat, export, feasibility, goals, plans, progress, quizzes, reschedule, resources, tutor
from app.core.config import settings

# Inisialisasi aplikasi FastAPI (async).
app = FastAPI(
    title="Study Agent API",
    description="Backend API untuk Study Agent — bikin jadwal belajar personal.",
    version="0.1.0",
)

# Izinkan akses dari frontend (Next.js) saat development (origin dari .env).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # Request body tidak valid → 400 (bukan default 422).
    # Ambil field yang aman diserialisasi (ctx bisa berisi objek Exception).
    detail = [
        {"loc": error.get("loc"), "msg": error.get("msg"), "type": error.get("type")}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=400, content={"detail": detail})


@app.get("/api/health")
async def health() -> dict[str, str]:
    # Endpoint health check untuk memastikan service berjalan.
    return {"status": "ok", "service": "study-agent-api"}


# Daftarkan router fitur.
app.include_router(auth.router)
app.include_router(goals.router)
app.include_router(feasibility.router)
app.include_router(plans.router)
app.include_router(progress.router)
app.include_router(export.router)
app.include_router(reschedule.router)
app.include_router(resources.router)
app.include_router(chat.router)
app.include_router(tutor.router)
app.include_router(quizzes.router)
