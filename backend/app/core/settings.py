import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


def _load_env_files() -> None:
    backend_dir = Path(__file__).resolve().parents[2]
    repo_root = backend_dir.parent

    load_dotenv(repo_root / ".env")
    load_dotenv(backend_dir / ".env", override=True)


class Settings(BaseModel):
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"


@lru_cache
def get_settings() -> Settings:
    _load_env_files()
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    )
