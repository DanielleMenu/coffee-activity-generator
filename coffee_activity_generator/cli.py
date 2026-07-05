"""Shared command-line helpers for generator modules."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from pathlib import Path
from typing import Callable

from .common import ensure_dir

GeneratorFn = Callable[[int | None, Path], Iterable[Path]]


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
    svg_path, png_path = result
    print(f"SVG: {svg_path}")
    print(f"PNG: {png_path}")

    answer_key_svg = getattr(result, "answer_key_svg_path", None)
    answer_key_png = getattr(result, "answer_key_png_path", None)
    pdf_path = getattr(result, "pdf_path", None)
    if answer_key_svg is not None:
        print(f"Answer key SVG: {answer_key_svg}")
    if answer_key_png is not None:
        print(f"Answer key PNG: {answer_key_png}")
    if pdf_path is not None:
        print(f"PDF: {pdf_path}")
