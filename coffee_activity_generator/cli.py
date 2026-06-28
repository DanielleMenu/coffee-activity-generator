"""Shared command-line helpers for generator modules."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

from .common import ensure_dir

GeneratorFn = Callable[[int | None, Path], tuple[Path, Path]]


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
    svg_path, png_path = generator(args.seed, out_dir)
    print(f"SVG: {svg_path}")
    print(f"PNG: {png_path}")
