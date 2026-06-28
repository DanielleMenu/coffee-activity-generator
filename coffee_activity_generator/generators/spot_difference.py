"""Spot-the-difference puzzle generator.

Example:
    python -m coffee_activity_generator.generators.spot_difference --seed 42
"""

from __future__ import annotations

from pathlib import Path

from ..cli import run_generator_cli
from ..common import Artwork, Circle, Label, Rect, StrokePath, add_department_header, seeded_rng
from ..render import export_artwork


def _panel_scene(art: Artwork, x0: float, y0: float, mutate: bool = False) -> None:
    art.rects.append(Rect(x0, y0, 0.36, 0.30, width=1.8))
    art.rects.append(Rect(x0 + 0.06, y0 + 0.14, 0.10, 0.08, width=1.4))
    art.rects.append(Rect(x0 + 0.21, y0 + 0.12, 0.09, 0.10, width=1.4))
    art.circles.append(Circle((x0 + 0.12, y0 + 0.12), 0.018, width=1.4))
    art.circles.append(Circle((x0 + 0.25, y0 + 0.09), 0.014, width=1.4))
    art.paths.append(StrokePath([(x0 + 0.04, y0 + 0.27), (x0 + 0.32, y0 + 0.27)], width=1.4))

    if mutate:
        art.circles[-1].radius = 0.009
        art.rects[-1].h = 0.07
        art.paths[-1].points[1] = (x0 + 0.30, y0 + 0.25)


def generate_spot_difference(seed: int | None, output_dir: Path) -> tuple[Path, Path]:
    """Generate a two-panel puzzle with subtle visual differences."""

    _ = seeded_rng(seed)
    art = Artwork(title="Spot the Difference", subtitle="Find 3 suspicious lab inconsistencies")
    add_department_header(art)

    _panel_scene(art, 0.08, 0.28, mutate=False)
    _panel_scene(art, 0.56, 0.28, mutate=True)

    art.labels.append(Label((0.26, 0.24), "A", size=15, anchor="middle"))
    art.labels.append(Label((0.74, 0.24), "B", size=15, anchor="middle"))
    art.labels.append(Label((0.5, 0.66), "Circle all differences between panel A and B.", size=12, anchor="middle"))

    return export_artwork(art, "spot_difference", output_dir)


if __name__ == "__main__":
    run_generator_cli("spot-difference", "Generate the spot-the-difference puzzle.", generate_spot_difference)
