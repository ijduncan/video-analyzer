from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_api_key: str = ""
    gemini_analysis_model: str = "gemini-3.8-flash"
    gemini_deep_model: str = "gemini-3.8-flash"
    database_path: str = str(Path(__file__).parent.parent / "data" / "library.sqlite3")
    max_concurrent_analyses: int = 2
    shape_index_concurrency: int = Field(default=3, ge=1, le=6)
    upload_dir: str = str(Path(__file__).parent.parent / "uploads")
    max_file_size_mb: int = 2000
    allowed_origins: list[str] = ["http://localhost:5173"]

    model_config = {
        "env_file": [
            str(Path(__file__).parent.parent.parent / ".env"),  # project root
            str(Path(__file__).parent.parent.parent / ".env.local"),
            ".env",  # cwd fallback
            ".env.local",
        ],
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
