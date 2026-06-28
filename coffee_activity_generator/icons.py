"""Procedural line-art icon library built from shared SVG primitives.

Icons are defined in local unit coordinates and transformed to normalized page
coordinates by center and size. All icons are monochrome and stroke-based for
print-friendly output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .common import Artwork, Circle, Rect, StrokePath

Point = tuple[float, float]


@dataclass(slots=True)
class IconGeometry:
    """Container of primitive shapes that make up one icon."""

    paths: list[StrokePath] = field(default_factory=list)
    circles: list[Circle] = field(default_factory=list)
    rects: list[Rect] = field(default_factory=list)


IconFactory = Callable[[Point, float, float], IconGeometry]


def add_icon(art: Artwork, geometry: IconGeometry) -> None:
    """Append an icon geometry into an artwork."""

    art.paths.extend(geometry.paths)
    art.circles.extend(geometry.circles)
    art.rects.extend(geometry.rects)


def _t(center: Point, size: float, local: Point) -> Point:
    """Transform local 0..1 icon coordinates into page coordinates."""

    cx, cy = center
    return cx + (local[0] - 0.5) * size, cy + (local[1] - 0.5) * size


def _path(center: Point, size: float, points: list[Point], width: float) -> StrokePath:
    return StrokePath([_t(center, size, p) for p in points], width=width)


def _rect(center: Point, size: float, x: float, y: float, w: float, h: float, width: float) -> Rect:
    px, py = _t(center, size, (x, y))
    return Rect(px, py, w * size, h * size, width=width)


def _circle(center: Point, size: float, c: Point, radius: float, width: float) -> Circle:
    cx, cy = _t(center, size, c)
    return Circle((cx, cy), radius * size, width=width)


def coffee_cup_icon(center: Point, size: float = 0.10, stroke_width: float = 2.0) -> IconGeometry:
    g = IconGeometry()
    g.paths.append(_path(center, size, [(0.20, 0.34), (0.20, 0.68), (0.72, 0.68), (0.72, 0.34)], stroke_width))
    g.paths.append(_path(center, size, [(0.28, 0.30), (0.64, 0.30)], stroke_width))
    g.paths.append(_path(center, size, [(0.72, 0.44), (0.84, 0.44), (0.84, 0.60), (0.72, 0.60)], stroke_width))
    g.paths.append(_path(center, size, [(0.28, 0.22), (0.28, 0.08)], stroke_width * 0.8))
    g.paths.append(_path(center, size, [(0.44, 0.22), (0.44, 0.06)], stroke_width * 0.8))
    return g


def espresso_cup_icon(center: Point, size: float = 0.10, stroke_width: float = 2.0) -> IconGeometry:
    g = IconGeometry()
    g.paths.append(_path(center, size, [(0.26, 0.40), (0.26, 0.62), (0.68, 0.62), (0.68, 0.40)], stroke_width))
    g.paths.append(_path(center, size, [(0.68, 0.46), (0.78, 0.46), (0.78, 0.58), (0.68, 0.58)], stroke_width))
    g.paths.append(_path(center, size, [(0.18, 0.70), (0.82, 0.70)], stroke_width))
    g.paths.append(_path(center, size, [(0.24, 0.76), (0.76, 0.76)], stroke_width * 0.8))
    return g


def takeaway_cup_icon(center: Point, size: float = 0.10, stroke_width: float = 2.0) -> IconGeometry:
    g = IconGeometry()
    g.paths.append(_path(center, size, [(0.30, 0.30), (0.70, 0.30), (0.62, 0.78), (0.38, 0.78), (0.30, 0.30)], stroke_width))
    g.paths.append(_path(center, size, [(0.26, 0.24), (0.74, 0.24)], stroke_width))
    g.paths.append(_path(center, size, [(0.32, 0.18), (0.68, 0.18)], stroke_width * 0.9))
    g.paths.append(_path(center, size, [(0.41, 0.48), (0.59, 0.48)], stroke_width * 0.8))
    return g


def outlet_icon(center: Point, size: float = 0.10, stroke_width: float = 2.0) -> IconGeometry:
    g = IconGeometry()
    g.rects.append(_rect(center, size, 0.24, 0.24, 0.52, 0.56, stroke_width))
    g.circles.append(_circle(center, size, (0.42, 0.46), 0.03, stroke_width * 0.8))
    g.circles.append(_circle(center, size, (0.58, 0.46), 0.03, stroke_width * 0.8))
    g.paths.append(_path(center, size, [(0.50, 0.58), (0.50, 0.66)], stroke_width * 0.8))
    return g


def laptop_icon(center: Point, size: float = 0.10, stroke_width: float = 2.0) -> IconGeometry:
    g = IconGeometry()
    g.rects.append(_rect(center, size, 0.22, 0.24, 0.56, 0.34, stroke_width))
    g.paths.append(_path(center, size, [(0.14, 0.66), (0.86, 0.66)], stroke_width))
    g.paths.append(_path(center, size, [(0.18, 0.66), (0.30, 0.76), (0.70, 0.76), (0.82, 0.66)], stroke_width))
    return g


def chair_icon(center: Point, size: float = 0.10, stroke_width: float = 2.0) -> IconGeometry:
    g = IconGeometry()
    g.rects.append(_rect(center, size, 0.30, 0.50, 0.40, 0.12, stroke_width))
    g.paths.append(_path(center, size, [(0.30, 0.20), (0.30, 0.50), (0.70, 0.50), (0.70, 0.20)], stroke_width))
    g.paths.append(_path(center, size, [(0.34, 0.62), (0.34, 0.82)], stroke_width))
    g.paths.append(_path(center, size, [(0.66, 0.62), (0.66, 0.82)], stroke_width))
    return g


def table_icon(center: Point, size: float = 0.10, stroke_width: float = 2.0) -> IconGeometry:
    g = IconGeometry()
    g.circles.append(_circle(center, size, (0.50, 0.34), 0.24, stroke_width))
    g.paths.append(_path(center, size, [(0.50, 0.58), (0.50, 0.80)], stroke_width))
    g.paths.append(_path(center, size, [(0.38, 0.80), (0.62, 0.80)], stroke_width))
    return g


def croissant_icon(center: Point, size: float = 0.10, stroke_width: float = 2.0) -> IconGeometry:
    g = IconGeometry()
    outer = [(0.18, 0.60), (0.28, 0.40), (0.44, 0.30), (0.56, 0.30), (0.72, 0.40), (0.82, 0.60)]
    inner = [(0.28, 0.60), (0.38, 0.48), (0.50, 0.44), (0.62, 0.48), (0.72, 0.60)]
    g.paths.append(_path(center, size, outer, stroke_width))
    g.paths.append(_path(center, size, inner, stroke_width))
    g.paths.append(_path(center, size, [(0.36, 0.52), (0.32, 0.60)], stroke_width * 0.8))
    g.paths.append(_path(center, size, [(0.64, 0.52), (0.68, 0.60)], stroke_width * 0.8))
    return g


def muffin_icon(center: Point, size: float = 0.10, stroke_width: float = 2.0) -> IconGeometry:
    g = IconGeometry()
    g.paths.append(_path(center, size, [(0.34, 0.48), (0.66, 0.48), (0.62, 0.78), (0.38, 0.78), (0.34, 0.48)], stroke_width))
    top = [(0.26, 0.50), (0.30, 0.36), (0.40, 0.30), (0.50, 0.34), (0.60, 0.30), (0.70, 0.36), (0.74, 0.50)]
    g.paths.append(_path(center, size, top, stroke_width))
    return g


def coffee_bean_icon(center: Point, size: float = 0.10, stroke_width: float = 2.0) -> IconGeometry:
    g = IconGeometry()
    bean = [(0.50, 0.20), (0.66, 0.26), (0.76, 0.42), (0.72, 0.62), (0.56, 0.78), (0.40, 0.74), (0.28, 0.58), (0.30, 0.38), (0.44, 0.24), (0.50, 0.20)]
    seam = [(0.38, 0.64), (0.46, 0.52), (0.54, 0.42), (0.62, 0.30)]
    g.paths.append(_path(center, size, bean, stroke_width))
    g.paths.append(_path(center, size, seam, stroke_width * 0.8))
    return g


def plant_icon(center: Point, size: float = 0.10, stroke_width: float = 2.0) -> IconGeometry:
    g = IconGeometry()
    g.rects.append(_rect(center, size, 0.34, 0.62, 0.32, 0.16, stroke_width))
    g.paths.append(_path(center, size, [(0.50, 0.62), (0.50, 0.38)], stroke_width))
    g.paths.append(_path(center, size, [(0.50, 0.44), (0.36, 0.30), (0.50, 0.34)], stroke_width * 0.9))
    g.paths.append(_path(center, size, [(0.50, 0.40), (0.64, 0.26), (0.50, 0.30)], stroke_width * 0.9))
    return g


def barista_icon(center: Point, size: float = 0.10, stroke_width: float = 2.0) -> IconGeometry:
    g = IconGeometry()
    g.circles.append(_circle(center, size, (0.50, 0.24), 0.10, stroke_width))
    g.paths.append(_path(center, size, [(0.40, 0.20), (0.60, 0.20)], stroke_width * 0.8))
    g.rects.append(_rect(center, size, 0.34, 0.36, 0.32, 0.36, stroke_width))
    g.paths.append(_path(center, size, [(0.34, 0.46), (0.22, 0.58)], stroke_width))
    g.paths.append(_path(center, size, [(0.66, 0.46), (0.78, 0.58)], stroke_width))
    g.paths.append(_path(center, size, [(0.42, 0.72), (0.42, 0.88)], stroke_width))
    g.paths.append(_path(center, size, [(0.58, 0.72), (0.58, 0.88)], stroke_width))
    return g


def customer_icon(center: Point, size: float = 0.10, stroke_width: float = 2.0) -> IconGeometry:
    g = IconGeometry()
    g.circles.append(_circle(center, size, (0.50, 0.24), 0.10, stroke_width))
    g.paths.append(_path(center, size, [(0.50, 0.34), (0.50, 0.70)], stroke_width))
    g.paths.append(_path(center, size, [(0.34, 0.48), (0.66, 0.48)], stroke_width))
    g.paths.append(_path(center, size, [(0.42, 0.70), (0.38, 0.88)], stroke_width))
    g.paths.append(_path(center, size, [(0.58, 0.70), (0.62, 0.88)], stroke_width))
    return g


def notebook_icon(center: Point, size: float = 0.10, stroke_width: float = 2.0) -> IconGeometry:
    g = IconGeometry()
    g.rects.append(_rect(center, size, 0.24, 0.18, 0.56, 0.66, stroke_width))
    g.paths.append(_path(center, size, [(0.34, 0.18), (0.34, 0.84)], stroke_width * 0.8))
    for y in [0.26, 0.36, 0.46, 0.56, 0.66, 0.76]:
        g.circles.append(_circle(center, size, (0.29, y), 0.012, stroke_width * 0.8))
    g.paths.append(_path(center, size, [(0.40, 0.34), (0.72, 0.34)], stroke_width * 0.8))
    g.paths.append(_path(center, size, [(0.40, 0.46), (0.72, 0.46)], stroke_width * 0.8))
    return g


def pencil_icon(center: Point, size: float = 0.10, stroke_width: float = 2.0) -> IconGeometry:
    g = IconGeometry()
    g.paths.append(_path(center, size, [(0.18, 0.74), (0.70, 0.22), (0.80, 0.32), (0.28, 0.84), (0.18, 0.74)], stroke_width))
    g.paths.append(_path(center, size, [(0.70, 0.22), (0.88, 0.14), (0.80, 0.32)], stroke_width))
    g.paths.append(_path(center, size, [(0.22, 0.78), (0.30, 0.86)], stroke_width * 0.8))
    return g


def arrow_icon(center: Point, size: float = 0.10, stroke_width: float = 2.0) -> IconGeometry:
    g = IconGeometry()
    g.paths.append(_path(center, size, [(0.16, 0.50), (0.82, 0.50)], stroke_width))
    g.paths.append(_path(center, size, [(0.66, 0.34), (0.82, 0.50), (0.66, 0.66)], stroke_width))
    return g


def door_icon(center: Point, size: float = 0.10, stroke_width: float = 2.0) -> IconGeometry:
    g = IconGeometry()
    g.rects.append(_rect(center, size, 0.28, 0.16, 0.44, 0.70, stroke_width))
    g.circles.append(_circle(center, size, (0.64, 0.52), 0.018, stroke_width * 0.8))
    g.paths.append(_path(center, size, [(0.28, 0.86), (0.72, 0.86)], stroke_width * 0.8))
    return g


def window_icon(center: Point, size: float = 0.10, stroke_width: float = 2.0) -> IconGeometry:
    g = IconGeometry()
    g.rects.append(_rect(center, size, 0.22, 0.20, 0.56, 0.60, stroke_width))
    g.paths.append(_path(center, size, [(0.50, 0.20), (0.50, 0.80)], stroke_width * 0.8))
    g.paths.append(_path(center, size, [(0.22, 0.50), (0.78, 0.50)], stroke_width * 0.8))
    return g


ICON_LIBRARY: dict[str, IconFactory] = {
    "coffee_cup": coffee_cup_icon,
    "espresso_cup": espresso_cup_icon,
    "takeaway_cup": takeaway_cup_icon,
    "outlet": outlet_icon,
    "laptop": laptop_icon,
    "chair": chair_icon,
    "table": table_icon,
    "croissant": croissant_icon,
    "muffin": muffin_icon,
    "coffee_bean": coffee_bean_icon,
    "plant": plant_icon,
    "barista": barista_icon,
    "customer": customer_icon,
    "notebook": notebook_icon,
    "pencil": pencil_icon,
    "arrow": arrow_icon,
    "door": door_icon,
    "window": window_icon,
}


__all__ = [
    "IconGeometry",
    "IconFactory",
    "ICON_LIBRARY",
    "add_icon",
    "coffee_cup_icon",
    "espresso_cup_icon",
    "takeaway_cup_icon",
    "outlet_icon",
    "laptop_icon",
    "chair_icon",
    "table_icon",
    "croissant_icon",
    "muffin_icon",
    "coffee_bean_icon",
    "plant_icon",
    "barista_icon",
    "customer_icon",
    "notebook_icon",
    "pencil_icon",
    "arrow_icon",
    "door_icon",
    "window_icon",
]
