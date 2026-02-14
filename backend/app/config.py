from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_api_key: str = ""
    upload_dir: str = str(Path(__file__).parent.parent / "uploads")
    max_file_size_mb: int = 2000
    allowed_origins: list[str] = ["http://localhost:5173"]

    model_config = {
        "env_file": [
            str(Path(__file__).parent.parent.parent / ".env"),  # project root
            ".env",  # cwd fallback
        ],
        "env_file_encoding": "utf-8",
    }


settings = Settings()
