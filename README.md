# IG Engine

A lightweight Python-based Instagram content publishing engine.

The long-term goal is to build a modular system capable of:

**Content Generation → Content Rendering → Resource Storage → Scheduling → Instagram Publishing → Analytics**

V1 currently only handles:

**Existing images → Public GitHub raw URLs → Instagram API → Automated publishing**

## Architecture

```
Content Generator (Future)
        ↓
Image Renderer (Future)
        ↓
Resources Repository
        ↓
Instagram Publisher
        ↓
Instagram
```

## Two-Repository Setup

This project uses two separate Git repositories:

1. **`ig-engine`** — Private repository containing application code.
2. **`resources`** — Public repository containing generated/public media assets.

The `resources/` directory is a nested Git repository cloned inside `ig-engine/`. The parent repository ignores it so each repo is managed independently.

### Why is `resources` public?

Instagram's API must fetch images from a publicly accessible URL. The engine converts local resource paths into raw GitHub URLs that Instagram can download directly.

## Resources Structure

Images are organized by date:

```
resources/
└── ig/
    └── posts/
        └── days/
            └── YYYY-MM-DD/
                ├── image_1.jpg
                ├── image_2.jpg
                ├── background.mp3
                └── reel/
                    └── reel.mp4
```

For example, images for July 17, 2026 live in:

```
resources/ig/posts/days/2026-07-17/
```

These map to raw GitHub URLs like:

```
https://raw.githubusercontent.com/mohit9121/resources/main/ig/posts/days/2026-07-17/image_1.jpg
```

## Environment Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
IG_ID=...
IG_ACCESS_TOKEN=...
```

**Never commit `.env` or expose Instagram access tokens.**

## Resource Generation vs Publishing

Resource generation and Instagram publishing are intentionally separate:

```
Batch Resource Generation
        ↓
Manual Review
        ↓
Manual Git Push (resources repo)
        ↓
Daily Automated Publishing
```

**Generation** creates local assets (images, Reels) under `resources/`. **Publishing** only consumes assets that already exist locally and are publicly available on GitHub.

| Task | Command |
|------|---------|
| Generate Reel (local MP4) | `python -m utils.reel.generate_reel <day-folder>` |
| Publish carousel / image | `python main.py` |
| Publish Reel | `python publish_reel.py` |

## How to Run

**Publish today's carousel or image:**

```bash
python main.py
```

**Publish today's Reel:**

```bash
python publish_reel.py
```

Both commands discover today's date automatically and expect resources under `resources/ig/posts/days/YYYY-MM-DD/`. They convert local paths to raw GitHub URLs before calling the Instagram API.

## Reel Generator

A standalone utility under `utils/reel/` that creates a local Instagram Reel-style MP4 from ordered images and one background MP3.

It does **not** use Instagram credentials, call the Instagram API, upload to GitHub, or publish anything. You generate the video locally, then manually commit and push it to the `resources` repository if needed.

### Prerequisites

1. **Python** — use the same virtual environment as the rest of the project (no extra pip packages required).
2. **FFmpeg** — must be installed and available on `PATH`.

```bash
brew install ffmpeg
```

Verify installation:

```bash
ffmpeg -version
```

### Input folder convention

Prepare a day folder inside `resources/` with numbered images and exactly one MP3:

```
resources/ig/posts/days/2026-07-17/
├── image_1.jpg
├── image_2.jpg
├── image_3.jpg
└── background.mp3
```

**Images**

- Filenames must match `image_<number>.<ext>`
- Supported extensions: `.jpg`, `.jpeg`, `.png`, `.webp`
- Sorted **numerically** by the number (`image_2` before `image_10`, not lexicographically)
- Duplicate numbers (e.g. two `image_1` files) are rejected

**Audio**

- Exactly **one** `.mp3` file in the day folder
- Any filename is fine (e.g. `background.mp3`)

### How to generate a reel

From the **project root** (`ig-engine/`):

```bash
source .venv/bin/activate
python -m utils.reel.generate_reel resources/ig/posts/days/2026-07-17
```

Replace the path with your target day folder.

**Custom slide duration** (default is 5 seconds per image):

```bash
python -m utils.reel.generate_reel \
    resources/ig/posts/days/2026-07-17 \
    --image-duration 7
```

**Help**

```bash
python -m utils.reel.generate_reel --help
```

### What gets created

The utility creates (or overwrites) output inside the same day folder:

```
resources/ig/posts/days/2026-07-17/
├── image_1.jpg
├── image_2.jpg
├── background.mp3
└── reel/
    └── reel.mp4
```

Source images and the MP3 are **not** modified, moved, or deleted.

**Video specs**

| Setting | Value |
|---------|-------|
| Resolution | 1080 × 1920 (9:16) |
| Format | MP4 |
| Video codec | H.264 |
| Audio codec | AAC |
| Slide duration | 5 seconds per image (configurable) |

Images are scaled to fit inside the frame without distortion, centered on a black background (letterboxing). Hard cuts between slides — no transitions in V1.

**Audio behavior**

- Audio starts at the beginning of the video
- If the MP3 is longer than the video, it is trimmed
- If the MP3 is shorter than the video, it is looped to fill the duration

**Duration example**

| Images | Duration per image | Video length |
|--------|-------------------|--------------|
| 2 | 5 s | ~10 s |
| 3 | 5 s | ~15 s |
| 3 | 7 s | ~21 s |

### Example output

On success, the utility prints something like:

```
Reel Generator
--------------------------------

Input folder:
.../resources/ig/posts/days/2026-07-17

Images found: 2

1. image_1.jpg
2. image_2.jpg

Audio:
background.mp3

Duration per image:
5 seconds

Expected video duration:
10 seconds

Generating reel...

Reel generated successfully!

Output:
.../resources/ig/posts/days/2026-07-17/reel/reel.mp4
```

### After generation

The Reel Generator only creates a local file. To publish it:

1. Review `reel/reel.mp4` locally
2. Commit and push it from the `resources` repository
3. Run `python publish_reel.py` to publish today's Reel to Instagram

### Common errors

| Error | Cause |
|-------|-------|
| FFmpeg not installed | Run `brew install ffmpeg` |
| No matching images | Missing or misnamed `image_<number>` files |
| No MP3 / multiple MP3s | Folder must contain exactly one `.mp3` |
| Duplicate image numbers | Two files share the same `image_<number>` prefix |

## Current Workflow

1. Add images to today's folder in the `resources` repository.
2. Commit and push those images to the public `resources` repository on GitHub.
3. Run `python main.py`.
4. IG Engine discovers today's images from the local `resources/` clone.
5. It converts local paths to raw GitHub URLs.
6. It creates Instagram media containers.
7. It waits for processing to finish.
8. It publishes each image as a separate post.

## Current Limitations

- Caption is currently hardcoded.
- Each image is published as a separate post.
- No carousel support yet.
- No content generation yet.
- No scheduler yet.
- No automatic Git commit/push for resources yet.
- No database or publishing history yet.

## Planned Architecture

| Version | Feature |
|---------|---------|
| V1 | Image publishing |
| V2 | Carousel publishing |
| V3 | Content/image renderer |
| V4 | AI content generation |
| V5 | Scheduler |
| V6 | Publishing history/database |
| V7 | Analytics and feedback loop |

The goal is to keep modules decoupled so that generators, renderers, publishers, and storage backends can be replaced independently.
