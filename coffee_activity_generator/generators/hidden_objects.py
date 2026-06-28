"""Hidden objects puzzle generator.

Example:
    python -m coffee_activity_generator.generators.hidden_objects --seed 42
"""

from __future__ import annotations

from pathlib import Path

from ..cli import run_generator_cli
from ..common import Artwork, Circle, Label, Rect, StrokePath, add_department_header, jittered_line, seeded_rng
from ..render import export_artwork


OBJECTS = ["bean", "spoon", "cup", "straw", "sugar"]


def _draw_icon(art: Artwork, kind: str, x: float, y: float, rng_seed: int) -> None:
    rng = seeded_rng(rng_seed)
    if kind == "bean":
        art.circles.append(Circle((x, y), 0.016, width=1.5))
        art.paths.append(StrokePath(jittered_line((x - 0.01, y + 0.01), (x + 0.01, y - 0.01), rng), width=1.2))
    elif kind == "spoon":
        art.circles.append(Circle((x - 0.012, y), 0.01, width=1.4))
        art.paths.append(StrokePath([(x - 0.002, y), (x + 0.02, y)], width=1.6))
    elif kind == "cup":
        art.rects.append(Rect(x - 0.015, y - 0.01, 0.03, 0.02, width=1.4))
        art.circles.append(Circle((x + 0.019, y), 0.007, width=1.2))
    elif kind == "straw":
        art.paths.append(StrokePath([(x - 0.015, y + 0.01), (x + 0.015, y - 0.015)], width=1.6))
    elif kind == "sugar":
        art.rects.append(Rect(x - 0.012, y - 0.012, 0.024, 0.024, width=1.2))


def generate_hidden_objects(seed: int | None, output_dir: Path) -> tuple[Path, Path]:
    """Generate a cafe clutter scene with hidden target objects."""

    rng = seeded_rng(seed)
    art = Artwork(title="Hidden Objects", subtitle="Find the five official lab artifacts")
    add_department_header(art)

    for i in range(80):
        x = float(rng.uniform(0.10, 0.90))
        y = float(rng.uniform(0.20, 0.88))
        kind = OBJECTS[int(rng.integers(0, len(OBJECTS)))]
        _draw_icon(art, kind, x, y, rng_seed=(seed or 0) + i)

    for i, kind in enumerate(OBJECTS):
        art.labels.append(Label((0.08, 0.90 + i * 0.02), f"Find: {kind}", size=11))

    return export_artwork(art, "hidden_objects", output_dir)


if __name__ == "__main__":
    run_generator_cli("hidden-objects", "Generate the hidden objects puzzle.", generate_hidden_objects)
