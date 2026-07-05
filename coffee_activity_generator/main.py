"""Main CLI to generate one or all coffee-themed activity pages."""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from pathlib import Path
from typing import Callable

from reportlab.lib.pagesizes import inch
from reportlab.pdfgen import canvas

from .common import ensure_dir
from .generators.coffee_flow import generate_coffee_flow
from .generators.connect_dots import generate_connect_dots
from .generators.floorplan import generate_floorplan
from .generators.hidden_objects import generate_hidden_objects
from .generators.maze import generate_maze
from .generators.queue_logic import generate_queue_logic
from .generators.seat_selection import generate_seat_selection
from .generators.spot_difference import generate_spot_difference
from .generators.wordsearch import generate_wordsearch


Generator = Callable[[int | None, Path], Iterable[Path]]

GENERATORS: dict[str, Generator] = {
    "maze": generate_maze,
    "connect-dots": generate_connect_dots,
    "floorplan": generate_floorplan,
    "seat-selection": generate_seat_selection,
    "coffee-flow": generate_coffee_flow,
    "queue-logic": generate_queue_logic,
    "wordsearch": generate_wordsearch,
    "hidden-objects": generate_hidden_objects,
    "spot-difference": generate_spot_difference,
}


def build_pdf(png_paths: list[Path], output_pdf: Path) -> None:
    """Create a 6x9 PDF booklet from generated PNG pages."""

    c = canvas.Canvas(str(output_pdf), pagesize=(6 * inch, 9 * inch))
    for png in png_paths:
        c.drawImage(str(png), 0, 0, width=6 * inch, height=9 * inch, preserveAspectRatio=False, mask="auto")
        c.showPage()
    c.save()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Department of Coffee Research activity pages.")
    parser.add_argument("activity", choices=["all", *GENERATORS.keys()], help="Activity to generate")
    parser.add_argument("--seed", type=int, default=7, help="Random seed for reproducibility")
    parser.add_argument("--output-dir", type=Path, default=Path("coffee_activity_generator/exports"))
    parser.add_argument("--pdf", action="store_true", help="Also assemble generated PNG files into a PDF book")
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    generated_pngs: list[Path] = []

    names = list(GENERATORS.keys()) if args.activity == "all" else [args.activity]
    for idx, name in enumerate(names):
        result = GENERATORS[name](args.seed + idx, output_dir)
        svg_path, png_path = result
        generated_pngs.append(png_path)
        print(f"{name}: {svg_path} | {png_path}")

        answer_key_svg = getattr(result, "answer_key_svg_path", None)
        answer_key_png = getattr(result, "answer_key_png_path", None)
        if answer_key_svg is not None:
            print(f"{name} answer key SVG: {answer_key_svg}")
        if answer_key_png is not None:
            print(f"{name} answer key PNG: {answer_key_png}")

    if args.pdf:
        pdf_path = output_dir / "coffee_activity_book.pdf"
        build_pdf(generated_pngs, pdf_path)
        print(f"PDF: {pdf_path}")


if __name__ == "__main__":
    main()
