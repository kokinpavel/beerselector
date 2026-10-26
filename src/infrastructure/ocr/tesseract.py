import asyncio
import csv
import io

from src.infrastructure.ocr.preprocess import prepare_image
from src.modules.menu_recognition.contracts import OcrUnavailable, RecognitionError


class TesseractReader:
    def __init__(
        self,
        executable: str = "tesseract",
        languages: str = "eng+rus",
        timeout: float = 30,
        page_segmentation: int = 3,
    ) -> None:
        self.executable = executable
        self.languages = languages
        self.timeout = timeout
        self.page_segmentation = page_segmentation
        self._slots = asyncio.Semaphore(1)

    async def read(self, image: bytes) -> str:
        async with self._slots:
            try:
                async with asyncio.timeout(self.timeout):
                    prepared = await asyncio.to_thread(prepare_image, image)
                    candidates = [await self._read(prepared, self.page_segmentation)]
                    candidates.append(await self._read(image, 6))
                    return max(candidates, key=lambda candidate: candidate[1])[0]
            except TimeoutError as exc:
                raise RecognitionError("OCR timed out") from exc

    async def _read(self, image: bytes, segmentation: int) -> tuple[str, float]:
        try:
            process = await asyncio.create_subprocess_exec(
                self.executable,
                "stdin",
                "stdout",
                "-l",
                self.languages,
                "--psm",
                str(segmentation),
                "--dpi",
                "300",
                "tsv",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise OcrUnavailable("Tesseract executable is unavailable") from exc
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(image), self.timeout)
        except (TimeoutError, asyncio.CancelledError) as exc:
            if process.returncode is None:
                process.kill()
            await process.wait()
            if isinstance(exc, asyncio.CancelledError):
                raise
            raise RecognitionError("OCR timed out") from exc
        if process.returncode:
            if b"traineddata" in stderr or b"Failed loading language" in stderr:
                raise OcrUnavailable("Tesseract language data is unavailable")
            raise RecognitionError("Tesseract could not read this image")
        return decode_tsv(stdout.decode("utf-8", errors="replace"))


def decode_tsv(text: str) -> tuple[str, float]:
    lines: dict[tuple[str, ...], list[str]] = {}
    weighted_confidence = 0.0
    characters = 0
    for row in csv.DictReader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE):
        word = (row.get("text") or "").strip()
        if not word or row.get("level") != "5":
            continue
        try:
            confidence = float(row["conf"])
        except KeyError, ValueError:
            continue
        if confidence < 0:
            continue
        key = tuple(
            row.get(field, "") for field in ("page_num", "block_num", "par_num", "line_num")
        )
        lines.setdefault(key, []).append(word)
        weight = len(word)
        weighted_confidence += confidence * weight
        characters += weight
    result = "\n".join(" ".join(words) for words in lines.values())
    score = weighted_confidence / characters + min(characters, 100) / 10 if characters else -1.0
    return result, score
