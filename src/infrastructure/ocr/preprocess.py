import io

from PIL import Image, ImageFilter, ImageOps, ImageStat

from src.modules.menu_recognition.contracts import RecognitionError


def prepare_image(data: bytes) -> bytes:
    """Orient, enlarge small text and improve contrast without hard thresholding."""
    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.width * source.height > 30_000_000:
                raise RecognitionError("Image exceeds 30 megapixels")
            image = ImageOps.exif_transpose(source).convert("L")
            longest = max(image.size)
            target = max(2400, min(longest, 3600))
            if longest != target:
                scale = target / longest
                image = image.resize(
                    (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
                    Image.Resampling.LANCZOS,
                )
            if ImageStat.Stat(image).mean[0] < 100:
                image = ImageOps.invert(image)
            image = ImageOps.autocontrast(image)
            image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
            output = io.BytesIO()
            image.save(output, format="PNG")
            return output.getvalue()
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise RecognitionError("Invalid or oversized image") from exc
