"""Maze activity generator.

Example:
    python -m coffee_activity_generator.generators.maze --seed 42
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx

from ..cli import run_generator_cli
from ..common import Artwork, Circle, Label, StrokePath, add_department_header, jittered_line, seeded_rng
from ..render import export_artwork


def _maze_passages(rows: int, cols: int, seed: int | None) -> set[frozenset[tuple[int, int]]]:
    """Build a randomized DFS spanning-tree maze using NetworkX adjacency."""

    rng = seeded_rng(seed)
    graph = nx.grid_2d_graph(rows, cols)
    start = (0, 0)
    stack = [start]
    visited = {start}
    passages: set[frozenset[tuple[int, int]]] = set()

    while stack:
        node = stack[-1]
        options = [n for n in graph.neighbors(node) if n not in visited]
        if not options:
            stack.pop()
            continue
        nxt = options[int(rng.integers(0, len(options)))]
        passages.add(frozenset((node, nxt)))
        visited.add(nxt)
        stack.append(nxt)

    return passages


def generate_maze(seed: int | None, output_dir: Path) -> tuple[Path, Path]:
    """Generate a coffee-themed printable maze.

    Args:
        seed: Random seed for reproducibility.
        output_dir: Destination folder.

    Returns:
        Tuple with SVG and PNG paths.
    """

    rows, cols = 12, 8
    rng = seeded_rng(seed)
    passages = _maze_passages(rows, cols, seed)

    art = Artwork(title="Maze 01: Espresso Escape", subtitle="Help the bean reach the perfect cup")
    add_department_header(art)

    x0, y0, x1, y1 = 0.08, 0.17, 0.92, 0.93
    cw = (x1 - x0) / cols
    ch = (y1 - y0) / rows

    for r in range(rows):
        for c in range(cols):
            if r == 0:
                art.paths.append(StrokePath(jittered_line((x0 + c * cw, y0), (x0 + (c + 1) * cw, y0), rng)))
            if c == 0:
                art.paths.append(StrokePath(jittered_line((x0, y0 + r * ch), (x0, y0 + (r + 1) * ch), rng)))

            if r < rows - 1 and frozenset(((r, c), (r + 1, c))) not in passages:
                art.paths.append(
                    StrokePath(jittered_line((x0 + c * cw, y0 + (r + 1) * ch), (x0 + (c + 1) * cw, y0 + (r + 1) * ch), rng))
                )
            if c < cols - 1 and frozenset(((r, c), (r, c + 1))) not in passages:
                art.paths.append(
                    StrokePath(jittered_line((x0 + (c + 1) * cw, y0 + r * ch), (x0 + (c + 1) * cw, y0 + (r + 1) * ch), rng))
                )

    art.paths.append(StrokePath(jittered_line((x0, y1), (x1, y1), rng)))
    art.paths.append(StrokePath(jittered_line((x1, y0), (x1, y1), rng)))

    art.circles.append(Circle((x0 + cw * 0.5, y0 + ch * 0.5), 0.012))
    art.circles.append(Circle((x1 - cw * 0.5, y1 - ch * 0.5), 0.012))
    art.labels.extend(
        [
            Label((x0 + 0.01, y0 - 0.012), "START", size=12),
            Label((x1 - 0.01, y1 + 0.02), "FINISH", size=12, anchor="end"),
        ]
    )

    return export_artwork(art, "maze", output_dir)


if __name__ == "__main__":
    run_generator_cli("maze", "Generate the Espresso Escape maze.", generate_maze)
