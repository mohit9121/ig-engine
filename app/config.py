"""Application configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

API_VERSION = "v25.0"
API_BASE_URL = "https://graph.instagram.com"

GITHUB_USERNAME = "mohit9121"
GITHUB_REPOSITORY = "resources"
GITHUB_BRANCH = "main"
GITHUB_RAW_BASE_URL = (
    f"https://raw.githubusercontent.com/{GITHUB_USERNAME}"
    f"/{GITHUB_REPOSITORY}/{GITHUB_BRANCH}"
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESOURCES_ROOT = PROJECT_ROOT / "resources"
RESOURCES_POSTS_DIR = RESOURCES_ROOT / "ig" / "posts" / "days"

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

POLL_DELAY_SECONDS = 5
POLL_MAX_ATTEMPTS = 20
REEL_POLL_DELAY_SECONDS = 5
REEL_POLL_MAX_ATTEMPTS = 60
REQUEST_TIMEOUT_SECONDS = 30


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value or not value.strip():
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Set it in your .env file."
        )
    return value.strip()


IG_ID = _require_env("IG_ID")
IG_ACCESS_TOKEN = _require_env("IG_ACCESS_TOKEN")
