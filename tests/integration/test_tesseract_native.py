import shutil
from pathlib import Path

import pytest

from src.infrastructure.ocr.tesseract import TesseractReader
from src.modules.menu_recognition.menu import parse_menu


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Native OCR runs in Docker")
async def test_real_tesseract_recognizes_generated_menu():
    image = (Path(__file__).resolve().parents[1] / "fixtures/menu_sample.pbm").read_bytes()
    draft = parse_menu(await TesseractReader().read(image))
    assert any("TRIPEL" in row.text.upper() and row.abv == 8 for row in draft.items)
    assert any("LAGER" in row.text.upper() and row.abv == 5 for row in draft.items)
