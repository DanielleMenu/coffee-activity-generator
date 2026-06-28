"""Maze activity generator.

Example:
    python -m coffee_activity_generator.generators.maze --seed 42 --width 16 --height 24 --difficulty hard
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

from ..common import Artwork, Label, StrokePath, seeded_rng
from ..render import export_artwork

Difficulty = Literal["easy", "medium", "hard"]
Cell = tuple[int, int]
Edge = frozenset[Cell]


@dataclass(slots=True)
class MazeData:
    """Structured maze output with cell graph and wall segments."""

    width: int
    height: int
    difficulty: Difficulty
    seed: int | None
    start: Cell
    finish: Cell
    passages: set[Edge]
    walls: list[tuple[tuple[float, float], tuple[float, float]]]


@dataclass(slots=True)
class MazeGenerationResult:
    """Return object exposing maze data and exported file paths.

    Iteration yields SVG and PNG paths for backward compatibility with
    existing code that unpacks the return value into two variables.
    """

    maze: MazeData
    svg_path: Path
    png_path: Path

    def __iter__(self) -> Iterator[Path]:
        yield self.svg_path
        yield self.png_path


def _neighbors(cell: Cell, width: int, height: int) -> list[Cell]:
    x, y = cell
    out: list[Cell] = []
    if x > 0:
        out.append((x - 1, y))
    if x < width - 1:
        out.append((x + 1, y))
    if y > 0:
        out.append((x, y - 1))
    if y < height - 1:
        out.append((x, y + 1))
    return out


def _recursive_backtracking_maze(
    width: int,
    height: int,
    rng_seed: int | None,
    difficulty: Difficulty,
) -> set[Edge]:
    """Generate a maze graph with recursive backtracking (iterative stack form)."""

    rng = seeded_rng(rng_seed)
    start = (0, 0)
    stack = [start]
    visited = {start}
    passages: set[Edge] = set()

    while stack:
        current = stack[-1]
        candidates = [n for n in _neighbors(current, width, height) if n not in visited]
        if not candidates:
            stack.pop()
            continue
        nxt = candidates[int(rng.integers(0, len(candidates)))]
        passages.add(frozenset((current, nxt)))
        visited.add(nxt)
        stack.append(nxt)

    extra_open_rate = {"easy": 0.12, "medium": 0.06, "hard": 0.0}[difficulty]
    if extra_open_rate > 0.0:
        for y in range(height):
            for x in range(width):
                for neighbor in _neighbors((x, y), width, height):
                    edge = frozenset(((x, y), neighbor))
                    if edge in passages:
                        continue
                    if int(rng.integers(0, 10_000)) < int(extra_open_rate * 10_000):
                        passages.add(edge)

    return passages


def _build_walls(
    width: int,
    height: int,
    passages: set[Edge],
    left: float,
    top: float,
    right: float,
    bottom: float,
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Return line segments for every closed wall in normalized page coordinates."""

    walls: list[tuple[tuple[float, float], tuple[float, float]]] = []
    cell_w = (right - left) / width
    cell_h = (bottom - top) / height

    for y in range(height):
        for x in range(width):
            if y == 0:
                walls.append(((left + x * cell_w, top), (left + (x + 1) * cell_w, top)))
            if x == 0:
                walls.append(((left, top + y * cell_h), (left, top + (y + 1) * cell_h)))

            if y < height - 1 and frozenset(((x, y), (x, y + 1))) not in passages:
                walls.append(
                    (
                        (left + x * cell_w, top + (y + 1) * cell_h),
                        (left + (x + 1) * cell_w, top + (y + 1) * cell_h),
                    )
                )
            if x < width - 1 and frozenset(((x, y), (x + 1, y))) not in passages:
                walls.append(
                    (
                        (left + (x + 1) * cell_w, top + y * cell_h),
                        (left + (x + 1) * cell_w, top + (y + 1) * cell_h),
                    )
                )

    walls.append(((left, bottom), (right, bottom)))
    walls.append(((right, top), (right, bottom)))
    return walls


def _draw_start_arrow(art: Artwork, x: float, y: float, size: float) -> None:
    art.paths.append(StrokePath([(x, y), (x + size * 1.2, y)], width=5.0))
    art.paths.append(StrokePath([(x + size * 1.2, y), (x + size * 0.75, y - size * 0.4)], width=5.0))
    art.paths.append(StrokePath([(x + size * 1.2, y), (x + size * 0.75, y + size * 0.4)], width=5.0))


def _draw_finish_cup(art: Artwork, cx: float, cy: float, size: float) -> None:
    half_w = size * 0.55
    half_h = size * 0.33
    left = cx - half_w
    right = cx + half_w
    top = cy - half_h
    bottom = cy + half_h

    art.paths.append(StrokePath([(left, top), (right, top), (right, bottom), (left, bottom), (left, top)], width=4.5))
    art.paths.append(StrokePath([(right, cy - size * 0.12), (right + size * 0.22, cy - size * 0.12), (right + size * 0.22, cy + size * 0.12), (right, cy + size * 0.12)], width=4.5))
    art.paths.append(StrokePath([(cx, top - size * 0.12), (cx, top - size * 0.32)], width=3.5))


def generate_maze(
    seed: int | None,
    output_dir: Path,
    width: int = 12,
    height: int = 16,
    difficulty: Difficulty = "medium",
    title: str = "Espresso Escape Maze",
    subtitle: str = "Help the freelancer reach the last available outlet.",
) -> MazeGenerationResult:
    """Generate a printable maze and export SVG/PNG files.

    Returns maze graph data and output file paths in a compatibility-friendly
    result object that can still be unpacked as ``svg_path, png_path``.
    """

    if width < 3 or height < 3:
        raise ValueError("Maze width and height must be at least 3.")
    if difficulty not in {"easy", "medium", "hard"}:
        raise ValueError("difficulty must be one of: easy, medium, hard")

    passages = _recursive_backtracking_maze(width, height, seed, difficulty)
    start: Cell = (0, 0)
    finish: Cell = (width - 1, height - 1)

    # 0.5 inch margin on 6x9 pages in normalized coordinates.
    margin_x = 0.5 / 6.0
    margin_y = 0.5 / 9.0
    maze_left = margin_x
    maze_right = 1.0 - margin_x
    title_y = margin_y + 0.015
    maze_top = margin_y + 0.13
    maze_bottom = 1.0 - margin_y

    art = Artwork(title=title, subtitle=subtitle)
    art.labels.append(Label((0.5, title_y), title, size=20, anchor="middle"))

    walls = _build_walls(width, height, passages, maze_left, maze_top, maze_right, maze_bottom)
    for p1, p2 in walls:
        art.paths.append(StrokePath([p1, p2], width=5.0))

    cell_w = (maze_right - maze_left) / width
    cell_h = (maze_bottom - maze_top) / height

    start_cx = maze_left + 0.5 * cell_w
    start_cy = maze_top + 0.5 * cell_h
    finish_cx = maze_left + (width - 0.5) * cell_w
    finish_cy = maze_top + (height - 0.5) * cell_h

    _draw_start_arrow(art, maze_left + 0.015, start_cy, size=min(cell_w, cell_h) * 0.55)
    _draw_finish_cup(art, finish_cx, finish_cy, size=min(cell_w, cell_h) * 0.60)

    stem = f"maze_{difficulty}_{width}x{height}"
    svg_path, png_path = export_artwork(art, stem, output_dir)

    maze_data = MazeData(
        width=width,
        height=height,
        difficulty=difficulty,
        seed=seed,
        start=start,
        finish=finish,
        passages=passages,
        walls=walls,
    )
    return MazeGenerationResult(maze=maze_data, svg_path=svg_path, png_path=png_path)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Generate a coffee-themed maze page.")
    parser.add_argument("--seed", type=int, default=7, help="Random seed for reproducibility")
    parser.add_argument("--output-dir", type=Path, default=Path("coffee_activity_generator/exports"))
    parser.add_argument("--width", type=int, default=12, help="Maze width in cells")
    parser.add_argument("--height", type=int, default=16, help="Maze height in cells")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], default="medium")
    parser.add_argument("--title", default="Espresso Escape Maze", help="Title shown above the maze")
    parser.add_argument(
        "--subtitle",
        default="Help the freelancer reach the last available outlet.",
        help="Subtitle/instruction line shown below the title",
    )
    args = parser.parse_args()

    result = generate_maze(
        seed=args.seed,
        output_dir=args.output_dir,
        width=args.width,
        height=args.height,
        difficulty=args.difficulty,
        title=args.title,
        subtitle=args.subtitle,
    )
    print(f"SVG: {result.svg_path}")
    print(f"PNG: {result.png_path}")
    print(
        "Maze: "
        f"{result.maze.width}x{result.maze.height}, "
        f"difficulty={result.maze.difficulty}, "
        f"passages={len(result.maze.passages)}"
    )


if __name__ == "__main__":
    _main()
