"""Discover today's images and publish them to Instagram."""

import sys
from datetime import date
from pathlib import Path

from app import config
from app.publisher import publish_carousel, publish_image

CAPTION = """Daily Brief 📖

An idea worth thinking about.

Follow @the_daily_brief01 for more.

#dailybrief #ideas #learning"""


def local_path_to_github_raw_url(local_path: Path) -> str:
    """Convert a local resources path to a public GitHub raw URL."""
    try:
        relative_path = local_path.relative_to(config.RESOURCES_ROOT)
    except ValueError as exc:
        raise ValueError(f"Path is not under resources root: {local_path}") from exc

    return f"{config.GITHUB_RAW_BASE_URL}/{relative_path.as_posix()}"


def find_todays_images(today: str) -> list[Path]:
    """Return supported images for today's date folder, sorted by filename."""
    today_dir = config.RESOURCES_POSTS_DIR / today

    if not today_dir.is_dir():
        return []

    images = [
        path
        for path in today_dir.iterdir()
        if path.is_file() and path.suffix.lower() in config.SUPPORTED_IMAGE_EXTENSIONS
    ]
    return sorted(images, key=lambda path: path.name.lower())


def main() -> None:
    today = date.today().isoformat()
    today_dir = config.RESOURCES_POSTS_DIR / today

    print(f"Looking for images in: {today_dir}")

    if not today_dir.is_dir():
        print(f"No folder found for today ({today}).")
        print(f"Expected directory: {today_dir}")
        sys.exit(0)

    images = find_todays_images(today)

    if not images:
        print(f"No supported images found in: {today_dir}")
        print(f"Supported extensions: {', '.join(sorted(config.SUPPORTED_IMAGE_EXTENSIONS))}")
        sys.exit(0)

    print(f"Found {len(images)} image(s) to publish.\n")

    image_urls = [local_path_to_github_raw_url(image_path) for image_path in images]

    print("Images to publish:")
    for image_url in image_urls:
        print(f"- {image_url}")

    try:
        if len(image_urls) == 1:
            print("\nPublishing single image post...")
            media_id = publish_image(image_urls[0], CAPTION)
        else:
            print(f"\nPublishing carousel with {len(image_urls)} images...")
            media_id = publish_carousel(image_urls, CAPTION)

        print("\nSuccessfully published post!")
        print(f"Media ID: {media_id}")

    except Exception as exc:
        print(f"\nFailed to publish post: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
