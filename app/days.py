"""Day-folder helpers under resources/ig/posts/days."""

from __future__ import annotations

from pathlib import Path

from app import config


def day_folder_for(date_str: str) -> Path:
    return config.RESOURCES_POSTS_DIR / date_str


def post_json_path(day_folder: Path) -> Path:
    return day_folder / "post.json"


def reel_path_for(day_folder: Path) -> Path:
    return day_folder / "reel" / "reel.mp4"


def iter_day_folders() -> list[Path]:
    """Return sorted day folders under posts/days."""
    root = config.RESOURCES_POSTS_DIR
    if not root.is_dir():
        return []

    return sorted(
        path
        for path in root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )


def days_needing_text_reel() -> list[Path]:
    """Day folders that have post.json but no reel/reel.mp4."""
    pending: list[Path] = []
    for day_folder in iter_day_folders():
        if post_json_path(day_folder).is_file() and not reel_path_for(day_folder).is_file():
            pending.append(day_folder)
    return pending
