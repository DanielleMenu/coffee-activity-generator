"""Word-search puzzle generator.

Example:
    python -m coffee_activity_generator.generators.wordsearch --seed 42
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Iterator
import sys

import numpy as np

try:
    from ..cli import run_generator_cli
    from ..common import Artwork, Label, PageConfig, StrokePath, seeded_rng
    from ..render import render_svg
except ImportError:
    # Allow direct execution: python coffee_activity_generator/generators/wordsearch.py
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from coffee_activity_generator.cli import run_generator_cli
    from coffee_activity_generator.common import Artwork, Label, PageConfig, StrokePath, seeded_rng
    from coffee_activity_generator.render import render_svg

DEFAULT_WORDS = [
    "AMERICANO",
    "BEANS",
    "BREW",
    "CAPPUCCINO",
    "CORTADO",
    "CREAM",
    "ESPRESSO",
    "FILTER",
    "FLATWHITE",
    "MACCHIATO",
    "MOCHA",
    "OATMILK",
    "ROAST",
    "GRINDER",
    "SYRUP",
    "DECAF"
]

WORDS_FILE = Path(__file__).with_name("wordsearch_words.txt")


def _normalize_words(words: list[str]) -> list[str]:
    cleaned = [word.strip().upper() for word in words]
    return [word for word in cleaned if word and not word.startswith("#")]


def _load_words() -> tuple[list[str], str]:
    script_words = _normalize_words(DEFAULT_WORDS)

    if WORDS_FILE.exists():
        file_words = _normalize_words(WORDS_FILE.read_text(encoding="utf-8").splitlines())
        if file_words:
            return file_words, str(WORDS_FILE)

    return script_words, "DEFAULT_WORDS in wordsearch.py"


@dataclass(slots=True)
class WordPlacement:
    word: str
    cells: list[tuple[int, int]]


@dataclass(slots=True)
class WordSearchResult:
    svg_path: Path
    answer_key_svg_path: Path
    png_path: Path | None = None
    answer_key_png_path: Path | None = None

    def __iter__(self) -> Iterator[Path | None]:
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


def _estimate_grid_size(words: list[str]) -> int:
    longest = max(len(word) for word in words)
    total_letters = sum(len(word) for word in words)
    area_estimate = int(math.ceil(math.sqrt(total_letters * 1.8)))
    return max(14, longest, area_estimate)


def _build_grid(words: list[str], rng: np.random.Generator) -> tuple[np.ndarray, list[WordPlacement]]:
    ordered_words = sorted(words, key=len, reverse=True)
    base_size = _estimate_grid_size(ordered_words)
    max_size = max(base_size + 6, 20)

    for size in range(base_size, max_size + 1):
        for _ in range(64):
            candidate = np.full((size, size), "", dtype="U1")
            try:
                placements = _place_words(candidate, ordered_words, rng)
                return candidate, placements
            except RuntimeError:
                continue

    raise RuntimeError(
        "Could not place all words in the word-search grid. "
        f"Tried sizes {base_size}..{max_size} for {len(words)} words; "
        f"longest word has {max(len(word) for word in words)} letters."
    )


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
    words, words_source = _load_words()
    grid, placements = _build_grid(words, rng)

    alphabet = np.array(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    empties = np.where(grid == "")
    grid[empties] = alphabet[rng.integers(0, len(alphabet), size=len(empties[0]))]

    puzzle_art, _, _, _, _, _ = _draw_grid_artwork(grid)
    answer_key_art = _draw_answer_key_artwork(grid, placements)
    output_dir.mkdir(parents=True, exist_ok=True)
    svg_path = output_dir / "wordsearch.svg"
    answer_key_svg_path = output_dir / "wordsearch_answer_key.svg"
    # Clean up legacy PNG outputs from older versions to avoid stale-file confusion.
    legacy_png_paths = [output_dir / "wordsearch.png", output_dir / "wordsearch_answer_key.png"]
    for legacy_png in legacy_png_paths:
        if legacy_png.exists():
            legacy_png.unlink()
    render_svg(puzzle_art, svg_path, PageConfig())
    render_svg(answer_key_art, answer_key_svg_path, PageConfig())
    print(f"Words source: {words_source}")

    return WordSearchResult(
        svg_path=svg_path,
        answer_key_svg_path=answer_key_svg_path,
    )


if __name__ == "__main__":
    run_generator_cli("wordsearch", "Generate the coffee word-search puzzle.", generate_wordsearch)
