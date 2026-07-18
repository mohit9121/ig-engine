"""Load and validate day-wise text post JSON specs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app import config


REQUIRED_TOP_LEVEL = ("meta", "background_music", "style", "caption", "hashtags", "scenes")
REQUIRED_META = ("post_type", "date", "slug")
REQUIRED_SCENE = ("scene_id", "duration_seconds", "text")


def load_post_json(path: Path) -> dict[str, Any]:
    """Load and validate a post.json file."""
    if not path.is_file():
        raise FileNotFoundError(f"post.json not found: {path}")

    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError("post.json must contain a JSON object.")

    validate_post(data)
    return data


def validate_post(data: dict[str, Any]) -> None:
    """Validate the research-LLM post JSON structure."""
    missing = [key for key in REQUIRED_TOP_LEVEL if key not in data]
    if missing:
        raise ValueError(f"post.json missing keys: {', '.join(missing)}")

    meta = data["meta"]
    if not isinstance(meta, dict):
        raise ValueError("meta must be an object.")

    missing_meta = [key for key in REQUIRED_META if key not in meta]
    if missing_meta:
        raise ValueError(f"meta missing keys: {', '.join(missing_meta)}")

    post_type = meta["post_type"]
    if post_type not in {"reel", "carousel", "image"}:
        raise ValueError(
            f"Unsupported post_type '{post_type}'. Expected reel, carousel, or image."
        )

    style = data["style"]
    if style not in config.SUPPORTED_POST_STYLES:
        raise ValueError(
            f"Unsupported style '{style}'. "
            f"Expected one of: {', '.join(sorted(config.SUPPORTED_POST_STYLES))}."
        )

    caption = data["caption"]
    if not isinstance(caption, dict) or not str(caption.get("text", "")).strip():
        raise ValueError("caption.text is required.")

    hashtags = data["hashtags"]
    if not isinstance(hashtags, list) or not hashtags:
        raise ValueError("hashtags must be a non-empty list.")

    scenes = data["scenes"]
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("scenes must be a non-empty list.")

    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            raise ValueError(f"scenes[{index}] must be an object.")

        missing_scene = [key for key in REQUIRED_SCENE if key not in scene]
        if missing_scene:
            raise ValueError(
                f"scenes[{index}] missing keys: {', '.join(missing_scene)}"
            )

        duration = scene["duration_seconds"]
        if not isinstance(duration, (int, float)) or duration <= 0:
            raise ValueError(
                f"scenes[{index}].duration_seconds must be a positive number."
            )

        text = scene["text"]
        if isinstance(text, dict):
            if not any(str(text.get(key, "")).strip() for key in ("line_1", "line_2")):
                raise ValueError(
                    f"scenes[{index}].text needs at least line_1 or line_2."
                )
        elif not str(text).strip():
            raise ValueError(f"scenes[{index}].text is empty.")


def build_caption(post: dict[str, Any]) -> str:
    """Combine caption text and hashtags into a single Instagram caption."""
    caption_text = str(post["caption"]["text"]).strip()
    hashtags = " ".join(str(tag).strip() for tag in post["hashtags"] if str(tag).strip())
    if not hashtags:
        return caption_text
    return f"{caption_text}\n\n{hashtags}"
