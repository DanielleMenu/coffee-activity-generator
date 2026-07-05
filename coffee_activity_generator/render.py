"""Render SVG and PNG exports from shared artwork primitives."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
import svgwrite

from .common import Artwork, PageConfig


def _to_px(x: float, y: float, cfg: PageConfig) -> tuple[float, float]:
    return x * cfg.width_px, y * cfg.height_px


def render_svg(art: Artwork, output_path: Path, cfg: PageConfig) -> None:
    """Render an SVG page using vector primitives."""

    dwg = svgwrite.Drawing(
        str(output_path),
        size=(f"{cfg.width_in}in", f"{cfg.height_in}in"),
        viewBox=f"0 0 {cfg.width_px} {cfg.height_px}",
    )
    dwg.add(dwg.rect(insert=(0, 0), size=(cfg.width_px, cfg.height_px), fill="white"))

    for rect in art.rects:
        x, y = _to_px(rect.x, rect.y, cfg)
        w, h = rect.w * cfg.width_px, rect.h * cfg.height_px
        dwg.add(dwg.rect(insert=(x, y), size=(w, h), fill="none", stroke="black", stroke_width=rect.width))

    for path in art.paths:
        points = [_to_px(x, y, cfg) for x, y in path.points]
        dwg.add(dwg.polyline(points=points, fill="none", stroke="black", stroke_width=path.width))

    for circle in art.circles:
        cx, cy = _to_px(circle.center[0], circle.center[1], cfg)
        dwg.add(
            dwg.circle(
                center=(cx, cy),
                r=circle.radius * cfg.width_px,
                fill="black" if circle.fill else "none",
                stroke="black",
                stroke_width=circle.width,
            )
        )

    anchors = {"start": "start", "middle": "middle", "end": "end"}
    for label in art.labels:
        x, y = _to_px(label.pos[0], label.pos[1], cfg)
        dwg.add(
            dwg.text(
                label.text,
                insert=(x, y),
                fill="black",
                font_size=label.size,
                font_family="Courier New",
                text_anchor=anchors[label.anchor],
            )
        )

    dwg.save()


def render_png(art: Artwork, output_path: Path, cfg: PageConfig) -> None:
    """Render a raster PNG from the same primitives using Matplotlib."""

    fig, ax = plt.subplots(figsize=(cfg.width_in, cfg.height_in), dpi=cfg.dpi)
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 1)
    ax.set_ylim(1, 0)
    ax.axis("off")

    for rect in art.rects:
        patch = plt.Rectangle((rect.x, rect.y), rect.w, rect.h, fill=False, edgecolor="black", linewidth=rect.width / 2)
        ax.add_patch(patch)

    for path in art.paths:
        xs = [pt[0] for pt in path.points]
        ys = [pt[1] for pt in path.points]
        ax.plot(xs, ys, color="black", linewidth=path.width / 2)

    for circle in art.circles:
        patch = plt.Circle(
            circle.center,
            radius=circle.radius,
            fill=circle.fill,
            facecolor="black" if circle.fill else "none",
            edgecolor="black",
            linewidth=circle.width / 2,
        )
        ax.add_patch(patch)

    for label in art.labels:
        ha = {"start": "left", "middle": "center", "end": "right"}[label.anchor]
        ax.text(
            label.pos[0],
            label.pos[1],
            label.text,
            ha=ha,
            va="center",
            fontsize=label.size * 0.65,
            family="DejaVu Sans Mono",
            color="black",
        )

    fig.savefig(output_path, dpi=cfg.dpi, bbox_inches="tight", pad_inches=0)
    plt.close(fig)

    # Convert to strict black and white for cleaner print output.
    img = Image.open(output_path).convert("L")
    bw = img.point(lambda v: 0 if v < 200 else 255, mode="1")
    bw.save(output_path)


def export_artwork(art: Artwork, stem: str, output_dir: Path, cfg: PageConfig | None = None) -> tuple[Path, Path]:
    """Export an artwork as both SVG and PNG and return file paths."""

    cfg = cfg or PageConfig()
    output_dir.mkdir(parents=True, exist_ok=True)
    svg_path = output_dir / f"{stem}.svg"
    png_path = output_dir / f"{stem}.png"
    render_svg(art, svg_path, cfg)
    render_png(art, png_path, cfg)
    return svg_path, png_path
