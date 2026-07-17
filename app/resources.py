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
