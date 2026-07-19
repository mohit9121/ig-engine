"""Bulk-generate local Reels for day folders that have post.json but no reel."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.days import (
    day_folder_for,
    days_needing_text_reel,
    iter_day_folders,
    post_json_path,
    reel_path_for,
)
from generation.text_reel import generate_text_reel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scan resources/ig/posts/days and generate local Reels from post.json "
            "when reel/reel.mp4 is missing. Does not publish or push to GitHub."
        )
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Only process one day folder (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even if reel/reel.mp4 already exists.",
    )
    return parser.parse_args()


def folders_to_process(date_str: str | None, force: bool) -> list[Path]:
    if date_str is not None:
        day_folder = day_folder_for(date_str)
        if not day_folder.is_dir():
            raise FileNotFoundError(f"Day folder does not exist: {day_folder}")
        if not post_json_path(day_folder).is_file():
            raise FileNotFoundError(f"No post.json in {day_folder}")
        if reel_path_for(day_folder).is_file() and not force:
            return []
        return [day_folder]

    if force:
        return [
            folder
            for folder in iter_day_folders()
            if post_json_path(folder).is_file()
        ]

    return days_needing_text_reel()


def main() -> None:
    args = parse_args()

    print("Text Reel Generation")
    print("-" * 32)

    try:
        folders = folders_to_process(args.date, args.force)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not folders:
        if args.date:
            print(f"\nNothing to generate for {args.date} (reel already exists).")
            print("Pass --force to regenerate.")
        else:
            print("\nNo pending day folders found.")
            print("Looking for folders with post.json and no reel/reel.mp4.")
        sys.exit(0)

    print(f"\nFolders to process: {len(folders)}\n")
    for folder in folders:
        print(f"- {folder.name}")

    succeeded = 0
    failed = 0

    for folder in folders:
        print("\n" + "=" * 32)
        print(f"Generating: {folder.name}")
        print("=" * 32)
        try:
            result = generate_text_reel(folder)
            print(f"\nWrote: {result['reel_path']}")
            succeeded += 1
        except Exception as exc:
            print(f"\nFailed for {folder.name}: {exc}", file=sys.stderr)
            failed += 1

    print("\n" + "-" * 32)
    print(f"Done. Generated: {succeeded}. Failed: {failed}.")
    print("Push the resources repo when ready, then use publishing.publish_reel.")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
