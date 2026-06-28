# coffee-activity-generator

Generate black-and-white printable activity pages for a humorous **Department of Coffee Research** activity book.

All pages are designed for Amazon KDP trim size **6x9 inches at 300 DPI**, exported as both **SVG** (vector-first) and **PNG**.

## Features

- Python 3.12+
- Reproducible generation via random seed
- Shared reusable rendering primitives across all activities
- Module-per-activity architecture with type hints and docs
- CLI entry point for each generator and a global CLI
- Optional PDF assembly from generated PNG pages (via ReportLab)

## Project structure

```text
coffee_activity_generator/
├── generators/
│   ├── maze.py
│   ├── connect_dots.py
│   ├── floorplan.py
│   ├── seat_selection.py
│   ├── coffee_flow.py
│   ├── queue_logic.py
│   ├── wordsearch.py
│   ├── hidden_objects.py
│   └── spot_difference.py
├── assets/
├── exports/
├── common.py
├── cli.py
├── render.py
└── main.py

examples/
tests/
main.py
requirements.txt
README.md
```

## Install

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Usage

Generate one activity:

```bash
python main.py maze --seed 42
```

Generate all activities:

```bash
python main.py all --seed 42
```

Generate all plus a merged PDF:

```bash
python main.py all --seed 42 --pdf
```

Run individual module CLIs:

```bash
python -m coffee_activity_generator.generators.wordsearch --seed 123
python -m coffee_activity_generator.generators.floorplan --seed 123
```

Outputs are written to `coffee_activity_generator/exports/` by default.

## Activity set

- Maze: Espresso Escape
- Connect the Dots: Beverage prototype reveal
- Floorplan: Barista route planning
- Seat Selection: Logic puzzle
- Coffee Flow: Process-completion chart
- Queue Logic: Dependency ordering challenge
- Word Search: Coffee vocabulary grid
- Hidden Objects: Clutter-scene search
- Spot the Difference: Two-panel mismatch puzzle

## Testing

```bash
pytest
```

## Design notes

- Visual language is intentionally minimalist monochrome line art.
- Slight geometric jitter is used to avoid sterile computer-perfect lines.
- Header branding follows a playful "Department of Coffee Research" tone.
