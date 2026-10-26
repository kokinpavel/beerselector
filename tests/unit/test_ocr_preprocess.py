import io

import pytest
from PIL import Image

from src.infrastructure.ocr.preprocess import prepare_image
from src.modules.menu_recognition.contracts import RecognitionError


def test_dark_small_image_becomes_large_light_background():
    image = Image.new("RGB", (400, 200), "black")
    image.putpixel((100, 100), (255, 255, 255))
    original = io.BytesIO()
    image.save(original, format="PNG")
    with Image.open(io.BytesIO(prepare_image(original.getvalue()))) as prepared:
        assert prepared.size == (2400, 1200)
        assert prepared.mode == "L"
        assert prepared.getpixel((0, 0)) == 255


def test_invalid_image_is_rejected():
    with pytest.raises(RecognitionError):
        prepare_image(b"not an image")
