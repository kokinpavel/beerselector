import pytest
from pydantic import ValidationError

from src.core.config import Settings


@pytest.mark.parametrize("value", ["3", "6", "11"])
def test_ocr_segmentation_from_environment(monkeypatch, value):
    monkeypatch.setenv("OCR_PAGE_SEGMENTATION", value)
    assert Settings(_env_file=None).ocr_page_segmentation == int(value)


@pytest.mark.parametrize("value", ["0", "7", "invalid"])
def test_invalid_ocr_segmentation_is_rejected(monkeypatch, value):
    monkeypatch.setenv("OCR_PAGE_SEGMENTATION", value)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
