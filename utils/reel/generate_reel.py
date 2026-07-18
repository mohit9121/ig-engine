"""Generate an Instagram Reel-style MP4 from ordered images and one MP3."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

IMAGE_PATTERN = re.compile(
    r"^image_(\d+)\.(jpg|jpeg|png|webp)$",
    re.IGNORECASE,
)

IMAGE_DURATION_SECONDS = 5.0
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
FPS = 30
VIDEO_CRF = 20
VIDEO_PRESET = "medium"
AUDIO_BITRATE = "192k"
AUDIO_FADE_SECONDS = 0.5

FFMPEG_INSTALL_HINT = "Install FFmpeg on macOS with: brew install ffmpeg"


def find_images(day_folder: Path) -> list[Path]:
    """Discover image_<number> files and return them sorted numerically."""
    matches: list[tuple[int, Path]] = []
    seen_numbers: dict[int, Path] = {}

    for path in day_folder.iterdir():
        if not path.is_file():
            continue

        match = IMAGE_PATTERN.match(path.name)
        if not match:
            continue

        number = int(match.group(1))
        if number in seen_numbers:
            raise ValueError(
                f"Duplicate image sequence number {number}: "
                f"{seen_numbers[number].name} and {path.name}"
            )

        seen_numbers[number] = path
        matches.append((number, path))

    if not matches:
        raise ValueError(
            f"No image_<number> files found in {day_folder}. "
            "Expected names like image_1.jpg, image_2.png, etc."
        )

    matches.sort(key=lambda item: item[0])
    return [path for _, path in matches]


def find_audio(day_folder: Path) -> Path:
    """Return the single MP3 file in the day folder."""
    mp3_files = sorted(
        path
        for path in day_folder.iterdir()
        if path.is_file() and path.suffix.lower() == ".mp3"
    )

    if not mp3_files:
        raise ValueError(f"No MP3 file found in {day_folder}.")

    if len(mp3_files) > 1:
        names = ", ".join(path.name for path in mp3_files)
        raise ValueError(
            f"Expected exactly one MP3 file in {day_folder}, "
            f"but found {len(mp3_files)}: {names}. "
            "Keep only one MP3 in the folder."
        )

    return mp3_files[0]


def check_ffmpeg() -> None:
    """Ensure FFmpeg is available on PATH."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "FFmpeg is not installed or not available on PATH.\n"
            f"{FFMPEG_INSTALL_HINT}"
        )


def get_audio_duration(audio_path: Path) -> float:
    """Return the duration of an audio file in seconds."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise RuntimeError(
            "ffprobe is not available on PATH.\n"
            f"{FFMPEG_INSTALL_HINT}"
        )

    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to read audio duration for {audio_path.name}:\n"
            f"{result.stderr.strip()}"
        )

    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(
            f"Could not parse audio duration for {audio_path.name}."
        ) from exc


def build_video_filter(image_count: int) -> str:
    """Build the FFmpeg filter graph for scaling, padding, and concatenation."""
    scale_pad = (
        f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:"
        "force_original_aspect_ratio=decrease,"
        f"pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1,fps={FPS},format=yuv420p"
    )

    parts = [f"[{index}:v]{scale_pad}[v{index}]" for index in range(image_count)]
    concat_inputs = "".join(f"[v{index}]" for index in range(image_count))
    parts.append(f"{concat_inputs}concat=n={image_count}:v=1:a=0[vout]")
    return ";".join(parts)


def build_audio_filter(audio_input_index: int, video_duration: float) -> str:
    """Build the FFmpeg filter graph for trimming, looping, and fade-out."""
    fade_duration = min(AUDIO_FADE_SECONDS, video_duration)
    fade_start = max(0.0, video_duration - fade_duration)

    return (
        f"[{audio_input_index}:a]"
        f"atrim=0:{video_duration},"
        "asetpts=PTS-STARTPTS,"
        f"afade=t=out:st={fade_start}:d={fade_duration}[aout]"
    )


def resolve_image_durations(
    image_count: int,
    image_duration: float | None = None,
    image_durations: list[float] | None = None,
) -> list[float]:
    """Resolve per-image durations from a uniform value or an explicit list."""
    if image_durations is not None:
        if len(image_durations) != image_count:
            raise ValueError(
                f"Expected {image_count} image durations, got {len(image_durations)}."
            )
        if any(duration <= 0 for duration in image_durations):
            raise ValueError("All image durations must be greater than 0.")
        return image_durations

    if image_duration is None:
        image_duration = IMAGE_DURATION_SECONDS

    if image_duration <= 0:
        raise ValueError("image_duration must be greater than 0.")

    return [image_duration] * image_count


def generate_reel(
    images: list[Path],
    audio_path: Path,
    output_path: Path,
    image_duration: float | None = None,
    image_durations: list[float] | None = None,
) -> None:
    """Generate a Reel-style MP4 from ordered images and background audio."""
    durations = resolve_image_durations(
        len(images),
        image_duration=image_duration,
        image_durations=image_durations,
    )
    video_duration = sum(durations)
    audio_duration = get_audio_duration(audio_path)
    loop_audio = audio_duration < video_duration

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]

    for image, duration in zip(images, durations):
        cmd.extend(["-loop", "1", "-t", str(duration), "-i", str(image)])

    if loop_audio:
        cmd.extend(["-stream_loop", "-1"])

    audio_input_index = len(images)
    cmd.extend(["-i", str(audio_path)])

    filter_complex = (
        f"{build_video_filter(len(images))};"
        f"{build_audio_filter(audio_input_index, video_duration)}"
    )

    cmd.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-t",
            str(video_duration),
            "-c:v",
            "libx264",
            "-crf",
            str(VIDEO_CRF),
            "-preset",
            VIDEO_PRESET,
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            AUDIO_BITRATE,
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        stderr = result.stderr.strip() or "Unknown FFmpeg error."
        raise RuntimeError(f"FFmpeg failed to generate reel:\n{stderr}")

    if not output_path.is_file():
        raise RuntimeError(
            f"FFmpeg finished but output file was not created: {output_path}"
        )


def validate_day_folder(path: Path) -> Path:
    """Validate that the input path exists and is a directory."""
    resolved = path.expanduser().resolve()

    if not resolved.exists():
        raise FileNotFoundError(f"Input folder does not exist: {path}")

    if not resolved.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {path}")

    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate an Instagram Reel-style MP4 from ordered images and one MP3."
        )
    )
    parser.add_argument(
        "day_folder",
        type=Path,
        help="Path to the day folder containing image_N files and one MP3",
    )
    parser.add_argument(
        "--image-duration",
        type=float,
        default=IMAGE_DURATION_SECONDS,
        help=f"Seconds each image is shown (default: {IMAGE_DURATION_SECONDS:g})",
    )
    args = parser.parse_args()

    if args.image_duration <= 0:
        print("Error: --image-duration must be greater than 0.", file=sys.stderr)
        sys.exit(1)

    try:
        print("Reel Generator")
        print("-" * 32)

        day_folder = validate_day_folder(args.day_folder)
        check_ffmpeg()

        images = find_images(day_folder)
        audio = find_audio(day_folder)
        output_path = day_folder / "reel" / "reel.mp4"
        video_duration = len(images) * args.image_duration

        print(f"\nInput folder:\n{day_folder}\n")
        print(f"Images found: {len(images)}\n")
        for index, image in enumerate(images, start=1):
            print(f"{index}. {image.name}")

        print(f"\nAudio:\n{audio.name}\n")
        print(f"Duration per image:\n{args.image_duration:g} seconds\n")
        print(f"Expected video duration:\n{video_duration:g} seconds\n")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        print("Generating reel...\n")
        generate_reel(images, audio, output_path, args.image_duration)

        print("Reel generated successfully!\n")
        print(f"Output:\n{output_path}")

    except (FileNotFoundError, NotADirectoryError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
