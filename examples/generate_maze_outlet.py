"""Generate the outlet-rescue maze example.

Run:
    python examples/generate_maze_outlet.py
"""

from pathlib import Path

from coffee_activity_generator.generators.maze import generate_maze


if __name__ == "__main__":
    out_dir = Path("coffee_activity_generator/exports/examples")
    result = generate_maze(
        seed=42,
        output_dir=out_dir,
        width=14,
        height=20,
        difficulty="hard",
        title="Help the freelancer reach the last available outlet.",
        subtitle="Start at the arrow and finish at the coffee cup.",
    )

    print(f"SVG: {result.svg_path}")
    print(f"PNG: {result.png_path}")
    print(f"Cells: {result.maze.width}x{result.maze.height}")
