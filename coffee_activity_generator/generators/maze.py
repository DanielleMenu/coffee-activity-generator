"""Maze activity generator.

Example:
    python -m coffee_activity_generator.generators.maze --seed 42 --width 16 --height 24 --difficulty hard
"""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

from ..common import Artwork, Label, StrokePath, seeded_rng
from ..render import export_artwork

Difficulty = Literal["easy", "medium", "hard"]
MazeShape = Literal["coffee-cup", "rectangle"]
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


def _coffee_cup_mask(width: int, height: int) -> set[Cell]:
    """Build a coarse coffee-cup silhouette over the logical grid."""

    valid: set[Cell] = set()
    for y in range(height):
        for x in range(width):
            nx = (x + 0.5) / width
            ny = (y + 0.5) / height

            cup_body = 0.18 <= nx <= 0.74 and 0.28 <= ny <= 0.80
            top_band = 0.16 <= nx <= 0.76 and 0.22 <= ny <= 0.30
            base_band = 0.24 <= nx <= 0.68 and 0.80 <= ny <= 0.88

            dx = nx - 0.82
            dy = ny - 0.54
            handle_outer = dx * dx + dy * dy <= 0.18 * 0.18
            handle_inner = dx * dx + dy * dy <= 0.10 * 0.10
            handle = handle_outer and not handle_inner and nx >= 0.72 and 0.34 <= ny <= 0.74

            bridge = 0.70 <= nx <= 0.78 and 0.45 <= ny <= 0.63
            if cup_body or top_band or base_band or handle or bridge:
                valid.add((x, y))
    return valid


def _largest_connected_component(valid_cells: set[Cell], width: int, height: int) -> set[Cell]:
    if not valid_cells:
        return set()

    unseen = set(valid_cells)
    largest: set[Cell] = set()
    while unseen:
        start = next(iter(unseen))
        q: deque[Cell] = deque([start])
        comp: set[Cell] = {start}
        unseen.remove(start)

        while q:
            cur = q.popleft()
            for nxt in _neighbors(cur, width, height):
                if nxt not in unseen:
                    continue
                unseen.remove(nxt)
                comp.add(nxt)
                q.append(nxt)

        if len(comp) > len(largest):
            largest = comp

    return largest


def _recursive_backtracking_maze(
    width: int,
    height: int,
    rng_seed: int | None,
    difficulty: Difficulty,
    valid_cells: set[Cell],
    start: Cell,
) -> set[Edge]:
    """Generate a maze graph with recursive backtracking (iterative stack form)."""

    rng = seeded_rng(rng_seed)
    stack = [start]
    visited = {start}
    passages: set[Edge] = set()

    while stack:
        current = stack[-1]
        candidates = [n for n in _neighbors(current, width, height) if n in valid_cells and n not in visited]
        if not candidates:
            stack.pop()
            continue
        nxt = candidates[int(rng.integers(0, len(candidates)))]
        passages.add(frozenset((current, nxt)))
        visited.add(nxt)
        stack.append(nxt)

    all_adjacent_edges: list[Edge] = []
    for x, y in valid_cells:
        for neighbor in _neighbors((x, y), width, height):
            if neighbor not in valid_cells:
                continue
            if (x, y) < neighbor:
                all_adjacent_edges.append(frozenset(((x, y), neighbor)))

    degree: dict[Cell, int] = {cell: 0 for cell in valid_cells}
    for edge in passages:
        a, b = tuple(edge)
        degree[a] += 1
        degree[b] += 1

    def _junction_count() -> int:
        return sum(1 for c in valid_cells if degree[c] >= 3)

    target_junction_ratio = {
        "easy": 0.10,
        "medium": 0.18,
        "hard": 0.26,
    }[difficulty]
    target_junctions = max(2, int(len(valid_cells) * target_junction_ratio))
    max_extra_edges = {
        "easy": int(len(valid_cells) * 0.10),
        "medium": int(len(valid_cells) * 0.18),
        "hard": int(len(valid_cells) * 0.28),
    }[difficulty]

    rng.shuffle(all_adjacent_edges)
    added = 0
    for edge in all_adjacent_edges:
        if edge in passages:
            continue
        if added >= max_extra_edges or _junction_count() >= target_junctions:
            break

        a, b = tuple(edge)
        if degree[a] >= 2 or degree[b] >= 2 or int(rng.integers(0, 100)) < 20:
            passages.add(edge)
            degree[a] += 1
            degree[b] += 1
            added += 1

    return passages


def _build_walls(
    width: int,
    height: int,
    valid_cells: set[Cell],
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

    for x, y in valid_cells:
        # Top wall
        top_neighbor = (x, y - 1)
        if top_neighbor not in valid_cells or frozenset(((x, y), top_neighbor)) not in passages:
            walls.append(
                (
                    (left + x * cell_w, top + y * cell_h),
                    (left + (x + 1) * cell_w, top + y * cell_h),
                )
            )

        # Left wall
        left_neighbor = (x - 1, y)
        if left_neighbor not in valid_cells or frozenset(((x, y), left_neighbor)) not in passages:
            walls.append(
                (
                    (left + x * cell_w, top + y * cell_h),
                    (left + x * cell_w, top + (y + 1) * cell_h),
                )
            )

        # Bottom wall
        bottom_neighbor = (x, y + 1)
        if bottom_neighbor not in valid_cells or frozenset(((x, y), bottom_neighbor)) not in passages:
            walls.append(
                (
                    (left + x * cell_w, top + (y + 1) * cell_h),
                    (left + (x + 1) * cell_w, top + (y + 1) * cell_h),
                )
            )

        # Right wall
        right_neighbor = (x + 1, y)
        if right_neighbor not in valid_cells or frozenset(((x, y), right_neighbor)) not in passages:
            walls.append(
                (
                    (left + (x + 1) * cell_w, top + y * cell_h),
                    (left + (x + 1) * cell_w, top + (y + 1) * cell_h),
                )
            )

    return walls


def _pick_start_finish(valid_cells: set[Cell]) -> tuple[Cell, Cell]:
    """Choose a left-most start and right-most finish within the shape."""

    start = min(valid_cells, key=lambda c: (c[0], c[1]))
    finish = max(valid_cells, key=lambda c: (c[0], -c[1]))
    return start, finish


def _open_wall_for_cell(
    walls: list[tuple[tuple[float, float], tuple[float, float]]],
    cell: Cell,
    direction: str,
    left: float,
    top: float,
    cell_w: float,
    cell_h: float,
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Remove one boundary wall segment for an opening at a specific cell side."""

    x, y = cell
    if direction == "left":
        target = ((left + x * cell_w, top + y * cell_h), (left + x * cell_w, top + (y + 1) * cell_h))
    elif direction == "right":
        target = (
            (left + (x + 1) * cell_w, top + y * cell_h),
            (left + (x + 1) * cell_w, top + (y + 1) * cell_h),
        )
    elif direction == "top":
        target = ((left + x * cell_w, top + y * cell_h), (left + (x + 1) * cell_w, top + y * cell_h))
    else:  # bottom
        target = (
            (left + x * cell_w, top + (y + 1) * cell_h),
            (left + (x + 1) * cell_w, top + (y + 1) * cell_h),
        )

    def _same_segment(a: tuple[tuple[float, float], tuple[float, float]], b: tuple[tuple[float, float], tuple[float, float]]) -> bool:
        eps = 1e-9

        def _pt_eq(p: tuple[float, float], q: tuple[float, float]) -> bool:
            return abs(p[0] - q[0]) < eps and abs(p[1] - q[1]) < eps

        return (_pt_eq(a[0], b[0]) and _pt_eq(a[1], b[1])) or (_pt_eq(a[0], b[1]) and _pt_eq(a[1], b[0]))

    return [seg for seg in walls if not _same_segment(seg, target)]


def _opening_direction(cell: Cell, valid_cells: set[Cell], preferred: tuple[str, ...]) -> str:
    x, y = cell
    candidates = {
        "left": (x - 1, y),
        "right": (x + 1, y),
        "top": (x, y - 1),
        "bottom": (x, y + 1),
    }
    for direction in preferred:
        if candidates[direction] not in valid_cells:
            return direction
    for direction, neighbor in candidates.items():
        if neighbor not in valid_cells:
            return direction
    return preferred[0]


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
    shape: MazeShape = "coffee-cup",
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
    if shape not in {"coffee-cup", "rectangle"}:
        raise ValueError("shape must be one of: coffee-cup, rectangle")

    if shape == "coffee-cup":
        valid_cells = _largest_connected_component(_coffee_cup_mask(width, height), width, height)
    else:
        valid_cells = {(x, y) for y in range(height) for x in range(width)}
    if not valid_cells:
        raise RuntimeError("Maze shape produced no valid cells.")

    start, finish = _pick_start_finish(valid_cells)
    passages = _recursive_backtracking_maze(width, height, seed, difficulty, valid_cells, start)

    # 0.5 inch margin on 6x9 pages in normalized coordinates.
    margin_x = 0.5 / 6.0
    margin_y = 0.5 / 9.0
    maze_left = margin_x
    maze_right = 1.0 - margin_x
    title_y = margin_y + 0.015
    maze_top = margin_y + 0.13
    maze_bottom = 1.0 - margin_y

    art = Artwork(title=title, subtitle=subtitle)

    walls = _build_walls(width, height, valid_cells, passages, maze_left, maze_top, maze_right, maze_bottom)

    # Open explicit entry/exit gaps on shape boundaries.
    entry_dir = _opening_direction(start, valid_cells, preferred=("left", "top", "bottom", "right"))
    exit_dir = _opening_direction(finish, valid_cells, preferred=("right", "top", "bottom", "left"))
    walls = _open_wall_for_cell(walls, start, entry_dir, maze_left, maze_top, cell_w=(maze_right - maze_left) / width, cell_h=(maze_bottom - maze_top) / height)
    walls = _open_wall_for_cell(walls, finish, exit_dir, maze_left, maze_top, cell_w=(maze_right - maze_left) / width, cell_h=(maze_bottom - maze_top) / height)

    for p1, p2 in walls:
        art.paths.append(StrokePath([p1, p2], width=5.0))

    cell_w = (maze_right - maze_left) / width
    cell_h = (maze_bottom - maze_top) / height

    start_cx = maze_left + (start[0] + 0.5) * cell_w
    start_cy = maze_top + (start[1] + 0.5) * cell_h
    finish_cx = maze_left + (finish[0] + 0.5) * cell_w
    finish_cy = maze_top + (finish[1] + 0.5) * cell_h

    # Intentionally render only maze walls (no titles/icons/markers).

    stem = f"maze_{shape}_{difficulty}_{width}x{height}"
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
    parser.add_argument("--shape", choices=["coffee-cup", "rectangle"], default="coffee-cup", help="Maze silhouette")
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
        shape=args.shape,
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
