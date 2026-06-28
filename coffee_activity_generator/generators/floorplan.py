"""Cafe floorplan puzzle generator.

Example:
    python -m coffee_activity_generator.generators.floorplan --seed 42 --difficulty hard
"""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

from ..common import Artwork, Circle, Label, Rect, StrokePath, seeded_rng
from ..render import export_artwork

Difficulty = Literal["easy", "medium", "hard"]


@dataclass(slots=True)
class PointObj:
    x: float
    y: float


@dataclass(slots=True)
class TableObj:
    center: PointObj
    radius: float
    occupied: bool
    has_laptop_user: bool


@dataclass(slots=True)
class OutletObj:
    pos: PointObj
    available: bool


@dataclass(slots=True)
class FloorplanPuzzleData:
    difficulty: Difficulty
    entrance: PointObj
    nearest_available_outlet: PointObj
    shortest_path: list[tuple[int, int]]
    tables: list[TableObj]
    outlets: list[OutletObj]


@dataclass(slots=True)
class FloorplanGenerationResult:
    puzzle: FloorplanPuzzleData
    svg_path: Path
    png_path: Path

    def __iter__(self) -> Iterator[Path]:
        yield self.svg_path
        yield self.png_path


def _distance(a: PointObj, b: PointObj) -> float:
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


def _rect_overlap(ax: float, ay: float, aw: float, ah: float, bx: float, by: float, bw: float, bh: float) -> bool:
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


def _draw_window(art: Artwork, x1: float, y1: float, x2: float, y2: float) -> None:
    art.paths.append(StrokePath([(x1, y1), (x2, y2)], width=3.0))
    if abs(x1 - x2) < 1e-6:
        art.paths.append(StrokePath([(x1 + 0.007, y1), (x2 + 0.007, y2)], width=1.5))
    else:
        art.paths.append(StrokePath([(x1, y1 + 0.007), (x2, y2 + 0.007)], width=1.5))


def _draw_door(art: Artwork, x: float, y: float, w: float, h: float) -> PointObj:
    # Door opening on left wall with an inward swing arc.
    art.paths.append(StrokePath([(x, y), (x, y + h)], width=4.0))
    art.paths.append(StrokePath([(x, y), (x + w, y + h * 0.5), (x, y + h)], width=1.5))
    return PointObj(x + w * 1.15, y + h * 0.5)


def _draw_counter(art: Artwork, x: float, y: float, w: float, h: float) -> None:
    art.rects.append(Rect(x, y, w, h, width=3.0))
    art.labels.append(Label((x + w * 0.5, y + h * 0.55), "COUNTER", size=11, anchor="middle"))


def _draw_plant(art: Artwork, x: float, y: float, size: float) -> None:
    art.rects.append(Rect(x - size * 0.18, y + size * 0.08, size * 0.36, size * 0.20, width=2.2))
    art.paths.append(StrokePath([(x, y - size * 0.30), (x - size * 0.10, y), (x, y + size * 0.06)], width=2.2))
    art.paths.append(StrokePath([(x, y - size * 0.30), (x + size * 0.10, y), (x, y + size * 0.06)], width=2.2))


def _draw_person(art: Artwork, x: float, y: float, scale: float = 1.0, laptop: bool = False, label: str | None = None) -> None:
    head_r = 0.0075 * scale
    art.circles.append(Circle((x, y - 0.012 * scale), head_r, width=2.0))
    art.paths.append(StrokePath([(x, y - 0.004 * scale), (x, y + 0.016 * scale)], width=2.0))
    art.paths.append(StrokePath([(x - 0.010 * scale, y + 0.006 * scale), (x + 0.010 * scale, y + 0.006 * scale)], width=2.0))
    if laptop:
        art.rects.append(Rect(x + 0.008 * scale, y + 0.002 * scale, 0.016 * scale, 0.010 * scale, width=1.8))
    if label:
        art.labels.append(Label((x, y + 0.030 * scale), label, size=8, anchor="middle"))


def _draw_table_with_chairs(art: Artwork, table: TableObj) -> None:
    cx, cy, r = table.center.x, table.center.y, table.radius
    art.circles.append(Circle((cx, cy), r, width=2.6))

    chair_offset = r * 1.5
    chair_r = r * 0.26
    chair_pts = [
        (cx, cy - chair_offset),
        (cx + chair_offset, cy),
        (cx, cy + chair_offset),
        (cx - chair_offset, cy),
    ]
    for px, py in chair_pts:
        art.circles.append(Circle((px, py), chair_r, width=1.8))

    if table.occupied:
        _draw_person(art, cx - r * 0.2, cy + r * 0.1, scale=0.9, laptop=table.has_laptop_user, label="CUSTOMER")
        if table.has_laptop_user:
            art.labels.append(Label((cx, cy + r * 1.55), "LAPTOP", size=8, anchor="middle"))


def _draw_outlet(art: Artwork, outlet: OutletObj) -> None:
    x, y = outlet.pos.x, outlet.pos.y
    art.rects.append(Rect(x - 0.010, y - 0.008, 0.020, 0.016, width=2.0))
    art.circles.append(Circle((x - 0.004, y), 0.0018, width=1.3))
    art.circles.append(Circle((x + 0.004, y), 0.0018, width=1.3))
    if not outlet.available:
        art.paths.append(StrokePath([(x - 0.012, y - 0.010), (x + 0.012, y + 0.010)], width=2.0))
        art.paths.append(StrokePath([(x - 0.012, y + 0.010), (x + 0.012, y - 0.010)], width=2.0))


def _build_blocked_grid(
    width_cells: int,
    height_cells: int,
    room_left: float,
    room_top: float,
    room_right: float,
    room_bottom: float,
    counter_rect: tuple[float, float, float, float],
    tables: list[TableObj],
) -> list[list[bool]]:
    blocked = [[False for _ in range(width_cells)] for _ in range(height_cells)]
    cell_w = (room_right - room_left) / width_cells
    cell_h = (room_bottom - room_top) / height_cells

    cx, cy, cw, ch = counter_rect
    for gy in range(height_cells):
        py = room_top + (gy + 0.5) * cell_h
        for gx in range(width_cells):
            px = room_left + (gx + 0.5) * cell_w
            if cx <= px <= cx + cw and cy <= py <= cy + ch:
                blocked[gy][gx] = True

    for table in tables:
        if not table.occupied:
            continue
        for gy in range(height_cells):
            py = room_top + (gy + 0.5) * cell_h
            for gx in range(width_cells):
                if blocked[gy][gx]:
                    continue
                px = room_left + (gx + 0.5) * cell_w
                dist = ((px - table.center.x) ** 2 + (py - table.center.y) ** 2) ** 0.5
                if dist <= table.radius * 1.45:
                    blocked[gy][gx] = True

    return blocked


def _to_grid(x: float, y: float, left: float, top: float, right: float, bottom: float, gw: int, gh: int) -> tuple[int, int]:
    gx = int((x - left) / (right - left) * gw)
    gy = int((y - top) / (bottom - top) * gh)
    return max(0, min(gw - 1, gx)), max(0, min(gh - 1, gy))


def _bfs_shortest_path(blocked: list[list[bool]], start: tuple[int, int], target: tuple[int, int]) -> list[tuple[int, int]]:
    gh, gw = len(blocked), len(blocked[0])
    q: deque[tuple[int, int]] = deque([start])
    parent: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    moves = [(1, 0), (-1, 0), (0, 1), (0, -1)]

    while q:
        x, y = q.popleft()
        if (x, y) == target:
            break
        for dx, dy in moves:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < gw and 0 <= ny < gh):
                continue
            if blocked[ny][nx] or (nx, ny) in parent:
                continue
            parent[(nx, ny)] = (x, y)
            q.append((nx, ny))

    if target not in parent:
        return []

    path = [target]
    cur = target
    while parent[cur] is not None:
        cur = parent[cur]  # type: ignore[assignment]
        path.append(cur)
    path.reverse()
    return path


def _generate_layout(
    seed: int | None,
    difficulty: Difficulty,
) -> tuple[
    list[TableObj],
    list[OutletObj],
    tuple[float, float, float, float],
    PointObj,
    PointObj,
    list[tuple[int, int]],
]:
    rng = seeded_rng(seed)

    room_left, room_top, room_right, room_bottom = 0.10, 0.18, 0.92, 0.92
    counter_rect = (0.61, 0.20, 0.27, 0.15)

    difficulty_cfg = {
        "easy": {"tables": 6, "occupied_ratio": 0.35, "laptop_ratio": 0.35, "occupied_outlets": 1},
        "medium": {"tables": 8, "occupied_ratio": 0.50, "laptop_ratio": 0.45, "occupied_outlets": 2},
        "hard": {"tables": 10, "occupied_ratio": 0.65, "laptop_ratio": 0.60, "occupied_outlets": 3},
    }[difficulty]

    tables: list[TableObj] = []
    max_tables = int(difficulty_cfg["tables"])

    for _ in range(max_tables * 25):
        if len(tables) >= max_tables:
            break
        r = float(rng.uniform(0.028, 0.038))
        cx = float(rng.uniform(room_left + 0.07, room_right - 0.07))
        cy = float(rng.uniform(room_top + 0.12, room_bottom - 0.07))

        if _rect_overlap(cx - r * 1.9, cy - r * 1.9, r * 3.8, r * 3.8, *counter_rect):
            continue
        if any(_distance(PointObj(cx, cy), t.center) < (r + t.radius) * 2.2 for t in tables):
            continue

        occupied = bool(rng.random() < float(difficulty_cfg["occupied_ratio"]))
        has_laptop_user = occupied and bool(rng.random() < float(difficulty_cfg["laptop_ratio"]))
        tables.append(TableObj(center=PointObj(cx, cy), radius=r, occupied=occupied, has_laptop_user=has_laptop_user))

    outlets = [
        OutletObj(PointObj(room_left + 0.005, room_top + 0.22), True),
        OutletObj(PointObj(room_left + 0.005, room_top + 0.50), True),
        OutletObj(PointObj(room_right - 0.005, room_top + 0.30), True),
        OutletObj(PointObj(room_right - 0.005, room_top + 0.62), True),
        OutletObj(PointObj(room_left + 0.36, room_bottom - 0.005), True),
    ]

    outlet_indices = list(range(len(outlets)))
    rng.shuffle(outlet_indices)
    for idx in outlet_indices[: int(difficulty_cfg["occupied_outlets"])]:
        outlets[idx].available = False

    entrance = PointObj(room_left + 0.03, room_top + 0.62)

    grid_w, grid_h = 96, 126
    blocked = _build_blocked_grid(grid_w, grid_h, room_left, room_top, room_right, room_bottom, counter_rect, tables)

    start = _to_grid(entrance.x, entrance.y, room_left, room_top, room_right, room_bottom, grid_w, grid_h)
    blocked[start[1]][start[0]] = False

    best_path: list[tuple[int, int]] = []
    nearest_available = PointObj(outlets[0].pos.x, outlets[0].pos.y)
    for outlet in outlets:
        if not outlet.available:
            continue
        target = _to_grid(outlet.pos.x, outlet.pos.y, room_left, room_top, room_right, room_bottom, grid_w, grid_h)
        blocked[target[1]][target[0]] = False
        p = _bfs_shortest_path(blocked, start, target)
        if not p:
            continue
        if not best_path or len(p) < len(best_path):
            best_path = p
            nearest_available = outlet.pos

    if not best_path:
        # Guaranteed fallback in case random placement traps all outlets.
        nearest_available = PointObj(room_right - 0.005, room_top + 0.30)
        outlets[2].available = True
        target = _to_grid(nearest_available.x, nearest_available.y, room_left, room_top, room_right, room_bottom, grid_w, grid_h)
        blocked[target[1]][target[0]] = False
        best_path = _bfs_shortest_path(blocked, start, target)

    return tables, outlets, counter_rect, entrance, nearest_available, best_path


def generate_floorplan(
    seed: int | None,
    output_dir: Path,
    difficulty: Difficulty = "medium",
    title: str = "Coffee Shop Floorplan",
) -> FloorplanGenerationResult:
    """Generate a random top-down coffee shop shortest-path puzzle page."""

    if difficulty not in {"easy", "medium", "hard"}:
        raise ValueError("difficulty must be one of: easy, medium, hard")

    tables, outlets, counter_rect, entrance, nearest_outlet, best_path = _generate_layout(seed=seed, difficulty=difficulty)

    room_left, room_top, room_right, room_bottom = 0.10, 0.18, 0.92, 0.92
    art = Artwork(title=title, subtitle="Route puzzle")

    art.labels.append(Label((0.5, 0.08), title, size=18, anchor="middle"))
    art.labels.append(
        Label(
            (0.5, 0.115),
            "Find the shortest path from the entrance to the nearest available outlet, avoiding occupied tables.",
            size=10,
            anchor="middle",
        )
    )
    art.labels.append(Label((0.5, 0.145), f"Difficulty: {difficulty.upper()}", size=10, anchor="middle"))

    # Room boundary.
    art.rects.append(Rect(room_left, room_top, room_right - room_left, room_bottom - room_top, width=3.2))

    # Windows on top and right walls.
    _draw_window(art, room_left + 0.08, room_top, room_left + 0.24, room_top)
    _draw_window(art, room_left + 0.30, room_top, room_left + 0.48, room_top)
    _draw_window(art, room_right, room_top + 0.14, room_right, room_top + 0.30)
    _draw_window(art, room_right, room_top + 0.40, room_right, room_top + 0.56)

    # Door and entrance marker.
    entrance = _draw_door(art, room_left, room_top + 0.56, 0.028, 0.12)
    art.labels.append(Label((room_left + 0.02, room_top + 0.71), "DOOR", size=9))
    art.labels.append(Label((entrance.x + 0.03, entrance.y - 0.01), "ENTRANCE", size=9))

    # Counter and barista.
    _draw_counter(art, *counter_rect)
    _draw_person(art, counter_rect[0] + counter_rect[2] * 0.5, counter_rect[1] + counter_rect[3] + 0.03, scale=1.05, label="BARISTA")

    # Plants.
    _draw_plant(art, room_left + 0.06, room_top + 0.10, 0.05)
    _draw_plant(art, room_right - 0.08, room_bottom - 0.08, 0.05)

    # Tables, chairs, customers, and laptop users.
    for table in tables:
        _draw_table_with_chairs(art, table)

    # Outlets and availability markers.
    for outlet in outlets:
        _draw_outlet(art, outlet)
    art.labels.append(Label((room_right - 0.13, room_bottom + 0.025), "X = occupied outlet", size=8))

    stem = f"floorplan_{difficulty}"
    svg_path, png_path = export_artwork(art, stem, output_dir)

    puzzle = FloorplanPuzzleData(
        difficulty=difficulty,
        entrance=entrance,
        nearest_available_outlet=nearest_outlet,
        shortest_path=best_path,
        tables=tables,
        outlets=outlets,
    )
    return FloorplanGenerationResult(puzzle=puzzle, svg_path=svg_path, png_path=png_path)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Generate a random coffee shop floorplan puzzle.")
    parser.add_argument("--seed", type=int, default=7, help="Random seed for reproducibility")
    parser.add_argument("--output-dir", type=Path, default=Path("coffee_activity_generator/exports"))
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], default="medium")
    parser.add_argument("--title", default="Coffee Shop Floorplan", help="Title displayed above the puzzle")
    args = parser.parse_args()

    result = generate_floorplan(args.seed, args.output_dir, difficulty=args.difficulty, title=args.title)
    print(f"SVG: {result.svg_path}")
    print(f"PNG: {result.png_path}")
    print(
        "Puzzle: "
        f"difficulty={result.puzzle.difficulty}, "
        f"tables={len(result.puzzle.tables)}, "
        f"path_steps={len(result.puzzle.shortest_path)}"
    )


if __name__ == "__main__":
    _main()
