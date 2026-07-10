"""Word-search puzzle generator.

Example:
    python -m coffee_activity_generator.generators.wordsearch --seed 42
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np

from ..cli import run_generator_cli
from ..common import Artwork, Label, StrokePath, seeded_rng
from ..render import export_artwork

WORDS = [
    "AMERICANO",
    "BEANS",
    "BREW",
    "CAPPUCCINO",
    "CROISSANT",
    "FOAM",
    "LAPTOP",
    "LATTE",
    "MUFFIN",
    "MUG",
    "NAPKIN",
    "OATMILK",
    "OUTLET",
    "ROAST",
    "WIFI",
    "PRODUCTIVITY",
]


@dataclass(slots=True)
class WordPlacement:
    word: str
    cells: list[tuple[int, int]]


@dataclass(slots=True)
class WordSearchResult:
    svg_path: Path
    png_path: Path
    answer_key_svg_path: Path
    answer_key_png_path: Path

    def __iter__(self) -> Iterator[Path]:
        yield self.svg_path
        yield self.png_path


def _place_words(grid: np.ndarray, words: list[str], rng: np.random.Generator) -> list[WordPlacement]:
    # Backward placements are disallowed: only right, down, and down-right.
    directions = [(1, 0), (0, 1), (1, 1)]
    n = grid.shape[0]
    placements: list[WordPlacement] = []

    for word in words:
        placed = False
        for _ in range(200):
            dx, dy = directions[int(rng.integers(0, len(directions)))]
            x = int(rng.integers(0, n))
            y = int(rng.integers(0, n))
            cells = [(x + i * dx, y + i * dy) for i in range(len(word))]
            if any(not (0 <= cx < n and 0 <= cy < n) for cx, cy in cells):
                continue
            if any(grid[cy, cx] not in ("", ch) for (cx, cy), ch in zip(cells, word, strict=False)):
                continue
            for (cx, cy), ch in zip(cells, word, strict=False):
                grid[cy, cx] = ch
            placed = True
            placements.append(WordPlacement(word=word, cells=cells))
            break
        if not placed:
            raise RuntimeError(f"Could not place word: {word}")

    return placements


def _draw_grid_artwork(grid: np.ndarray) -> tuple[Artwork, float, float, float, float, float]:
    size = grid.shape[0]
    art = Artwork(title="", subtitle="")

    # Typography/style requested for this puzzle export.
    letter_size = 24
    font_family = '"Avenir Next","Aptos","Futura",sans-serif'
    font_weight = "700"

    # Space letters by multipliers relative to character metrics in print units.
    # Approximate uppercase width for this heavier sans style is closer to 0.9em.
    page_w_in = 6.0
    page_h_in = 9.0
    letter_in = letter_size / 72.0
    char_width_in = letter_in * 0.9
    x_step = (char_width_in * 1.1) / page_w_in
    row_step = ((letter_in * 1.2) / page_h_in) * 0.6

    total_w = (size - 1) * x_step
    total_h = (size - 1) * row_step
    x0 = (1.0 - total_w) / 2.0
    y0 = (1.0 - total_h) / 2.0

    baseline_nudge = (letter_in * 0.35) / page_h_in

    for r in range(size):
        for c in range(size):
            art.labels.append(
                Label(
                    (x0 + c * x_step, y0 + r * row_step + baseline_nudge),
                    str(grid[r, c]),
                    size=letter_size,
                    anchor="middle",
                    font_family=font_family,
                    font_weight=font_weight,
                    png_scale=1.0,
                )
            )

    return art, x0, y0, x_step, row_step, baseline_nudge


def _draw_answer_key_artwork(grid: np.ndarray, placements: list[WordPlacement]) -> Artwork:
    art, x0, y0, x_step, row_step, baseline_nudge = _draw_grid_artwork(grid)
    art.labels.append(Label((0.5, 0.07), "ANSWER KEY", size=20, anchor="middle"))

    for placement in placements:
        start = placement.cells[0]
        end = placement.cells[-1]
        sx = x0 + start[0] * x_step
        sy = y0 + start[1] * row_step + baseline_nudge
        ex = x0 + end[0] * x_step
        ey = y0 + end[1] * row_step + baseline_nudge
        art.paths.append(StrokePath(points=[(sx, sy), (ex, ey)], width=3.0))

    return art


def generate_wordsearch(seed: int | None, output_dir: Path) -> WordSearchResult:
    """Generate a coffee-themed printable word-search."""

    rng = seeded_rng(seed)
    size = 14

    grid: np.ndarray | None = None
    for _ in range(32):
        candidate = np.full((size, size), "", dtype="U1")
        try:
            placements = _place_words(candidate, WORDS, rng)
            grid = candidate
            break
        except RuntimeError:
            continue

    if grid is None:
        raise RuntimeError("Could not place all words in the word-search grid.")

    alphabet = np.array(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    empties = np.where(grid == "")
    grid[empties] = alphabet[rng.integers(0, len(alphabet), size=len(empties[0]))]

    puzzle_art, _, _, _, _, _ = _draw_grid_artwork(grid)
    answer_key_art = _draw_answer_key_artwork(grid, placements)
    svg_path, png_path = export_artwork(puzzle_art, "wordsearch", output_dir)
    answer_key_svg_path, answer_key_png_path = export_artwork(answer_key_art, "wordsearch_answer_key", output_dir)

    return WordSearchResult(
        svg_path=svg_path,
        png_path=png_path,
        answer_key_svg_path=answer_key_svg_path,
        answer_key_png_path=answer_key_png_path,
    )


if __name__ == "__main__":
    run_generator_cli("wordsearch", "Generate the coffee word-search puzzle.", generate_wordsearch)
