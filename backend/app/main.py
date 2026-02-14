import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
