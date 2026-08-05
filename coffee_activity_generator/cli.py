"""Shared command-line helpers for generator modules."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from pathlib import Path
from typing import Callable

from .common import ensure_dir

GeneratorFn = Callable[[int | None, Path], Iterable[Path]]


def _extract_primary_paths(result: object) -> tuple[Path, Path | None]:
    svg_path = getattr(result, "svg_path", None)
    png_path = getattr(result, "png_path", None)
    if isinstance(svg_path, Path):
        return svg_path, png_path if isinstance(png_path, Path) else None

    svg_path, png_path = result  # type: ignore[misc]
    if not isinstance(svg_path, Path):
        raise TypeError("Generator result must include a Path svg_path.")
    if png_path is not None and not isinstance(png_path, Path):
        raise TypeError("Generator png_path must be a Path or None.")
    return svg_path, png_path


def run_generator_cli(name: str, description: str, generator: GeneratorFn) -> None:
    """Build and run a simple standard CLI for any generator."""

    parser = argparse.ArgumentParser(prog=name, description=description)
    parser.add_argument("--seed", type=int, default=7, help="Random seed for reproducibility.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("coffee_activity_generator/exports"),
        help="Folder where both SVG and PNG are exported.",
    )
    args = parser.parse_args()
    out_dir = ensure_dir(args.output_dir)
    result = generator(args.seed, out_dir)
    svg_path, png_path = _extract_primary_paths(result)
    print(f"SVG: {svg_path.resolve()}")
    if png_path is not None:
        print(f"PNG: {png_path.resolve()}")

    answer_key_svg = getattr(result, "answer_key_svg_path", None)
    answer_key_png = getattr(result, "answer_key_png_path", None)
    pdf_path = getattr(result, "pdf_path", None)
    if answer_key_svg is not None:
        print(f"Answer key SVG: {answer_key_svg.resolve()}")
    if answer_key_png is not None:
        print(f"Answer key PNG: {answer_key_png.resolve()}")
    if pdf_path is not None:
        print(f"PDF: {pdf_path.resolve()}")
