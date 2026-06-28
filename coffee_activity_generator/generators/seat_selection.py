"""Seat selection logic puzzle generator.

Example:
    python -m coffee_activity_generator.generators.seat_selection --seed 42 --difficulty medium
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

from ..common import Artwork, Circle, Label, Rect, StrokePath, seeded_rng
from ..render import export_artwork

Mission = Literal[
    "Need silence",
    "Need sunlight",
    "Need power outlet",
    "Need people watching",
    "Need to leave quickly",
    "Need privacy",
]
Difficulty = Literal["easy", "medium", "hard"]

MISSIONS: list[Mission] = [
    "Need silence",
    "Need sunlight",
    "Need power outlet",
    "Need people watching",
    "Need to leave quickly",
    "Need privacy",
]


@dataclass(slots=True)
class ZoneRect:
    x: float
    y: float
    w: float
    h: float

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h


@dataclass(slots=True)
class Seat:
    seat_id: str
    x: float
    y: float
    available: bool
    near_window: bool
    near_outlet: bool
    in_noisy_zone: bool
    in_quiet_zone: bool
    near_traffic: bool
    privacy_score: float


@dataclass(slots=True)
class SeatSelectionPuzzleData:
    mission: Mission
    difficulty: Difficulty
    seats: list[Seat]
    correct_seat_id: str
    score_by_seat_id: dict[str, float]


@dataclass(slots=True)
class SeatSelectionResult:
    puzzle: SeatSelectionPuzzleData
    svg_path: Path
    png_path: Path

    def __iter__(self) -> Iterator[Path]:
        yield self.svg_path
        yield self.png_path


def _dist(ax: float, ay: float, bx: float, by: float) -> float:
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5


def _draw_zone_box(art: Artwork, z: ZoneRect, label: str) -> None:
    art.rects.append(Rect(z.x, z.y, z.w, z.h, width=1.5))
    art.labels.append(Label((z.x + z.w * 0.5, z.y + z.h * 0.55), label, size=8, anchor="middle"))


def _draw_window(art: Artwork, x1: float, y1: float, x2: float, y2: float) -> None:
    art.paths.append(StrokePath([(x1, y1), (x2, y2)], width=3.0))
    if abs(x1 - x2) < 1e-6:
        art.paths.append(StrokePath([(x1 + 0.006, y1), (x2 + 0.006, y2)], width=1.2))
    else:
        art.paths.append(StrokePath([(x1, y1 + 0.006), (x2, y2 + 0.006)], width=1.2))


def _draw_outlet(art: Artwork, x: float, y: float) -> None:
    art.rects.append(Rect(x - 0.010, y - 0.007, 0.020, 0.014, width=1.8))
    art.circles.append(Circle((x - 0.004, y), 0.0017, width=1.2))
    art.circles.append(Circle((x + 0.004, y), 0.0017, width=1.2))


def _draw_plant(art: Artwork, x: float, y: float, size: float = 0.045) -> None:
    art.rects.append(Rect(x - size * 0.18, y + size * 0.05, size * 0.36, size * 0.20, width=1.8))
    art.paths.append(StrokePath([(x, y - size * 0.32), (x - size * 0.10, y), (x, y + size * 0.02)], width=1.8))
    art.paths.append(StrokePath([(x, y - size * 0.32), (x + size * 0.10, y), (x, y + size * 0.02)], width=1.8))


def _draw_counter(art: Artwork, x: float, y: float, w: float, h: float) -> None:
    art.rects.append(Rect(x, y, w, h, width=2.5))
    art.labels.append(Label((x + w * 0.5, y + h * 0.55), "COUNTER", size=8, anchor="middle"))


def _draw_traffic_path(art: Artwork, x1: float, y1: float, x2: float, y2: float) -> None:
    art.paths.append(StrokePath([(x1, y1), (x2, y2)], width=1.2))
    art.labels.append(Label(((x1 + x2) * 0.5, (y1 + y2) * 0.5 - 0.012), "TRAFFIC", size=7, anchor="middle"))


def _draw_seat(art: Artwork, seat: Seat) -> None:
    tw, th = 0.070, 0.048
    x = seat.x - tw * 0.5
    y = seat.y - th * 0.5
    art.rects.append(Rect(x, y, tw, th, width=2.0))
    art.labels.append(Label((seat.x, y - 0.008), seat.seat_id, size=9, anchor="middle"))

    chair_r = 0.0085
    for cx, cy in [
        (x - 0.012, y + 0.012),
        (x + tw + 0.012, y + 0.012),
        (x - 0.012, y + th - 0.012),
        (x + tw + 0.012, y + th - 0.012),
    ]:
        art.circles.append(Circle((cx, cy), chair_r, width=1.4))

    if not seat.available:
        art.paths.append(StrokePath([(x - 0.008, y - 0.008), (x + tw + 0.008, y + th + 0.008)], width=2.0))
        art.paths.append(StrokePath([(x - 0.008, y + th + 0.008), (x + tw + 0.008, y - 0.008)], width=2.0))


def _mission_score(mission: Mission, seat: Seat) -> float:
    score = 0.0

    if mission == "Need silence":
        score += 3.0 if seat.in_quiet_zone else 0.0
        score += -3.5 if seat.in_noisy_zone else 0.0
        score += -2.0 if seat.near_traffic else 0.0
        score += seat.privacy_score * 1.5
    elif mission == "Need sunlight":
        score += 4.0 if seat.near_window else 0.0
        score += 1.2 if seat.in_quiet_zone else 0.0
        score += -1.0 if seat.in_noisy_zone else 0.0
    elif mission == "Need power outlet":
        score += 4.5 if seat.near_outlet else 0.0
        score += 1.0 if seat.in_quiet_zone else 0.0
        score += -0.8 if seat.near_traffic else 0.0
    elif mission == "Need people watching":
        score += 3.0 if seat.near_traffic else 0.0
        score += 1.8 if seat.in_noisy_zone else 0.0
        score += -1.2 if seat.in_quiet_zone else 0.0
    elif mission == "Need to leave quickly":
        score += (1.0 / (0.06 + seat.privacy_score)) * 0.5
        score += 3.5 if seat.near_traffic else 0.0
        score += -0.8 if seat.in_quiet_zone else 0.0
    elif mission == "Need privacy":
        score += seat.privacy_score * 4.0
        score += 1.5 if seat.in_quiet_zone else 0.0
        score += -2.5 if seat.near_traffic else 0.0
        score += -2.0 if seat.in_noisy_zone else 0.0

    return score


def _make_layout(seed: int | None, difficulty: Difficulty) -> tuple[list[Seat], Mission, dict[str, float], str]:
    rng = seeded_rng(seed)

    room_left, room_top, room_right, room_bottom = 0.10, 0.20, 0.92, 0.90
    counter = ZoneRect(0.64, 0.22, 0.23, 0.10)
    noisy_zone = ZoneRect(0.58, 0.34, 0.28, 0.18)
    quiet_zone = ZoneRect(0.14, 0.58, 0.28, 0.20)

    windows = [(0.22, room_top, 0.40, room_top), (0.46, room_top, 0.60, room_top), (room_right, 0.58, room_right, 0.74)]
    outlets = [(room_left + 0.003, 0.36), (room_left + 0.003, 0.70), (room_right - 0.003, 0.44), (0.52, room_bottom - 0.003)]
    traffic_paths = [
        (room_left + 0.03, 0.32, room_right - 0.02, 0.32),
        (room_left + 0.05, 0.50, room_right - 0.02, 0.50),
        (room_left + 0.05, 0.80, room_right - 0.02, 0.80),
    ]

    cols, rows = {
        "easy": (3, 3),
        "medium": (4, 3),
        "hard": (4, 4),
    }[difficulty]

    x0, y0 = 0.20, 0.30
    dx = (0.78 - x0) / (cols - 1)
    dy = (0.82 - y0) / (rows - 1)

    seats: list[Seat] = []
    idx = 1

    traffic_band_half = 0.024
    for r in range(rows):
        for c in range(cols):
            sx = x0 + c * dx + float(rng.normal(0.0, 0.004))
            sy = y0 + r * dy + float(rng.normal(0.0, 0.004))

            near_window = any(_dist(sx, sy, (x1 + x2) * 0.5, (y1 + y2) * 0.5) < 0.18 for x1, y1, x2, y2 in windows)
            near_outlet = any(_dist(sx, sy, ox, oy) < 0.16 for ox, oy in outlets)
            in_noisy_zone = noisy_zone.contains(sx, sy)
            in_quiet_zone = quiet_zone.contains(sx, sy)
            near_traffic = any(min(abs(sy - y1), abs(sy - y2)) < traffic_band_half for _, y1, __, y2 in traffic_paths)

            dist_counter = _dist(sx, sy, counter.x + counter.w * 0.5, counter.y + counter.h * 0.5)
            edge_clearance = min(sx - room_left, room_right - sx, sy - room_top, room_bottom - sy)
            privacy_score = max(0.0, min(1.0, 0.6 * (dist_counter / 0.65) + 0.4 * (edge_clearance / 0.20)))

            seats.append(
                Seat(
                    seat_id=f"S{idx}",
                    x=sx,
                    y=sy,
                    available=True,
                    near_window=near_window,
                    near_outlet=near_outlet,
                    in_noisy_zone=in_noisy_zone,
                    in_quiet_zone=in_quiet_zone,
                    near_traffic=near_traffic,
                    privacy_score=privacy_score,
                )
            )
            idx += 1

    occupied_count = {
        "easy": 1,
        "medium": 2,
        "hard": 3,
    }[difficulty]
    taken = rng.choice(len(seats), size=occupied_count, replace=False)
    for i in taken:
        seats[int(i)].available = False

    # Ensure multiple available seats.
    if sum(1 for s in seats if s.available) < 2:
        seats[0].available = True
        seats[1].available = True

    mission = MISSIONS[int(rng.integers(0, len(MISSIONS)))]

    scores: dict[str, float] = {}
    for seat in seats:
        if not seat.available:
            continue
        scores[seat.seat_id] = _mission_score(mission, seat)

    # Tie-break on seat id for deterministic result ordering.
    sorted_candidates = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    correct_seat_id = sorted_candidates[0][0]
    return seats, mission, scores, correct_seat_id


def generate_seat_selection(
    seed: int | None,
    output_dir: Path,
    difficulty: Difficulty = "medium",
    title: str = "Seat Selection",
) -> SeatSelectionResult:
    """Generate a coffee shop seating puzzle with a hidden internal answer."""

    if difficulty not in {"easy", "medium", "hard"}:
        raise ValueError("difficulty must be one of: easy, medium, hard")

    seats, mission, scores, correct_seat_id = _make_layout(seed, difficulty)
    art = Artwork(title=title, subtitle="Choose the best available seat for the mission")

    room_left, room_top, room_right, room_bottom = 0.10, 0.20, 0.92, 0.90
    art.labels.append(Label((0.5, 0.07), title, size=18, anchor="middle"))
    art.labels.append(Label((0.5, 0.105), f"Mission: {mission}", size=12, anchor="middle"))
    art.labels.append(Label((0.5, 0.13), "Pick one available seat. Do not sit at crossed-out tables.", size=9, anchor="middle"))
    art.labels.append(Label((0.5, 0.155), f"Difficulty: {difficulty.upper()}", size=9, anchor="middle"))

    art.rects.append(Rect(room_left, room_top, room_right - room_left, room_bottom - room_top, width=3.0))

    windows = [(0.22, room_top, 0.40, room_top), (0.46, room_top, 0.60, room_top), (room_right, 0.58, room_right, 0.74)]
    outlets = [(room_left + 0.003, 0.36), (room_left + 0.003, 0.70), (room_right - 0.003, 0.44), (0.52, room_bottom - 0.003)]
    noisy_zone = ZoneRect(0.58, 0.34, 0.28, 0.18)
    quiet_zone = ZoneRect(0.14, 0.58, 0.28, 0.20)
    counter = ZoneRect(0.64, 0.22, 0.23, 0.10)

    for x1, y1, x2, y2 in windows:
        _draw_window(art, x1, y1, x2, y2)
    for ox, oy in outlets:
        _draw_outlet(art, ox, oy)

    _draw_zone_box(art, noisy_zone, "NOISY")
    _draw_zone_box(art, quiet_zone, "QUIET")
    _draw_counter(art, counter.x, counter.y, counter.w, counter.h)

    _draw_traffic_path(art, room_left + 0.03, 0.32, room_right - 0.02, 0.32)
    _draw_traffic_path(art, room_left + 0.05, 0.50, room_right - 0.02, 0.50)
    _draw_traffic_path(art, room_left + 0.05, 0.80, room_right - 0.02, 0.80)

    _draw_plant(art, room_left + 0.06, room_top + 0.08)
    _draw_plant(art, room_right - 0.07, room_bottom - 0.07)
    _draw_plant(art, room_right - 0.09, room_top + 0.16)

    for seat in seats:
        _draw_seat(art, seat)

    # Do not draw the computed answer; only store it in return metadata.
    svg_path, png_path = export_artwork(art, f"seat_selection_{difficulty}", output_dir)

    puzzle_data = SeatSelectionPuzzleData(
        mission=mission,
        difficulty=difficulty,
        seats=seats,
        correct_seat_id=correct_seat_id,
        score_by_seat_id=scores,
    )
    return SeatSelectionResult(puzzle=puzzle_data, svg_path=svg_path, png_path=png_path)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Generate a coffee shop seat selection puzzle.")
    parser.add_argument("--seed", type=int, default=7, help="Random seed for reproducibility")
    parser.add_argument("--output-dir", type=Path, default=Path("coffee_activity_generator/exports"))
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], default="medium")
    parser.add_argument("--title", default="Seat Selection", help="Title shown above the puzzle")
    args = parser.parse_args()

    result = generate_seat_selection(seed=args.seed, output_dir=args.output_dir, difficulty=args.difficulty, title=args.title)
    print(f"SVG: {result.svg_path}")
    print(f"PNG: {result.png_path}")
    print(f"Mission: {result.puzzle.mission}")


if __name__ == "__main__":
    _main()
