"""Word-search puzzle generator.

Example:
    python -m coffee_activity_generator.generators.wordsearch --seed 42
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..cli import run_generator_cli
from ..common import Artwork, Label, StrokePath, add_department_header, seeded_rng
from ..render import export_artwork

WORDS = ["LATTE", "BEAN", "CREMA", "MUG", "ROAST", "FOAM"]


def _place_words(grid: np.ndarray, words: list[str], rng: np.random.Generator) -> None:
    directions = [(1, 0), (0, 1), (1, 1), (-1, 1)]
    n = grid.shape[0]

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
            break
        if not placed:
            raise RuntimeError(f"Could not place word: {word}")


def generate_wordsearch(seed: int | None, output_dir: Path) -> tuple[Path, Path]:
    """Generate a coffee-themed printable word-search."""

    rng = seeded_rng(seed)
    size = 12
    grid = np.full((size, size), "", dtype="U1")
    _place_words(grid, WORDS, rng)

    alphabet = np.array(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    empties = np.where(grid == "")
    grid[empties] = alphabet[rng.integers(0, len(alphabet), size=len(empties[0]))]

    art = Artwork(title="Word Search", subtitle="Find all classified coffee terms")
    add_department_header(art)

    x0, y0, w = 0.14, 0.20, 0.72
    cell = w / size

    for i in range(size + 1):
        x = x0 + i * cell
        y = y0 + i * cell
        art.paths.append(StrokePath([(x, y0), (x, y0 + w)], width=1.0))
        art.paths.append(StrokePath([(x0, y), (x0 + w, y)], width=1.0))

    for r in range(size):
        for c in range(size):
            art.labels.append(Label((x0 + c * cell + cell * 0.5, y0 + r * cell + cell * 0.58), grid[r, c], size=10, anchor="middle"))

    art.labels.append(Label((0.14, 0.87), "Words:", size=12))
    art.labels.append(Label((0.14, 0.91), "  ".join(WORDS), size=11))
    return export_artwork(art, "wordsearch", output_dir)


if __name__ == "__main__":
    run_generator_cli("wordsearch", "Generate the coffee word-search puzzle.", generate_wordsearch)
