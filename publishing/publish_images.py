"""Publish today's image or carousel from public GitHub raw URLs.

Assumes images already exist locally and have been pushed to the public
resources repository. Does not generate content.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from app import config
from app.days import day_folder_for
from app.publisher import publish_carousel, publish_image
from app.resources import local_path_to_github_raw_url

FALLBACK_CAPTION = """Daily Brief 📖

An idea worth thinking about.

Follow @the_daily_brief01 for more.

#dailybrief #ideas #learning"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Publish one day's image/carousel to Instagram via GitHub raw URLs. "
            "Does not generate images."
        )
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Day folder date (YYYY-MM-DD). Defaults to today.",
    )
    return parser.parse_args()


def find_images(day_folder: Path) -> list[Path]:
    if not day_folder.is_dir():
        return []

    images = [
        path
        for path in day_folder.iterdir()
        if path.is_file() and path.suffix.lower() in config.SUPPORTED_IMAGE_EXTENSIONS
    ]
    return sorted(images, key=lambda path: path.name.lower())


def main() -> None:
    args = parse_args()
    day = args.date or date.today().isoformat()
    day_folder = day_folder_for(day)

    print("Image Publishing")
    print("-" * 32)
    print(f"\nLooking for images in:\n{day_folder}")

    if not day_folder.is_dir():
        print(f"\nNo folder found for {day}.")
        sys.exit(0)

    images = find_images(day_folder)
    if not images:
        print(f"\nNo supported images found in: {day_folder}")
        print(
            f"Supported extensions: "
            f"{', '.join(sorted(config.SUPPORTED_IMAGE_EXTENSIONS))}"
        )
        sys.exit(0)

    image_urls = [local_path_to_github_raw_url(path) for path in images]

    print(f"\nFound {len(image_urls)} image(s):")
    for image_url in image_urls:
        print(f"- {image_url}")

    try:
        if len(image_urls) == 1:
            print("\nPublishing single image post...")
            media_id = publish_image(image_urls[0], FALLBACK_CAPTION)
        else:
            print(f"\nPublishing carousel with {len(image_urls)} images...")
            media_id = publish_carousel(image_urls, FALLBACK_CAPTION)

        print("\nSuccessfully published post!")
        print(f"Media ID: {media_id}")
    except Exception as exc:
        print(f"\nFailed to publish post: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
