from pathlib import Path

from coffee_activity_generator.main import GENERATORS
from coffee_activity_generator.generators.wordsearch import generate_wordsearch


def test_all_generators_export_svg_and_png(tmp_path: Path) -> None:
    for i, generator in enumerate(GENERATORS.values()):
        svg_path, png_path = generator(10 + i, tmp_path)
        assert svg_path.exists()
        assert png_path.exists()
        assert svg_path.suffix == ".svg"
        assert png_path.suffix == ".png"


def test_wordsearch_exports_answer_key(tmp_path: Path) -> None:
    result = generate_wordsearch(42, tmp_path)
    assert result.answer_key_svg_path.exists()
    assert result.answer_key_png_path.exists()
    assert result.answer_key_svg_path.suffix == ".svg"
    assert result.answer_key_png_path.suffix == ".png"
