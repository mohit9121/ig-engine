"""Publish a day's Reel from its public GitHub raw URL.

Reels are expected to be already pushed to the public resources repository at:
  ig/posts/days/{YYYY-MM-DD}/reel/reel.mp4

URL is constructed directly from the date — no local file dependency.

Idempotency: a published.json log in publishing/ prevents double-posting the
same date on repeated runs.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import requests

from app import config, publisher
from app.resources import verify_public_resource_url

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FALLBACK_CAPTION = """KuchAurTha

Stories where the real event is stranger than the explanation.

#KuchAurTha #TrueStory #IndianMystery"""

# Path to the idempotency log (stored next to this script)
PUBLISHED_LOG = Path(__file__).parent / "published.json"


# ---------------------------------------------------------------------------
# URL construction (no local path required)
# ---------------------------------------------------------------------------

def reel_github_url(date_str: str) -> str:
    """Return the public GitHub raw URL for a day's reel.mp4."""
    return (
        f"{config.GITHUB_RAW_BASE_URL}"
        f"/ig/posts/days/{date_str}/reel/reel.mp4"
    )


def post_json_github_url(date_str: str) -> str:
    """Return the public GitHub raw URL for a day's post.json."""
    return (
        f"{config.GITHUB_RAW_BASE_URL}"
        f"/ig/posts/days/{date_str}/post.json"
    )


# ---------------------------------------------------------------------------
# Caption resolution
# ---------------------------------------------------------------------------

def _fetch_post_json_from_github(date_str: str) -> dict | None:
    """Fetch and parse post.json from GitHub raw URL. Returns None on failure."""
    url = post_json_github_url(date_str)
    try:
        response = requests.get(url, timeout=config.REQUEST_TIMEOUT_SECONDS)
        if response.status_code == 200:
            return response.json()
    except Exception as exc:
        print(f"  Could not fetch post.json from GitHub: {exc}")
    return None


def resolve_caption(date_str: str) -> str:
    """
    Try to build caption from post.json.

    Priority:
      1. Local resources/ig/posts/days/{date_str}/post.json
      2. GitHub raw URL for the same post.json
      3. FALLBACK_CAPTION constant
    """
    # 1. Try local file first (works when running locally with repo checked out)
    local_post = config.RESOURCES_POSTS_DIR / date_str / "post.json"
    if local_post.is_file():
        try:
            from app.post_spec import build_caption, load_post_json
            return build_caption(load_post_json(local_post))
        except Exception as exc:
            print(f"  Warning: could not load local post.json — {exc}")

    # 2. Try fetching from GitHub (works in CI where resources aren't checked out)
    print("  Local post.json not found, trying GitHub raw URL...")
    post_data = _fetch_post_json_from_github(date_str)
    if post_data:
        try:
            from app.post_spec import build_caption
            return build_caption(post_data)
        except Exception as exc:
            print(f"  Warning: could not parse remote post.json — {exc}")

    # 3. Fallback
    print("  Using fallback caption.")
    return FALLBACK_CAPTION


# ---------------------------------------------------------------------------
# Idempotency log
# ---------------------------------------------------------------------------

def _load_published_log() -> dict:
    if PUBLISHED_LOG.is_file():
        try:
            return json.loads(PUBLISHED_LOG.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_published_log(log: dict) -> None:
    PUBLISHED_LOG.write_text(
        json.dumps(log, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def is_already_published(date_str: str) -> bool:
    log = _load_published_log()
    return date_str in log


def record_published(date_str: str, media_id: str) -> None:
    log = _load_published_log()
    log[date_str] = {
        "media_id": media_id,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_published_log(log)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Publish one day's Reel to Instagram via its public GitHub raw URL. "
            "Does not generate Reels."
        )
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Day folder date (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Bypass idempotency check and re-publish even if already logged.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    day = args.date or date.today().isoformat()

    print("Reel Publishing")
    print("-" * 32)
    print(f"\nDate: {day}")

    # ------------------------------------------------------------------
    # Idempotency check
    # ------------------------------------------------------------------
    if not args.force and is_already_published(day):
        log = _load_published_log()
        entry = log[day]
        print(
            f"\nReel for {day} was already published.\n"
            f"   Media ID : {entry.get('media_id')}\n"
            f"   Published: {entry.get('published_at')}\n"
            "\nSkipping. Use --force to override."
        )
        sys.exit(0)

    # ------------------------------------------------------------------
    # Construct GitHub raw URL directly from date (no local file needed)
    # ------------------------------------------------------------------
    reel_url = reel_github_url(day)
    print(f"\nPublic Reel URL:\n{reel_url}")

    # ------------------------------------------------------------------
    # Resolve caption
    # ------------------------------------------------------------------
    print("\nResolving caption...")
    caption = resolve_caption(day)
    print("\nCaption:")
    print("-" * 32)
    print(caption)
    print("-" * 32)

    # ------------------------------------------------------------------
    # Verify the reel is publicly accessible
    # ------------------------------------------------------------------
    print("\nVerifying public Reel URL...")
    try:
        verify_public_resource_url(reel_url)
        print("Reel URL is publicly accessible.")
    except requests.HTTPError as exc:
        print(
            f"\nReel URL returned HTTP {exc.response.status_code}.\n"
            "Make sure reel.mp4 has been committed and pushed to the "
            "resources repository, then rerun.\n"
            f"Expected path in resources repo: ig/posts/days/{day}/reel/reel.mp4"
        )
        sys.exit(1)
    except requests.RequestException as exc:
        print(f"Failed to verify public Reel URL: {exc}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------
    print("\nPublishing Reel via GitHub URL...")
    try:
        media_id = publisher.publish_reel(reel_url, caption)
        record_published(day, media_id)
        print("\nReel published successfully!")
        print(f"   Media ID : {media_id}")
        print(f"   Logged to: {PUBLISHED_LOG}")
    except Exception as exc:
        print(f"\nFailed to publish Reel: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
