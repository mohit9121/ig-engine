"""Publish today's Reel to Instagram."""

import sys
from datetime import date
from pathlib import Path

import requests

from app import config
from app import publisher
from app.resources import local_path_to_github_raw_url, verify_public_resource_url

CAPTION = """Daily Brief 📖

An idea worth thinking about.

Follow @the_daily_brief01 for more.

#dailybrief #ideas #learning"""


def get_todays_reel_path(today: str) -> Path:
    return config.RESOURCES_POSTS_DIR / today / "reel" / "reel.mp4"


def main() -> None:
    # TODO: Add idempotency / publishing history before production scheduling
    # so rerunning this script on the same day does not publish twice.

    today = date.today().isoformat()
    reel_path = get_todays_reel_path(today)

    if not reel_path.is_file():
        print(f"No Reel found for today ({today}).")
        print(f"Expected:\n{reel_path}")
        sys.exit(0)

    reel_url = local_path_to_github_raw_url(reel_path)

    print(f"Today's Reel:\n{reel_path}\n")
    print(f"Public URL:\n{reel_url}\n")

    try:
        verify_public_resource_url(reel_url)
    except requests.HTTPError:
        print(
            "The Reel exists locally but is not publicly accessible from the "
            "resources repository. Make sure you committed and pushed reel.mp4 "
            "to the resources GitHub repository."
        )
        sys.exit(1)
    except requests.RequestException as exc:
        print(f"Failed to verify public Reel URL: {exc}")
        sys.exit(1)

    try:
        media_id = publisher.publish_reel(reel_url, CAPTION)
        print("\nReel published successfully!")
        print(f"Media ID: {media_id}")
    except Exception as exc:
        print(f"\nFailed to publish Reel: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
