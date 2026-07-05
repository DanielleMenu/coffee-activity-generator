"""Common data structures and helper utilities for all activity generators."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np

Point = tuple[float, float]
Anchor = Literal["start", "middle", "end"]


@dataclass(slots=True)
class PageConfig:
    """Physical page configuration for KDP-ready pages."""

    width_in: float = 6.0
    height_in: float = 9.0
    dpi: int = 300

    @property
    def width_px(self) -> int:
        return int(self.width_in * self.dpi)

    @property
    def height_px(self) -> int:
        return int(self.height_in * self.dpi)


@dataclass(slots=True)
class StrokePath:
    points: list[Point]
    width: float = 2.0


@dataclass(slots=True)
class Circle:
    center: Point
    radius: float
    width: float = 2.0
    fill: bool = False


@dataclass(slots=True)
class Rect:
    x: float
    y: float
    w: float
    h: float
    width: float = 2.0


@dataclass(slots=True)
class Label:
    pos: Point
    text: str
    size: int = 14
    anchor: Anchor = "start"


@dataclass(slots=True)
class Artwork:
    """Container for drawable elements in normalized page space (0..1)."""

    title: str
    subtitle: str
    paths: list[StrokePath] = field(default_factory=list)
    circles: list[Circle] = field(default_factory=list)
    rects: list[Rect] = field(default_factory=list)
    labels: list[Label] = field(default_factory=list)


def seeded_rng(seed: int | None) -> np.random.Generator:
    """Return a reproducible NumPy random generator."""

    return np.random.default_rng(seed)


def ensure_dir(path: str | Path) -> Path:
    """Create a directory if needed and return it as a Path."""

    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def jittered_line(
    p1: Point,
    p2: Point,
    rng: np.random.Generator,
    wiggle: float = 0.0025,
    segments: int = 8,
) -> list[Point]:
    """Create a subtle hand-drawn polyline between two points."""

    t_values = np.linspace(0.0, 1.0, segments + 1)
    pts: list[Point] = []
    for t in t_values:
        x = p1[0] + (p2[0] - p1[0]) * t
        y = p1[1] + (p2[1] - p1[1]) * t
        if 0.0 < t < 1.0:
            x += float(rng.normal(0.0, wiggle))
            y += float(rng.normal(0.0, wiggle))
        pts.append((x, y))
    return pts


def add_department_header(art: Artwork) -> None:
    """Add a consistent Department of Coffee Research page header."""

    art.labels.append(Label((0.5, 0.05), "DEPARTMENT OF COFFEE RESEARCH", size=16, anchor="middle"))
    art.labels.append(Label((0.5, 0.082), art.title, size=18, anchor="middle"))
    art.labels.append(Label((0.5, 0.11), art.subtitle, size=12, anchor="middle"))
    art.rects.append(Rect(0.05, 0.03, 0.90, 0.10, width=2.0))
