import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.application.recognize_menu import MAX_IMAGE_BYTES, RecognizeMenu
from src.infrastructure.ocr.tesseract import TesseractReader
from src.modules.menu_recognition.contracts import OcrUnavailable, RecognitionError
from src.modules.menu_recognition.menu import parse_menu


@pytest.fixture(autouse=True)
def isolate_preprocessing(monkeypatch):
    monkeypatch.setattr("src.infrastructure.ocr.tesseract.prepare_image", lambda image: image)


def test_menu_rows_preserve_names_and_only_explicit_abv():
    raw = "BEER MENU\n1. West Tripel 8,5% 0.33l 600 руб\nUnknown Beer\n250\nLocal IPA 6.2%"
    draft = parse_menu(raw, "крепкое типа бельгия")
    assert len(draft.items) == 3
    assert draft.items[0].abv == 8.5
    assert draft.items[1].text == "Unknown Beer"
    assert draft.items[1].abv is None
    assert draft.items[2].abv == 6.2
    assert draft.raw_text == raw
    assert draft.caption == "крепкое типа бельгия"


@pytest.mark.parametrize("row", ["Beer 99%", "Beer 6% / 8%", "Beer 0.5l 350 руб"])
def test_menu_does_not_guess_ambiguous_or_missing_abv(row):
    assert parse_menu(row).items[0].abv is None


def test_menu_is_bounded_and_reports_truncation():
    draft = parse_menu("\n".join(f"Beer {i}" for i in range(100)))
    assert len(draft.items) == 60
    assert draft.truncated
    long = parse_menu("A" * 30_000)
    assert len(long.raw_text) == 20_000
    assert len(long.items[0].text) == 300
    assert long.truncated


async def test_recognition_calls_replaceable_reader():
    reader = SimpleNamespace(read=AsyncMock(return_value="Beer Tripel 8%"))
    cleaner = SimpleNamespace(clean=AsyncMock(return_value=["Beer Tripel"]))
    draft = await RecognizeMenu(reader, cleaner).execute(b"image", "хочу крепкое")
    reader.read.assert_awaited_once_with(b"image")
    assert draft.items[0].text == "Beer Tripel"
    assert draft.items[0].abv is None
    cleaner.clean.assert_awaited_once_with("Beer Tripel 8%")
    assert draft.caption == "хочу крепкое"


@pytest.mark.parametrize("image", [b"", b"x" * (MAX_IMAGE_BYTES + 1)])
async def test_reject_invalid_image_size_without_running_ocr(image):
    reader = SimpleNamespace(read=AsyncMock())
    with pytest.raises(RecognitionError):
        await RecognizeMenu(reader, SimpleNamespace(clean=AsyncMock())).execute(image)
    reader.read.assert_not_awaited()


async def test_missing_tesseract_has_actionable_error(monkeypatch):
    monkeypatch.setattr(
        asyncio, "create_subprocess_exec", AsyncMock(side_effect=FileNotFoundError())
    )
    with pytest.raises(OcrUnavailable):
        await TesseractReader().read(b"image")


@pytest.mark.parametrize(
    "stderr, error",
    [
        (b"Failed loading language rus traineddata", OcrUnavailable),
        (b"Invalid image", RecognitionError),
    ],
)
async def test_native_ocr_failures_are_translated(monkeypatch, stderr, error):
    process = SimpleNamespace(returncode=1, communicate=AsyncMock(return_value=(b"", stderr)))
    monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(return_value=process))
    with pytest.raises(error):
        await TesseractReader().read(b"image")


async def test_ocr_timeout_kills_and_reaps_child(monkeypatch):
    process = SimpleNamespace(returncode=None, kill=Mock(), wait=AsyncMock())

    async def hang(image):
        await asyncio.Event().wait()

    process.communicate = hang
    monkeypatch.setattr(asyncio, "create_subprocess_exec", AsyncMock(return_value=process))
    with pytest.raises(RecognitionError, match="timed out"):
        await TesseractReader(timeout=0.01).read(b"image")
    process.kill.assert_called_once()
    process.wait.assert_awaited_once()


async def test_ocr_uses_stdin_and_argument_list(monkeypatch):
    process = SimpleNamespace(
        returncode=0,
        communicate=AsyncMock(
            return_value=(
                (
                    b"level\tpage_num\tblock_num\tpar_num\tline_num\tconf\ttext\n"
                    b"5\t1\t1\t1\t1\t90\tTripel\n5\t1\t1\t1\t1\t90\t8%\n"
                ),
                b"",
            )
        ),
    )
    spawn = AsyncMock(return_value=process)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    assert await TesseractReader().read(b"image") == "Tripel 8%"
    process.communicate.assert_awaited_with(b"image")
    assert spawn.call_args.args[:3] == ("tesseract", "stdin", "stdout")


async def test_ocr_prefers_more_confident_original_over_preprocessing(monkeypatch):
    from src.infrastructure.ocr.tesseract import decode_tsv

    header = "level\tpage_num\tblock_num\tpar_num\tline_num\tconf\ttext\n"
    poor = decode_tsv(header + "5\t1\t1\t1\t1\t20\tgarbage\n")
    good = decode_tsv(header + "5\t1\t1\t1\t1\t95\tTripel\n")
    reader = TesseractReader()
    monkeypatch.setattr(reader, "_read", AsyncMock(side_effect=[poor, good]))
    assert await reader.read(b"image") == "Tripel"
