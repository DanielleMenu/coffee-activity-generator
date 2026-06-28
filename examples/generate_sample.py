"""Generate a sample set of activity pages.

Run:
    python examples/generate_sample.py
"""

from pathlib import Path

from coffee_activity_generator.main import GENERATORS


if __name__ == "__main__":
    out = Path("coffee_activity_generator/exports/samples")
    out.mkdir(parents=True, exist_ok=True)
    for i, (name, gen) in enumerate(GENERATORS.items()):
        gen(100 + i, out)
    print(f"Generated {len(GENERATORS)} sample pages in {out}")
