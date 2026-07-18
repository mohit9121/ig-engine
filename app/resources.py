"""Helpers for locating and resolving public resource URLs."""

from pathlib import Path

import requests

from app import config


def local_path_to_github_raw_url(local_path: Path) -> str:
    """Convert a local resources path to a public GitHub raw URL."""
    try:
        relative_path = local_path.relative_to(config.RESOURCES_ROOT)
    except ValueError as exc:
        raise ValueError(f"Path is not under resources root: {local_path}") from exc

    return f"{config.GITHUB_RAW_BASE_URL}/{relative_path.as_posix()}"


def resolve_background_music(music_name: str) -> Path:
    """
    Resolve a background music filename (or research-prompt alias)
    to a local file under resources/ig/music/background/.
    """
    filename = Path(music_name).name
    resolved_name = config.BACKGROUND_MUSIC_ALIASES.get(filename, filename)
    music_path = config.RESOURCES_MUSIC_DIR / resolved_name

    if not music_path.is_file():
        available = sorted(
            path.name
            for path in config.RESOURCES_MUSIC_DIR.glob("*.mp3")
            if path.is_file()
        )
        available_text = ", ".join(available) if available else "(none found)"
        raise FileNotFoundError(
            f"Background music not found: {music_name} "
            f"(resolved to {resolved_name}). "
            f"Available: {available_text}"
        )

    return music_path


def music_github_raw_url(music_name: str) -> str:
    """Return the public GitHub raw URL for a background music file."""
    music_path = resolve_background_music(music_name)
    return local_path_to_github_raw_url(music_path)


def verify_public_resource_url(url: str) -> None:
    """Verify that a resource URL is publicly reachable."""
    response = requests.head(
        url,
        timeout=config.REQUEST_TIMEOUT_SECONDS,
        allow_redirects=True,
    )

    if response.status_code == 405:
        response = requests.get(
            url,
            timeout=config.REQUEST_TIMEOUT_SECONDS,
            stream=True,
        )

    response.raise_for_status()
