"""Queue logic puzzle generator.

Example:
    python -m coffee_activity_generator.generators.queue_logic --seed 42
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx

from ..cli import run_generator_cli
from ..common import Artwork, Circle, Label, StrokePath, add_department_header, jittered_line, seeded_rng
from ..render import export_artwork


def generate_queue_logic(seed: int | None, output_dir: Path) -> tuple[Path, Path]:
    """Generate a queue decision graph puzzle using NetworkX."""

    rng = seeded_rng(seed)
    art = Artwork(title="Queue Logic", subtitle="Who gets coffee first?")
    add_department_header(art)

    graph = nx.DiGraph()
    graph.add_edges_from(
        [
            ("A", "C"),
            ("B", "C"),
            ("C", "D"),
            ("B", "E"),
            ("E", "F"),
            ("D", "F"),
        ]
    )

    pos = {
        "A": (0.20, 0.28),
        "B": (0.20, 0.52),
        "C": (0.42, 0.40),
        "D": (0.62, 0.32),
        "E": (0.62, 0.58),
        "F": (0.82, 0.45),
    }

    for node, (x, y) in pos.items():
        art.circles.append(Circle((x, y), 0.03, width=1.8))
        art.labels.append(Label((x, y), node, size=14, anchor="middle"))

    for src, dst in graph.edges:
        p1 = pos[src]
        p2 = pos[dst]
        art.paths.append(StrokePath(jittered_line(p1, p2, rng), width=1.8))

    art.labels.append(Label((0.5, 0.80), "Rule: arrows show dependency. Solve a valid serving order.", size=12, anchor="middle"))
    art.labels.append(Label((0.5, 0.84), "Write one topological ordering below:", size=12, anchor="middle"))
    art.paths.append(StrokePath([(0.20, 0.88), (0.80, 0.88)], width=1.6))
    return export_artwork(art, "queue_logic", output_dir)


if __name__ == "__main__":
    run_generator_cli("queue-logic", "Generate the queue logic puzzle.", generate_queue_logic)
