"""Instagram media publishing via the Graph API."""

from __future__ import annotations

import time

import requests

from app import config


def create_media_container(image_url: str, caption: str) -> str:
    """Create a single-image Instagram media container."""
    print("Creating single image media container...")

    url = f"{config.API_BASE_URL}/{config.API_VERSION}/{config.IG_ID}/media"
    params = {
        "image_url": image_url,
        "caption": caption,
        "access_token": config.IG_ACCESS_TOKEN,
    }

    response = requests.post(url, params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    container_id = response.json()["id"]
    print(f"Media container created: {container_id}")
    return container_id


def create_carousel_child(image_url: str) -> str:
    """Create an unpublished media container for use as a carousel child."""
    print(f"Creating carousel child: {image_url}")

    url = f"{config.API_BASE_URL}/{config.API_VERSION}/{config.IG_ID}/media"
    params = {
        "image_url": image_url,
        "is_carousel_item": "true",
        "access_token": config.IG_ACCESS_TOKEN,
    }

    response = requests.post(url, params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    container_id = response.json()["id"]
    print(f"Carousel child created: {container_id}")
    return container_id


def create_carousel_container(child_container_ids: list[str], caption: str) -> str:
    """Create the parent carousel container."""
    print("Creating carousel container...")

    url = f"{config.API_BASE_URL}/{config.API_VERSION}/{config.IG_ID}/media"
    params = {
        "media_type": "CAROUSEL",
        "children": ",".join(child_container_ids),
        "caption": caption,
        "access_token": config.IG_ACCESS_TOKEN,
    }

    response = requests.post(url, params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    container_id = response.json()["id"]
    print(f"Carousel container created: {container_id}")
    return container_id


def wait_until_ready(
    container_id: str,
    max_attempts: int | None = None,
    delay_seconds: int | None = None,
) -> None:
    """Wait until Instagram finishes processing a media container."""
    attempts = max_attempts if max_attempts is not None else config.POLL_MAX_ATTEMPTS
    delay = delay_seconds if delay_seconds is not None else config.POLL_DELAY_SECONDS

    print(f"Waiting for container {container_id}...")

    url = f"{config.API_BASE_URL}/{config.API_VERSION}/{container_id}"
    params = {
        "fields": "status_code",
        "access_token": config.IG_ACCESS_TOKEN,
    }

    for attempt in range(1, attempts + 1):
        response = requests.get(url, params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()

        status_code = response.json().get("status_code", "UNKNOWN")
        print(f"Attempt {attempt}/{attempts}: {status_code}")

        if status_code == "FINISHED":
            return

        if status_code == "ERROR":
            raise RuntimeError(
                f"Media container {container_id} failed with status ERROR."
            )

        if status_code == "EXPIRED":
            raise RuntimeError(
                f"Media container {container_id} expired before publishing."
            )

        if attempt < attempts:
            time.sleep(delay)

    raise TimeoutError(
        f"Media container {container_id} did not reach FINISHED status "
        f"after {attempts} attempts."
    )


def publish_media(container_id: str) -> str:
    """Publish a ready Instagram media container."""
    print("Publishing media...")

    url = f"{config.API_BASE_URL}/{config.API_VERSION}/{config.IG_ID}/media_publish"
    params = {
        "creation_id": container_id,
        "access_token": config.IG_ACCESS_TOKEN,
    }

    response = requests.post(url, params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    media_id = response.json()["id"]
    print("Post published successfully.")
    print(f"Media ID: {media_id}")
    return media_id


def publish_image(image_url: str, caption: str) -> str:
    """Publish one image as one Instagram post."""
    container_id = create_media_container(image_url, caption)
    wait_until_ready(container_id)
    return publish_media(container_id)


def publish_carousel(image_urls: list[str], caption: str) -> str:
    """Publish multiple images as one Instagram carousel post."""
    if len(image_urls) < 2:
        raise ValueError("A carousel requires at least 2 images.")

    print(f"Creating carousel with {len(image_urls)} images...")

    child_container_ids: list[str] = []

    for index, image_url in enumerate(image_urls, start=1):
        print(f"\nCreating carousel item {index}/{len(image_urls)}")
        child_id = create_carousel_child(image_url)
        wait_until_ready(child_id)
        child_container_ids.append(child_id)

    carousel_container_id = create_carousel_container(child_container_ids, caption)
    wait_until_ready(carousel_container_id)
    return publish_media(carousel_container_id)


def create_reel_container(video_url: str, caption: str) -> str:
    """Create an Instagram Reel media container."""
    print("Creating Reel media container...")

    url = f"{config.API_BASE_URL}/{config.API_VERSION}/{config.IG_ID}/media"
    params = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": config.IG_ACCESS_TOKEN,
    }

    response = requests.post(url, params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    container_id = response.json()["id"]
    print(f"Reel container created: {container_id}")
    return container_id


def publish_reel(video_url: str, caption: str) -> str:
    """Publish a Reel from a publicly accessible video URL."""
    container_id = create_reel_container(video_url, caption)
    wait_until_ready(
        container_id,
        max_attempts=config.REEL_POLL_MAX_ATTEMPTS,
        delay_seconds=config.REEL_POLL_DELAY_SECONDS,
    )
    return publish_media(container_id)
