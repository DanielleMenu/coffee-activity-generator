"""Word-search puzzle generator.

Example:
    python -m coffee_activity_generator.generators.wordsearch --seed 42
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..cli import run_generator_cli
from ..common import Artwork, Label, seeded_rng
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
    size = 14

    grid: np.ndarray | None = None
    for _ in range(32):
        candidate = np.full((size, size), "", dtype="U1")
        try:
            _place_words(candidate, WORDS, rng)
            grid = candidate
            break
        except RuntimeError:
            continue

    if grid is None:
        raise RuntimeError("Could not place all words in the word-search grid.")

    alphabet = np.array(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    empties = np.where(grid == "")
    grid[empties] = alphabet[rng.integers(0, len(alphabet), size=len(empties[0]))]

    art = Artwork(title="", subtitle="")

    # Use a square letter area centered on the 6x9 page, with no visible table.
    w = 0.82
    x0 = (1.0 - w) / 2.0
    y0 = (1.0 - w) / 2.0
    cell = w / size
    letter_size = int((cell * 1800) * 0.58)

    for r in range(size):
        for c in range(size):
            art.labels.append(
                Label(
                    (x0 + c * cell + cell * 0.5, y0 + r * cell + cell * 0.57),
                    str(grid[r, c]),
                    size=letter_size,
                    anchor="middle",
                )
            )

    return export_artwork(art, "wordsearch", output_dir)


if __name__ == "__main__":
    run_generator_cli("wordsearch", "Generate the coffee word-search puzzle.", generate_wordsearch)
