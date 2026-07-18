"""One-step Reel publish: use existing reel/ or generate from post.json."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import requests

from app import publisher
from app.post_spec import build_caption, load_post_json
from app.resources import local_path_to_github_raw_url, verify_public_resource_url
from app.text_post import day_folder_for, generate_text_reel, post_json_path, reel_path_for

FALLBACK_CAPTION = """KuchAurTha

Stories where the real event is stranger than the explanation.

#KuchAurTha #TrueStory #IndianMystery"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Publish today's Reel in one step via GitHub raw URL. "
            "If reel/reel.mp4 already exists, publish it. "
            "Otherwise generate from post.json and publish. "
            "Assets must already be pushed to the public resources repo."
        )
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Day folder date (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--day-folder",
        type=Path,
        default=None,
        help="Explicit path to a day folder.",
    )
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="Generate from post.json if needed, but do not publish.",
    )
    return parser.parse_args()


def resolve_day_folder(args: argparse.Namespace) -> Path:
    if args.day_folder is not None and args.date is not None:
        raise ValueError("Pass either --day-folder or --date, not both.")

    if args.day_folder is not None:
        return args.day_folder.expanduser().resolve()

    day = args.date or date.today().isoformat()
    return day_folder_for(day)


def resolve_caption(day_folder: Path) -> str:
    """Prefer caption from post.json when available."""
    post_path = post_json_path(day_folder)
    if not post_path.is_file():
        return FALLBACK_CAPTION

    post = load_post_json(post_path)
    return build_caption(post)


def ensure_reel(day_folder: Path) -> tuple[Path, str, bool]:
    """
    Return (reel_path, caption, generated).

    Prefer an existing reel/reel.mp4. Otherwise generate from post.json.
    """
    reel_path = reel_path_for(day_folder)
    caption = resolve_caption(day_folder)

    if reel_path.is_file():
        print(f"Found existing Reel:\n{reel_path}")
        print("Skipping generation — publishing the saved Reel.")
        return reel_path, caption, False

    post_path = post_json_path(day_folder)
    if not post_path.is_file():
        raise FileNotFoundError(
            f"No reel/reel.mp4 and no post.json in {day_folder}.\n"
            "Either save a Reel under reel/reel.mp4 or add a post.json."
        )

    print("No existing Reel found. Generating from post.json...")
    result = generate_text_reel(day_folder)
    return result["reel_path"], result["caption"], True


def main() -> None:
    args = parse_args()

    try:
        day_folder = resolve_day_folder(args)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Reel Publish Pipeline")
    print("-" * 32)
    print(f"\nDay folder:\n{day_folder}\n")

    if not day_folder.is_dir():
        print(f"Day folder does not exist:\n{day_folder}")
        sys.exit(0)

    try:
        reel_path, caption, generated = ensure_reel(day_folder)
    except Exception as exc:
        print(f"\nFailed to prepare Reel: {exc}", file=sys.stderr)
        sys.exit(1)

    reel_url = local_path_to_github_raw_url(reel_path)

    print(f"\nPublic URL:\n{reel_url}")
    print("\nCaption:")
    print("-" * 32)
    print(caption)
    print("-" * 32)

    if args.generate_only:
        action = "generated" if generated else "already present"
        print(f"\nGenerate-only mode. Reel is {action}:\n{reel_path}")
        if generated:
            print(
                "\nPush the generated assets to the resources GitHub repo "
                "before publishing."
            )
        sys.exit(0)

    print("\nVerifying public Reel URL...")
    try:
        verify_public_resource_url(reel_url)
    except requests.HTTPError:
        print(
            "The Reel exists locally but is not publicly accessible yet.\n"
            "Commit and push reel.mp4 to the resources GitHub repository, "
            "then rerun this command."
        )
        sys.exit(1)
    except requests.RequestException as exc:
        print(f"Failed to verify public Reel URL: {exc}")
        sys.exit(1)

    print("\nPublishing Reel via GitHub URL...")
    try:
        media_id = publisher.publish_reel(reel_url, caption)
        print("\nReel published successfully!")
        print(f"Media ID: {media_id}")
    except Exception as exc:
        print(f"\nFailed to publish Reel: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
