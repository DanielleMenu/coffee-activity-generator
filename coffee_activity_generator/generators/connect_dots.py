"""Connect-the-dots activity generator.

Example:
    python -m coffee_activity_generator.generators.connect_dots --seed 42
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..cli import run_generator_cli
from ..common import Artwork, Circle, Label, add_department_header, seeded_rng
from ..render import export_artwork


def _cup_outline_points(samples: int = 44) -> np.ndarray:
    """Return ordered points approximating a coffee cup silhouette."""

    top = np.column_stack((np.linspace(0.28, 0.72, samples // 4), np.full(samples // 4, 0.28)))
    right = np.column_stack((np.full(samples // 4, 0.72), np.linspace(0.28, 0.66, samples // 4)))
    bottom = np.column_stack((np.linspace(0.72, 0.28, samples // 4), np.full(samples // 4, 0.66)))
    left = np.column_stack((np.full(samples // 4, 0.28), np.linspace(0.66, 0.28, samples // 4)))
    handle_t = np.linspace(0.0, np.pi, samples // 8)
    handle = np.column_stack((0.74 + 0.08 * np.cos(handle_t), 0.45 + 0.12 * np.sin(handle_t)))
    steam_t = np.linspace(0.0, 1.0, samples // 8)
    steam = np.column_stack((0.47 + 0.05 * np.sin(steam_t * np.pi * 2.4), 0.22 - 0.11 * steam_t))
    return np.vstack((top, right, bottom, left, handle, steam))


def generate_connect_dots(seed: int | None, output_dir: Path) -> tuple[Path, Path]:
    """Generate a numbered connect-the-dots puzzle in line-art style."""

    rng = seeded_rng(seed)
    pts = _cup_outline_points(56)
    pts += rng.normal(0.0, 0.002, size=pts.shape)

    art = Artwork(title="Connect the Dots", subtitle="Reveal the classified beverage prototype")
    add_department_header(art)

    for idx, (x, y) in enumerate(pts, start=1):
        art.circles.append(Circle((float(x), float(y)), 0.006, width=1.5))
        if idx % 2 == 0:
            art.labels.append(Label((float(x) + 0.01, float(y) - 0.008), str(idx), size=9))

    art.labels.append(Label((0.5, 0.90), "Connect 1 -> 56, then color only with imagination.", size=12, anchor="middle"))
    return export_artwork(art, "connect_dots", output_dir)


if __name__ == "__main__":
    run_generator_cli("connect-dots", "Generate the coffee connect-the-dots page.", generate_connect_dots)
