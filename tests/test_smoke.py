from pathlib import Path

from coffee_activity_generator.main import GENERATORS


def test_all_generators_export_svg_and_png(tmp_path: Path) -> None:
    for i, generator in enumerate(GENERATORS.values()):
        svg_path, png_path = generator(10 + i, tmp_path)
        assert svg_path.exists()
        assert png_path.exists()
        assert svg_path.suffix == ".svg"
        assert png_path.suffix == ".png"
