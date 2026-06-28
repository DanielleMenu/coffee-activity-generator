"""Seat selection logic puzzle generator.

Example:
    python -m coffee_activity_generator.generators.seat_selection --seed 42
"""

from __future__ import annotations

from pathlib import Path

from ..cli import run_generator_cli
from ..common import Artwork, Circle, Label, Rect, add_department_header, seeded_rng
from ..render import export_artwork


def generate_seat_selection(seed: int | None, output_dir: Path) -> tuple[Path, Path]:
    """Generate a seating optimization puzzle for cafe visitors."""

    rng = seeded_rng(seed)
    art = Artwork(title="Seat Selection", subtitle="Choose the best table for each mission")
    add_department_header(art)

    cols, rows = 3, 4
    x0, y0, dx, dy = 0.18, 0.22, 0.23, 0.15
    seat_id = 1

    for r in range(rows):
        for c in range(cols):
            tx = x0 + c * dx
            ty = y0 + r * dy
            art.rects.append(Rect(tx, ty, 0.14, 0.08, width=1.8))
            for sx, sy in [(tx - 0.02, ty + 0.02), (tx + 0.16, ty + 0.02), (tx - 0.02, ty + 0.06), (tx + 0.16, ty + 0.06)]:
                art.circles.append(Circle((sx, sy), 0.012, width=1.4))
            art.labels.append(Label((tx + 0.07, ty - 0.01), f"T{seat_id}", size=10, anchor="middle"))
            seat_id += 1

    clues = [
        "1) Best for stroller + quick exit",
        "2) Best for laptop + outlet",
        "3) Best for gossip + low queue noise",
        "4) Worst if you dislike espresso aroma",
    ]
    for i, clue in enumerate(clues):
        art.labels.append(Label((0.08, 0.86 + i * 0.03), clue, size=11))

    # Tiny imperfections keep shapes from looking machine-sterile.
    for rect in art.rects:
        rect.x += float(rng.normal(0.0, 0.001))
        rect.y += float(rng.normal(0.0, 0.001))

    return export_artwork(art, "seat_selection", output_dir)


if __name__ == "__main__":
    run_generator_cli("seat-selection", "Generate the cafe seat selection puzzle.", generate_seat_selection)
