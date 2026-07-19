"""Generate a local Reel from a day folder's post.json."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.days import post_json_path, reel_path_for
from app.post_spec import build_caption, load_post_json
from app.resources import music_github_raw_url, resolve_background_music
from utils.image.render import render
from utils.reel.generate_reel import check_ffmpeg, generate_reel


def render_scene_images(post: dict[str, Any], day_folder: Path) -> list[Path]:
    """Render one styled image per scene into the day folder."""
    style = post["style"]
    images: list[Path] = []

    for index, scene in enumerate(post["scenes"], start=1):
        output_path = day_folder / f"image_{index}.png"
        render(
            {
                "style": style,
                "text": scene["text"],
            },
            output_path,
        )
        images.append(output_path)
        print(f"Rendered scene {scene.get('scene_id', index)} → {output_path.name}")

    return images


def generate_text_reel(
    day_folder: Path,
    *,
    post: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Load post.json, render scene images, and write reel/reel.mp4 locally.

    Does not publish or push to GitHub.
    """
    day_folder = day_folder.expanduser().resolve()
    if not day_folder.is_dir():
        raise FileNotFoundError(f"Day folder does not exist: {day_folder}")

    if post is None:
        post = load_post_json(post_json_path(day_folder))

    check_ffmpeg()

    music_path = resolve_background_music(post["background_music"])
    print(f"Background music: {music_path.name}")
    print(f"Music source URL: {music_github_raw_url(music_path.name)}")

    print("\nRendering scene images...")
    images = render_scene_images(post, day_folder)

    durations = [float(scene["duration_seconds"]) for scene in post["scenes"]]
    output_path = reel_path_for(day_folder)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("\nGenerating reel...")
    generate_reel(
        images=images,
        audio_path=music_path,
        output_path=output_path,
        image_durations=durations,
    )

    return {
        "post": post,
        "day_folder": day_folder,
        "images": images,
        "music_path": music_path,
        "reel_path": output_path,
        "caption": build_caption(post),
        "durations": durations,
    }
