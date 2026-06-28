"""Coffee process flowchart generator.

Example:
    python -m coffee_activity_generator.generators.coffee_flow --seed 42
"""

from __future__ import annotations

from pathlib import Path

from ..cli import run_generator_cli
from ..common import Artwork, Label, Rect, StrokePath, add_department_header, jittered_line, seeded_rng
from ..render import export_artwork


STEPS = ["Beans", "Grind", "Brew", "Serve"]


def generate_coffee_flow(seed: int | None, output_dir: Path) -> tuple[Path, Path]:
    """Generate a fill-in-the-blank coffee workflow diagram."""

    rng = seeded_rng(seed)
    art = Artwork(title="Coffee Flow", subtitle="Complete the process diagram")
    add_department_header(art)

    y = 0.45
    x_positions = [0.12, 0.32, 0.52, 0.72]

    for x, step in zip(x_positions, STEPS, strict=False):
        art.rects.append(Rect(x, y, 0.16, 0.10, width=2.0))
        art.labels.append(Label((x + 0.08, y + 0.055), step if step != "Brew" else "_____", size=13, anchor="middle"))

    for i in range(len(x_positions) - 1):
        p1 = (x_positions[i] + 0.16, y + 0.05)
        p2 = (x_positions[i + 1], y + 0.05)
        art.paths.append(StrokePath(jittered_line(p1, p2, rng)))
        art.paths.append(StrokePath(jittered_line((p2[0] - 0.01, p2[1] - 0.01), p2, rng), width=1.5))
        art.paths.append(StrokePath(jittered_line((p2[0] - 0.01, p2[1] + 0.01), p2, rng), width=1.5))

    art.labels.append(Label((0.5, 0.72), "Write a better verb than 'Brew' for step 3.", size=12, anchor="middle"))
    art.labels.append(Label((0.5, 0.76), "Bonus: add one quality-control checkpoint.", size=12, anchor="middle"))
    return export_artwork(art, "coffee_flow", output_dir)


if __name__ == "__main__":
    run_generator_cli("coffee-flow", "Generate the coffee process flowchart.", generate_coffee_flow)
