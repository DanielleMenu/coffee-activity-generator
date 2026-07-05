"""Connect-the-dots activity generator.

Supports both built-in outlines and image-driven connect-the-dots puzzles.
Raster inputs are contourized with OpenCV, SVG inputs are sampled from path data,
then all contours pass through simplification, filtering, ordering, resampling,
and numbering to produce printable puzzle pages.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Literal

import numpy as np
from PIL import Image
from reportlab.lib.pagesizes import inch
from reportlab.pdfgen import canvas

from ..common import Artwork, Circle, Label, PageConfig, add_department_header, ensure_dir, seeded_rng
from ..render import render_png, render_svg


DifficultyName = Literal["easy", "medium", "hard"]


@dataclass(slots=True)
class DifficultySpec:
    name: DifficultyName
    target_dots: int
    font_size: int
    number_offset: float


@dataclass(slots=True)
class ConnectDotsConfig:
    simplify_epsilon_ratio: float = 0.012
    min_area_ratio: float = 0.003
    min_bbox_ratio: float = 0.002
    min_length_ratio: float = 0.10
    min_area_px: float = 120.0
    min_length_px: float = 40.0
    max_contours: int = 6
    close_kernel_size: int = 3
    close_iterations: int = 1
    detail_dilate_iterations: int = 1
    spacing_min_px: float = 8.0
    spacing_max_px: float = 15.0
    dot_radius: float = 0.0031
    dot_stroke: float = 1.0
    drawing_margin_x: float = 0.12
    drawing_top: float = 0.18
    drawing_height: float = 0.62
    label_clearance: float = 0.012
    label_tangent_shift: float = 0.004
    label_box_scale: float = 0.00125


@dataclass(slots=True)
class Contour:
    points: np.ndarray
    closed: bool


@dataclass(slots=True)
class LoadedArtwork:
    kind: Literal["builtin", "raster", "svg"]
    width: float
    height: float
    source_name: str
    raster_rgba: np.ndarray | None = None
    raster_gray: np.ndarray | None = None
    vector_contours: list[Contour] | None = None


@dataclass(slots=True)
class NumberedPoint:
    point: tuple[float, float]
    label_pos: tuple[float, float]
    number: int


@dataclass(slots=True)
class ConnectDotsResult:
    svg_path: Path
    png_path: Path
    pdf_path: Path
    difficulty: DifficultyName

    def __iter__(self) -> Iterator[Path]:
        yield self.svg_path
        yield self.png_path


DIFFICULTIES: dict[DifficultyName, DifficultySpec] = {
    "easy": DifficultySpec("easy", target_dots=48, font_size=8, number_offset=0.015),
    "medium": DifficultySpec("medium", target_dots=82, font_size=8, number_offset=0.013),
    "hard": DifficultySpec("hard", target_dots=120, font_size=6, number_offset=0.0085),
}

DEFAULT_CONFIG = ConnectDotsConfig()


def _sample_segment(start: tuple[float, float], end: tuple[float, float], count: int) -> np.ndarray:
    x = np.linspace(start[0], end[0], count)
    y = np.linspace(start[1], end[1], count)
    return np.column_stack((x, y))


def _sample_arc(
    center: tuple[float, float],
    rx: float,
    ry: float,
    start_angle: float,
    end_angle: float,
    count: int,
) -> np.ndarray:
    t = np.linspace(start_angle, end_angle, count)
    x = center[0] + rx * np.cos(t)
    y = center[1] + ry * np.sin(t)
    return np.column_stack((x, y))


def _barista_outline_points() -> np.ndarray:
    parts = [
        _sample_arc((0.50, 0.26), 0.10, 0.11, -0.50 * np.pi, 1.50 * np.pi, 20),
        _sample_segment((0.50, 0.37), (0.60, 0.40), 3),
        _sample_segment((0.60, 0.40), (0.71, 0.35), 4),
        _sample_segment((0.71, 0.35), (0.75, 0.41), 3),
        _sample_segment((0.75, 0.41), (0.63, 0.47), 5),
        _sample_segment((0.63, 0.47), (0.62, 0.73), 9),
        _sample_segment((0.62, 0.73), (0.67, 0.85), 5),
        _sample_segment((0.67, 0.85), (0.57, 0.85), 4),
        _sample_segment((0.57, 0.85), (0.53, 0.74), 4),
        _sample_segment((0.53, 0.74), (0.50, 0.84), 4),
        _sample_segment((0.50, 0.84), (0.42, 0.84), 4),
        _sample_segment((0.42, 0.84), (0.45, 0.74), 4),
        _sample_segment((0.45, 0.74), (0.37, 0.73), 4),
        _sample_segment((0.37, 0.73), (0.36, 0.50), 8),
        _sample_segment((0.36, 0.50), (0.27, 0.56), 4),
        _sample_segment((0.27, 0.56), (0.24, 0.49), 3),
        _sample_segment((0.24, 0.49), (0.35, 0.43), 5),
        _sample_segment((0.35, 0.43), (0.40, 0.38), 3),
        _sample_segment((0.40, 0.38), (0.50, 0.37), 4),
        _sample_segment((0.50, 0.37), (0.50, 0.15), 5),
    ]
    pts = [parts[0]]
    for seg in parts[1:]:
        pts.append(seg[1:])
    return np.vstack(pts)


def _require_cv2() -> object:
    try:
        import cv2  # type: ignore
    except ImportError as exc:
        raise RuntimeError("OpenCV is required for raster connect-the-dots inputs. Install opencv-python-headless.") from exc
    return cv2


def _require_svgpathtools() -> object:
    try:
        from svgpathtools import svg2paths2  # type: ignore
    except ImportError as exc:
        raise RuntimeError("svgpathtools is required for SVG connect-the-dots inputs.") from exc
    return svg2paths2


def _polyline_length(points: np.ndarray, closed: bool) -> float:
    if len(points) < 2:
        return 0.0
    pts = points
    if closed:
        pts = np.vstack((points, points[0]))
    return float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())


def _signed_area(points: np.ndarray) -> float:
    if len(points) < 3:
        return 0.0
    x = points[:, 0]
    y = points[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def _bbox_area(points: np.ndarray) -> float:
    span = np.ptp(points, axis=0)
    return float(span[0] * span[1])


def _contour_centroid(points: np.ndarray) -> np.ndarray:
    if len(points) == 0:
        return np.array([0.0, 0.0])
    return points.mean(axis=0)


def _is_closed(points: np.ndarray) -> bool:
    return len(points) >= 3 and float(np.linalg.norm(points[0] - points[-1])) <= 1.5


def _normalize_contour(points: np.ndarray, closed: bool) -> Contour:
    pts = points.astype(float)
    if closed and len(pts) >= 2 and float(np.linalg.norm(pts[0] - pts[-1])) <= 1.5:
        pts = pts[:-1]
    return Contour(points=pts, closed=closed)


def load_image(source_path: Path | None) -> LoadedArtwork:
    if source_path is None:
        pts = _barista_outline_points() * 1000.0
        return LoadedArtwork(
            kind="builtin",
            width=1000.0,
            height=1000.0,
            source_name="barista",
            vector_contours=[Contour(points=pts, closed=False)],
        )

    suffix = source_path.suffix.lower()
    if suffix == ".svg":
        svg2paths2 = _require_svgpathtools()
        paths, _, svg_attr = svg2paths2(str(source_path))

        if "viewBox" in svg_attr:
            _, _, width_str, height_str = svg_attr["viewBox"].replace(",", " ").split()
            width = float(width_str)
            height = float(height_str)
        else:
            width = float(str(svg_attr.get("width", "100")).replace("px", ""))
            height = float(str(svg_attr.get("height", "100")).replace("px", ""))

        contours: list[Contour] = []
        for path in paths:
            for subpath in path.continuous_subpaths():
                samples = max(32, int(max(subpath.length(error=1e-3), 20.0) / 4.0))
                pts = []
                for idx in range(samples):
                    t = 0.0 if samples == 1 else idx / (samples - 1)
                    z = subpath.point(t)
                    pts.append((float(z.real), float(z.imag)))
                arr = np.array(pts, dtype=float)
                contours.append(_normalize_contour(arr, closed=subpath.isclosed() or _is_closed(arr)))

        return LoadedArtwork(
            kind="svg",
            width=width,
            height=height,
            source_name=source_path.stem,
            vector_contours=contours,
        )

    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise RuntimeError(f"Unsupported connect-the-dots source format: {source_path.suffix}")

    rgba = np.array(Image.open(source_path).convert("RGBA"))
    gray = np.array(Image.open(source_path).convert("L"))
    return LoadedArtwork(
        kind="raster",
        width=float(rgba.shape[1]),
        height=float(rgba.shape[0]),
        source_name=source_path.stem,
        raster_rgba=rgba,
        raster_gray=gray,
    )


def extract_contours(loaded: LoadedArtwork, config: ConnectDotsConfig) -> list[Contour]:
    if loaded.vector_contours is not None:
        return list(loaded.vector_contours)

    if loaded.raster_rgba is None or loaded.raster_gray is None:
        raise RuntimeError("Raster source is missing image data.")

    cv2 = _require_cv2()
    rgba = loaded.raster_rgba
    gray = loaded.raster_gray

    alpha = rgba[:, :, 3]
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    binary[alpha <= 15] = 0

    kernel = np.ones((config.close_kernel_size, config.close_kernel_size), dtype=np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=config.close_iterations)
    if config.detail_dilate_iterations > 0:
        binary = cv2.dilate(binary, kernel, iterations=config.detail_dilate_iterations)

    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    extracted: list[Contour] = []
    for contour in contours:
        pts = contour[:, 0, :].astype(float)
        if len(pts) < 3:
            continue
        extracted.append(_normalize_contour(pts, closed=True))
    return extracted


def _point_line_distance(point: np.ndarray, start: np.ndarray, end: np.ndarray) -> float:
    seg = end - start
    seg_len_sq = float(np.dot(seg, seg))
    if seg_len_sq <= 1e-12:
        return float(np.linalg.norm(point - start))
    projection = float(np.dot(point - start, seg) / seg_len_sq)
    projection = max(0.0, min(1.0, projection))
    nearest = start + projection * seg
    return float(np.linalg.norm(point - nearest))


def _douglas_peucker_open(points: np.ndarray, epsilon: float) -> np.ndarray:
    if len(points) <= 2:
        return points

    start = points[0]
    end = points[-1]
    distances = np.array([_point_line_distance(point, start, end) for point in points[1:-1]], dtype=float)
    if len(distances) == 0:
        return np.vstack((start, end))

    idx = int(np.argmax(distances)) + 1
    max_distance = float(distances[idx - 1])
    if max_distance <= epsilon:
        return np.vstack((start, end))

    left = _douglas_peucker_open(points[: idx + 1], epsilon)
    right = _douglas_peucker_open(points[idx:], epsilon)
    return np.vstack((left[:-1], right))


def _simplify_points(points: np.ndarray, epsilon: float, closed: bool) -> np.ndarray:
    pts = points
    if closed:
        pts = np.vstack((points, points[0]))
        simplified = _douglas_peucker_open(pts, epsilon)
        return simplified[:-1]
    return _douglas_peucker_open(points, epsilon)


def simplify_contours(contours: list[Contour], config: ConnectDotsConfig) -> list[Contour]:
    simplified: list[Contour] = []
    for contour in contours:
        epsilon = max(1.5, _polyline_length(contour.points, contour.closed) * config.simplify_epsilon_ratio)
        pts = _simplify_points(contour.points, epsilon=epsilon, closed=contour.closed)
        if len(pts) >= (3 if contour.closed else 2):
            simplified.append(Contour(points=pts, closed=contour.closed))
    return simplified


def filter_contours(contours: list[Contour], loaded: LoadedArtwork, config: ConnectDotsConfig) -> list[Contour]:
    if not contours:
        raise RuntimeError("No contours found for connect-the-dots generation.")

    canvas_area = loaded.width * loaded.height
    lengths = [_polyline_length(contour.points, contour.closed) for contour in contours]
    areas = [abs(_signed_area(contour.points)) if contour.closed else 0.0 for contour in contours]
    bbox_areas = [_bbox_area(contour.points) for contour in contours]

    max_area = max(max(areas), config.min_area_px)
    max_length = max(max(lengths), config.min_length_px)

    ranked: list[tuple[float, int]] = []
    kept: list[Contour] = []
    for idx, contour in enumerate(contours):
        area = areas[idx]
        length = lengths[idx]
        bbox_area = bbox_areas[idx]

        too_small = (
            bbox_area < canvas_area * config.min_bbox_ratio
            or (area < config.min_area_px and length < config.min_length_px)
            or (area < max_area * config.min_area_ratio and length < max_length * config.min_length_ratio)
        )
        if too_small:
            continue

        importance = max(area, bbox_area * 0.8) + length * 4.0
        ranked.append((importance, idx))

    if not ranked:
        biggest = int(np.argmax(bbox_areas))
        return [contours[biggest]]

    ranked.sort(reverse=True)
    for _, idx in ranked[: config.max_contours]:
        kept.append(contours[idx])
    return kept


def _order_score(candidate: Contour, previous: Contour | None, primary_area: float) -> tuple[float, float, float]:
    area = abs(_signed_area(candidate.points)) if candidate.closed else _bbox_area(candidate.points)
    centroid = _contour_centroid(candidate.points)
    if previous is None:
        return (-area, centroid[1], centroid[0])
    prev_centroid = _contour_centroid(previous.points)
    distance = float(np.linalg.norm(prev_centroid - centroid))
    return (distance, -area / max(primary_area, 1.0), centroid[1])


def order_contours(contours: list[Contour]) -> list[Contour]:
    if not contours:
        return []

    primary_area = max(
        [abs(_signed_area(contour.points)) for contour in contours if contour.closed]
        or [_bbox_area(contour.points) for contour in contours]
        or [1.0]
    )
    remaining = list(contours)
    ordered: list[Contour] = []
    previous: Contour | None = None

    while remaining:
        next_index = min(range(len(remaining)), key=lambda idx: _order_score(remaining[idx], previous, primary_area))
        next_contour = remaining.pop(next_index)
        ordered.append(next_contour)
        previous = next_contour
    return ordered


def _allocate_dots(contours: list[Contour], target_total: int, config: ConnectDotsConfig) -> list[int]:
    perimeters = np.array([_polyline_length(contour.points, contour.closed) for contour in contours], dtype=float)
    total_perimeter = float(perimeters.sum())
    if total_perimeter <= 1e-9:
        return [max(2, len(contour.points)) for contour in contours]

    minimums = [8 if contour.closed else 5 for contour in contours]
    minimum_total = sum(minimums)
    if target_total <= minimum_total:
        return minimums

    remaining = target_total - minimum_total
    weights = perimeters / total_perimeter
    raw_extra = weights * remaining
    extras = np.floor(raw_extra).astype(int)
    remainder = remaining - int(extras.sum())
    if remainder > 0:
        order = np.argsort(-(raw_extra - extras))
        for idx in order[:remainder]:
            extras[idx] += 1

    return [minimums[idx] + int(extras[idx]) for idx in range(len(contours))]


def _resample_single_contour(contour: Contour, point_count: int) -> np.ndarray:
    vertices = contour.points
    if point_count <= 0:
        return vertices.copy()

    if contour.closed:
        pts = np.vstack((vertices, vertices[0]))
    else:
        pts = vertices

    deltas = np.diff(pts, axis=0)
    seg_lengths = np.linalg.norm(deltas, axis=1)
    total = float(seg_lengths.sum())
    if total <= 1e-9:
        return vertices.copy()

    targets = np.linspace(0.0, total, point_count + (1 if contour.closed else 0))
    cumulative = np.concatenate(([0.0], np.cumsum(seg_lengths)))
    x = np.interp(targets, cumulative, pts[:, 0])
    y = np.interp(targets, cumulative, pts[:, 1])
    sampled = np.column_stack((x, y))
    if contour.closed:
        sampled = sampled[:-1]
    return sampled


def _resample_single_contour_old(contour: Contour, point_count: int) -> np.ndarray:
    vertices = contour.points
    if contour.closed:
        starts = vertices
        ends = np.roll(vertices, -1, axis=0)
    else:
        starts = vertices[:-1]
        ends = vertices[1:]

    segment_lengths = np.linalg.norm(ends - starts, axis=1)
    total = float(segment_lengths.sum())
    if total <= 1e-9:
        return vertices.copy()

    required_vertices = len(vertices)
    point_count = max(point_count, required_vertices)
    extras = point_count - required_vertices

    if extras > 0:
        weights = segment_lengths / total
        raw = weights * extras
        allocations = np.floor(raw).astype(int)
        remainder = extras - int(allocations.sum())
        if remainder > 0:
            order = np.argsort(-(raw - allocations))
            for idx in order[:remainder]:
                allocations[idx] += 1
    else:
        allocations = np.zeros(len(segment_lengths), dtype=int)

    sampled: list[np.ndarray] = [starts[0]]
    for idx, (start, end) in enumerate(zip(starts, ends, strict=False)):
        count = int(allocations[idx])
        for inner in range(1, count + 1):
            t = inner / (count + 1)
            sampled.append(start * (1.0 - t) + end * t)
        sampled.append(end)

    result = np.array(sampled, dtype=float)
    if contour.closed:
        result = result[:-1]
    return result


def resample_contours(contours: list[Contour], difficulty: DifficultySpec, config: ConnectDotsConfig) -> list[Contour]:
    allocations = _allocate_dots(contours, difficulty.target_dots, config)
    return [Contour(points=_resample_single_contour(contour, allocations[idx]), closed=contour.closed) for idx, contour in enumerate(contours)]


def _normalize_page_contours(contours: list[Contour], config: ConnectDotsConfig) -> list[Contour]:
    all_points = np.vstack([contour.points for contour in contours])
    mins = all_points.min(axis=0)
    maxs = all_points.max(axis=0)
    span = np.maximum(maxs - mins, 1e-6)

    max_width = 1.0 - 2.0 * config.drawing_margin_x
    max_height = config.drawing_height
    scale = min(max_width / span[0], max_height / span[1])

    width = span[0] * scale
    height = span[1] * scale
    x_offset = (1.0 - width) / 2.0 - mins[0] * scale
    y_offset = config.drawing_top + (config.drawing_height - height) / 2.0 - mins[1] * scale

    normalized: list[Contour] = []
    for contour in contours:
        pts = contour.points * scale + np.array([x_offset, y_offset])
        normalized.append(Contour(points=pts, closed=contour.closed))
    return normalized


def _estimate_label_box(text: str, font_size: int, config: ConnectDotsConfig) -> tuple[float, float]:
    width = max(0.010, len(text) * font_size * config.label_box_scale)
    height = max(0.010, font_size * config.label_box_scale * 1.8)
    return width, height


def _boxes_overlap(box_a: tuple[float, float, float, float], box_b: tuple[float, float, float, float]) -> bool:
    ax0, ay0, ax1, ay1 = box_a
    bx0, by0, bx1, by1 = box_b
    return not (ax1 < bx0 or bx1 < ax0 or ay1 < by0 or by1 < ay0)


def number_points(contours: list[Contour], difficulty: DifficultySpec, config: ConnectDotsConfig) -> list[NumberedPoint]:
    occupied_boxes: list[tuple[float, float, float, float]] = []
    numbered: list[NumberedPoint] = []
    counter = 1

    for contour in contours:
        centroid = _contour_centroid(contour.points)
        for idx, point in enumerate(contour.points):
            prev_point = contour.points[idx - 1] if idx > 0 else (contour.points[-1] if contour.closed else contour.points[idx])
            next_point = contour.points[(idx + 1) % len(contour.points)] if contour.closed or idx < len(contour.points) - 1 else contour.points[idx]
            tangent = next_point - prev_point
            tangent_norm = float(np.linalg.norm(tangent))
            if tangent_norm <= 1e-9:
                tangent = np.array([1.0, 0.0])
            else:
                tangent = tangent / tangent_norm
            normal = np.array([-tangent[1], tangent[0]])

            candidate_normals = [normal, -normal]
            candidate_normals.sort(key=lambda n: float(np.linalg.norm(point + n * difficulty.number_offset - centroid)), reverse=True)

            text = str(counter)
            width, height = _estimate_label_box(text, difficulty.font_size, config)
            label_pos: tuple[float, float] | None = None
            for outward in candidate_normals:
                for tangent_shift in (0.0, config.label_tangent_shift, -config.label_tangent_shift):
                    for radial_scale in (1.0, 1.35, 1.7):
                        candidate = point + outward * difficulty.number_offset * radial_scale + tangent * tangent_shift
                        box = (
                            float(candidate[0] - width * 0.5),
                            float(candidate[1] - height * 0.5),
                            float(candidate[0] + width * 0.5),
                            float(candidate[1] + height * 0.5),
                        )
                        if box[0] < 0.04 or box[2] > 0.96 or box[1] < 0.12 or box[3] > 0.91:
                            continue
                        if any(_boxes_overlap(box, existing) for existing in occupied_boxes):
                            continue
                        label_pos = (float(candidate[0]), float(candidate[1]))
                        occupied_boxes.append(box)
                        break
                    if label_pos is not None:
                        break
                if label_pos is not None:
                    break

            if label_pos is None:
                fallback = point + candidate_normals[0] * difficulty.number_offset * 1.8
                label_pos = (float(fallback[0]), float(fallback[1]))

            numbered.append(NumberedPoint(point=(float(point[0]), float(point[1])), label_pos=label_pos, number=counter))
            counter += 1
    return numbered


def _build_artwork(contours: list[Contour], numbered: list[NumberedPoint], difficulty: DifficultySpec, source_name: str) -> Artwork:
    subtitle = f"Reveal the hidden {source_name.replace('_', ' ')}"
    art = Artwork(title="Connect the Dots", subtitle=subtitle)
    add_department_header(art)

    for dot in numbered:
        art.circles.append(Circle(dot.point, radius=0.0019, width=0.8, fill=True))
        art.labels.append(Label(dot.label_pos, str(dot.number), size=difficulty.font_size, anchor="middle"))

    art.labels.append(
        Label((0.5, 0.90), f"Connect 1 -> {len(numbered)}. Keep the line invisible between separate parts.", size=11, anchor="middle")
    )
    return art


def export_svg(art: Artwork, output_path: Path, cfg: PageConfig | None = None) -> Path:
    render_svg(art, output_path, cfg or PageConfig())
    return output_path


def export_png(art: Artwork, output_path: Path, cfg: PageConfig | None = None) -> Path:
    render_png(art, output_path, cfg or PageConfig())
    return output_path


def export_pdf(png_path: Path, pdf_path: Path) -> Path:
    pdf = canvas.Canvas(str(pdf_path), pagesize=(6 * inch, 9 * inch))
    pdf.drawImage(str(png_path), 0, 0, width=6 * inch, height=9 * inch, preserveAspectRatio=False, mask="auto")
    pdf.showPage()
    pdf.save()
    return pdf_path


def _stem_for(source_name: str, difficulty: DifficultyName, built_in: bool) -> str:
    if built_in and difficulty == "medium":
        return "connect_dots"
    return f"connect_dots_{source_name}_{difficulty}".replace("-", "_")


def _generate_connect_dots_artwork(
    seed: int | None,
    source_path: Path | None,
    difficulty: DifficultyName,
    config: ConnectDotsConfig,
) -> tuple[Artwork, str]:
    loaded = load_image(source_path)
    extracted = extract_contours(loaded, config)
    simplified = simplify_contours(extracted, config)
    filtered = filter_contours(simplified, loaded, config)
    ordered = order_contours(filtered)
    resampled = resample_contours(ordered, DIFFICULTIES[difficulty], config)
    normalized = _normalize_page_contours(resampled, config)

    rng = seeded_rng(seed)
    jitter_scale = 0.0004 if source_path is not None else 0.0007
    jittered = [Contour(points=contour.points + rng.normal(0.0, jitter_scale, size=contour.points.shape), closed=contour.closed) for contour in normalized]
    numbered = number_points(jittered, DIFFICULTIES[difficulty], config)
    return _build_artwork(jittered, numbered, DIFFICULTIES[difficulty], loaded.source_name), loaded.source_name


def generate_connect_dots_variant(
    seed: int | None,
    output_dir: Path,
    *,
    source_path: Path | None = None,
    difficulty: DifficultyName = "medium",
    config: ConnectDotsConfig | None = None,
) -> ConnectDotsResult:
    cfg = config or ConnectDotsConfig()
    art, source_name = _generate_connect_dots_artwork(seed, source_path, difficulty, cfg)
    output_dir = ensure_dir(output_dir)

    built_in = source_path is None
    stem = _stem_for(source_name, difficulty, built_in)
    svg_path = export_svg(art, output_dir / f"{stem}.svg")
    png_path = export_png(art, output_dir / f"{stem}.png")
    pdf_path = export_pdf(png_path, output_dir / f"{stem}.pdf")
    return ConnectDotsResult(svg_path=svg_path, png_path=png_path, pdf_path=pdf_path, difficulty=difficulty)


def generate_connect_dots_from_image(
    seed: int | None,
    output_dir: Path,
    image_path: Path | None = None,
    *,
    difficulty: DifficultyName = "medium",
    config: ConnectDotsConfig | None = None,
) -> ConnectDotsResult:
    return generate_connect_dots_variant(seed, output_dir, source_path=image_path, difficulty=difficulty, config=config)


def generate_connect_dots(seed: int | None, output_dir: Path) -> ConnectDotsResult:
    return generate_connect_dots_variant(seed, output_dir, source_path=None, difficulty="medium")


def _build_config_from_args(args: argparse.Namespace) -> ConnectDotsConfig:
    return ConnectDotsConfig(
        simplify_epsilon_ratio=args.simplify_epsilon_ratio,
        min_area_ratio=args.min_area_ratio,
        min_bbox_ratio=args.min_bbox_ratio,
        min_length_ratio=args.min_length_ratio,
        max_contours=args.max_contours,
        spacing_min_px=args.spacing_min_px,
        spacing_max_px=args.spacing_max_px,
    )


def _iter_difficulties(requested: str) -> Iterable[DifficultyName]:
    if requested == "all":
        return ("easy", "medium")
    return (requested,)  # type: ignore[return-value]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="connect-dots", description="Generate a high-quality connect-the-dots page.")
    parser.add_argument("--seed", type=int, default=7, help="Random seed for reproducibility.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("coffee_activity_generator/exports"),
        help="Folder where SVG, PNG, and PDF are exported.",
    )
    parser.add_argument("--image-path", type=Path, default=None, help="Optional PNG/SVG source image.")
    parser.add_argument("--difficulty", choices=["easy", "medium", "all"], default="medium")
    parser.add_argument("--simplify-epsilon-ratio", type=float, default=DEFAULT_CONFIG.simplify_epsilon_ratio)
    parser.add_argument("--min-area-ratio", type=float, default=DEFAULT_CONFIG.min_area_ratio)
    parser.add_argument("--min-bbox-ratio", type=float, default=DEFAULT_CONFIG.min_bbox_ratio)
    parser.add_argument("--min-length-ratio", type=float, default=DEFAULT_CONFIG.min_length_ratio)
    parser.add_argument("--max-contours", type=int, default=DEFAULT_CONFIG.max_contours)
    parser.add_argument("--spacing-min-px", type=float, default=DEFAULT_CONFIG.spacing_min_px)
    parser.add_argument("--spacing-max-px", type=float, default=DEFAULT_CONFIG.spacing_max_px)
    args = parser.parse_args()

    config = _build_config_from_args(args)
    out_dir = ensure_dir(args.output_dir)
    for difficulty_name in _iter_difficulties(args.difficulty):
        result = generate_connect_dots_from_image(
            seed=args.seed,
            output_dir=out_dir,
            image_path=args.image_path,
            difficulty=difficulty_name,
            config=config,
        )
        print(f"{difficulty_name} SVG: {result.svg_path}")
        print(f"{difficulty_name} PNG: {result.png_path}")
        print(f"{difficulty_name} PDF: {result.pdf_path}")