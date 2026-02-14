import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.upload_dir, exist_ok=True)
    yield


app = FastAPI(title="Video Analyzer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from app.routers import upload, analyze, status, results, export, files, thumbnails, compare

app.include_router(upload.router)
app.include_router(analyze.router)
app.include_router(status.router)
app.include_router(results.router)
app.include_router(export.router)
app.include_router(files.router)
app.include_router(thumbnails.router)
app.include_router(compare.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/validate-key")
async def validate_key(body: dict):
    """Validate a Google API key by making a lightweight API call."""
    key = body.get("api_key", "").strip()
    if not key:
        return {"valid": False, "error": "No API key provided"}
    try:
        from google import genai
        client = genai.Client(api_key=key)
        # List models as a cheap validation call
        models = client.models.list()
        next(iter(models))
        return {"valid": True}
    except Exception as e:
        return {"valid": False, "error": str(e)}


# Serve frontend build in production (when frontend/dist exists)
_frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    from fastapi.responses import FileResponse

    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the React SPA for any non-API route."""
        file_path = _frontend_dist / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_frontend_dist / "index.html")
