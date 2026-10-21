# Entry point untuk Vercel Services (entrypoint: "main:app").
# FastAPI instance sebenarnya ada di app.main.
from app.main import app

__all__ = ["app"]
