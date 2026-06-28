"""Cafe floorplan puzzle generator.

Example:
    python -m coffee_activity_generator.generators.floorplan --seed 42
"""

from __future__ import annotations

from pathlib import Path

from shapely.geometry import LineString, Polygon
from shapely.ops import split

from ..cli import run_generator_cli
from ..common import Artwork, Label, StrokePath, add_department_header, jittered_line, seeded_rng
from ..render import export_artwork


def _split_polygon(poly: Polygon, cuts: list[LineString]) -> list[Polygon]:
    """Split polygon by a list of cutting lines and return resulting rooms."""

    rooms = [poly]
    for cut in cuts:
        next_rooms: list[Polygon] = []
        for room in rooms:
            if room.intersects(cut):
                result = split(room, cut)
                next_rooms.extend(Polygon(geom.exterior.coords) for geom in result.geoms)
            else:
                next_rooms.append(room)
        rooms = next_rooms
    return rooms


def generate_floorplan(seed: int | None, output_dir: Path) -> tuple[Path, Path]:
    """Generate a floorplan pathfinding challenge using Shapely geometry."""

    rng = seeded_rng(seed)
    art = Artwork(title="Cafe Floorplan", subtitle="Plan an efficient route for one heroic barista")
    add_department_header(art)

    outer = Polygon([(0.12, 0.20), (0.88, 0.20), (0.88, 0.90), (0.12, 0.90)])
    cuts = [
        LineString([(0.36, 0.20), (0.36, 0.68)]),
        LineString([(0.58, 0.36), (0.88, 0.36)]),
        LineString([(0.58, 0.60), (0.88, 0.60)]),
        LineString([(0.12, 0.52), (0.36, 0.52)]),
    ]
    rooms = _split_polygon(outer, cuts)

    for room in rooms:
        pts = list(room.exterior.coords)
        for i in range(len(pts) - 1):
            p1 = pts[i]
            p2 = pts[i + 1]
            art.paths.append(StrokePath(jittered_line((p1[0], p1[1]), (p2[0], p2[1]), rng)))

    labels = ["Roaster", "Milk Lab", "Espresso", "Pastry", "Sink", "Storage"]
    for name, room in zip(labels, rooms, strict=False):
        cx, cy = room.centroid.x, room.centroid.y
        art.labels.append(Label((float(cx), float(cy)), name, size=11, anchor="middle"))

    art.labels.append(Label((0.5, 0.94), "Draw the shortest line from Roaster to Espresso without crossing walls.", size=11, anchor="middle"))
    return export_artwork(art, "floorplan", output_dir)


if __name__ == "__main__":
    run_generator_cli("floorplan", "Generate the cafe floorplan puzzle.", generate_floorplan)
