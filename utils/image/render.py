"""Brand-styled text image renderer for KuchAurTha posts."""

from __future__ import annotations

from pathlib import Path
from textwrap import fill

import matplotlib.pyplot as plt
import numpy as np

STYLES = {
    "documentary": {
        "description": (
            "Signature cinematic storytelling. "
            "History, biographies, business case studies."
        ),
        "background": ("#081C2E", "#163D63"),
        "accent": "#F6C453",
        "text_color": "#FFFFFF",
        "overlay": 0.35,
        "font_size": 34,
        "text_width": 24,
        "line_spacing": 1.45,
        "accent_line": True,
        "gradient": "vertical",
        "vignette": True,
    },
    "editorial": {
        "description": (
            "Magazine inspired. Psychology, philosophy, "
            "essays and premium educational content."
        ),
        "background": ("#F8F5EF", "#EAE4D8"),
        "accent": "#B8860B",
        "text_color": "#202020",
        "overlay": 0.0,
        "font_size": 34,
        "text_width": 26,
        "line_spacing": 1.55,
        "accent_line": True,
        "gradient": "vertical",
        "vignette": False,
    },
    "cinematic": {
        "description": (
            "Movie poster aesthetic. Mystery, space, war and emotional stories."
        ),
        "background": ("#050505", "#2C2C2C"),
        "accent": "#D62828",
        "text_color": "#FFFFFF",
        "overlay": 0.45,
        "font_size": 40,
        "text_width": 22,
        "line_spacing": 1.35,
        "accent_line": False,
        "gradient": "radial",
        "vignette": True,
    },
    "minimal": {
        "description": "Clean educational style. Facts, quotes and explainers.",
        "background": ("#FFFFFF", "#F4F4F4"),
        "accent": "#111111",
        "text_color": "#111111",
        "overlay": 0.0,
        "font_size": 34,
        "text_width": 28,
        "line_spacing": 1.55,
        "accent_line": False,
        "gradient": "vertical",
        "vignette": False,
    },
}

DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1350


def hex_to_rgb(color: str) -> np.ndarray:
    color = color.lstrip("#")
    return (
        np.array(
            [
                int(color[0:2], 16),
                int(color[2:4], 16),
                int(color[4:6], 16),
            ]
        )
        / 255
    )


def scene_text_to_string(text: dict | str) -> str:
    """Normalize scene text into a single renderable string."""
    if isinstance(text, str):
        return text.strip()

    lines = [
        str(text[key]).strip()
        for key in ("line_1", "line_2", "line_3")
        if key in text and str(text[key]).strip()
    ]
    return "\n".join(lines)


def render(
    image_spec: dict,
    output_path: Path | str,
    *,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> Path:
    """Render a styled text image and save it to ``output_path``."""
    style_name = image_spec["style"]
    if style_name not in STYLES:
        raise ValueError(
            f"Unknown style '{style_name}'. "
            f"Expected one of: {', '.join(sorted(STYLES))}."
        )

    style = STYLES[style_name]
    text = scene_text_to_string(image_spec["text"])
    if not text:
        raise ValueError("Image text is empty.")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    top = hex_to_rgb(style["background"][0])
    bottom = hex_to_rgb(style["background"][1])

    gradient = np.zeros((height, width, 3))

    if style["gradient"] == "vertical":
        for y in range(height):
            ratio = y / (height - 1)
            gradient[y, :, :] = top * (1 - ratio) + bottom * ratio
    else:
        y, x = np.ogrid[-1:1:height * 1j, -1:1:width * 1j]
        radius = np.sqrt(x * x + y * y)
        radius = np.clip(radius, 0, 1)
        for channel in range(3):
            gradient[:, :, channel] = top[channel] * (1 - radius) + bottom[channel] * radius

    fig = plt.figure(figsize=(width / 135, height / 135), dpi=135)
    ax = plt.axes([0, 0, 1, 1])
    ax.imshow(gradient)
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)
    ax.axis("off")

    if style["overlay"] > 0:
        ax.imshow(
            np.zeros((height, width)),
            cmap="gray",
            alpha=style["overlay"],
            extent=[0, width, height, 0],
        )

    if style["accent_line"]:
        line_width = 170
        accent_y = int(height * 0.185)
        ax.plot(
            [width / 2 - line_width / 2, width / 2 + line_width / 2],
            [accent_y, accent_y],
            lw=6,
            color=style["accent"],
            solid_capstyle="round",
        )

    wrapped = fill(text.replace("\n", " "), width=style["text_width"])
    # Preserve intentional scene line breaks when both lines are short.
    if "\n" in text:
        wrapped = "\n".join(
            fill(line, width=style["text_width"]) for line in text.splitlines()
        )

    ax.text(
        width / 2,
        height / 2,
        wrapped,
        fontsize=style["font_size"],
        color=style["text_color"],
        ha="center",
        va="center",
        linespacing=style["line_spacing"],
        fontweight="bold",
    )

    fig.savefig(
        output,
        dpi=135,
        bbox_inches="tight",
        pad_inches=0,
    )
    plt.close(fig)

    if not output.is_file():
        raise RuntimeError(f"Failed to write rendered image: {output}")

    return output
