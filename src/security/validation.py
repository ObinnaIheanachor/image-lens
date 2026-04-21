from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from PIL import Image, UnidentifiedImageError

from src.domain.errors import ValidationError


@dataclass
class ValidatedImage:
    mime: str
    suffix: str
    width: int
    height: int
    size_bytes: int


SUPPORTED_MAGIC = {
    b"\xff\xd8\xff": ("image/jpeg", ".jpg"),
    b"\x89PNG\r\n\x1a\n": ("image/png", ".png"),
}


def _detect_mime(data: bytes) -> tuple[str, str] | None:
    if data.startswith(b"RIFF") and len(data) > 12 and data[8:12] == b"WEBP":
        return ("image/webp", ".webp")
    if b"ftypheic" in data[:64] or b"ftypheif" in data[:64]:
        return ("image/heic", ".heic")
    for magic, result in SUPPORTED_MAGIC.items():
        if data.startswith(magic):
            return result
    return None


def validate_image_bytes(
    image_bytes: bytes,
    *,
    max_size_bytes: int,
    max_width: int,
    max_height: int,
) -> ValidatedImage:
    if len(image_bytes) == 0:
        raise ValidationError("empty_file", "File is empty", status_code=400)
    if len(image_bytes) > max_size_bytes:
        raise ValidationError("payload_too_large", "File exceeds size limit", status_code=413)
    if image_bytes.startswith(b"%PDF-"):
        raise ValidationError("unsupported_media_type", "PDF masquerading as image", status_code=415)

    mime_result = _detect_mime(image_bytes)
    if not mime_result:
        raise ValidationError("unsupported_media_type", "Unsupported media type", status_code=415)
    mime, suffix = mime_result

    try:
        img = Image.open(BytesIO(image_bytes))
        width, height = img.size
        img.verify()
    except UnidentifiedImageError as exc:
        raise ValidationError("unsupported_media_type", "Unsupported media type", status_code=415) from exc
    except Exception as exc:
        if mime in {"image/webp", "image/heic"}:
            raise ValidationError("unsupported_media_type", "Unsupported media type", status_code=415) from exc
        raise ValidationError("image_decode_failed", "Image decode failed", status_code=422) from exc

    if width <= 0 or height <= 0 or width > max_width or height > max_height:
        raise ValidationError("invalid_dimensions", "Image dimensions out of bounds", status_code=422)

    return ValidatedImage(
        mime=mime,
        suffix=suffix,
        width=width,
        height=height,
        size_bytes=len(image_bytes),
    )
