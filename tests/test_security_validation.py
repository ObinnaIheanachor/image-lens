from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from src.domain.errors import ValidationError
from src.security.validation import validate_image_bytes


def _make_png(width: int = 16, height: int = 16) -> bytes:
    img = Image.new("RGB", (width, height), (10, 20, 30))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_jpeg(width: int = 16, height: int = 16) -> bytes:
    img = Image.new("RGB", (width, height), (200, 120, 10))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_validate_image_bytes_accepts_png() -> None:
    payload = _make_png(20, 12)
    out = validate_image_bytes(
        payload,
        max_size_bytes=1024 * 1024,
        max_width=1000,
        max_height=1000,
    )
    assert out.mime == "image/png"
    assert out.suffix == ".png"
    assert out.width == 20
    assert out.height == 12
    assert out.size_bytes == len(payload)


def test_validate_image_bytes_rejects_empty_and_too_large() -> None:
    with pytest.raises(ValidationError) as empty:
        validate_image_bytes(
            b"",
            max_size_bytes=10,
            max_width=100,
            max_height=100,
        )
    assert empty.value.code == "empty_file"
    assert empty.value.status_code == 400

    with pytest.raises(ValidationError) as too_large:
        validate_image_bytes(
            b"\x89PNG\r\n\x1a\n" + b"x" * 32,
            max_size_bytes=8,
            max_width=100,
            max_height=100,
        )
    assert too_large.value.code == "payload_too_large"
    assert too_large.value.status_code == 413


def test_validate_image_bytes_rejects_pdf_and_unknown_magic() -> None:
    with pytest.raises(ValidationError) as pdf:
        validate_image_bytes(
            b"%PDF-1.7 fake",
            max_size_bytes=1024,
            max_width=100,
            max_height=100,
        )
    assert pdf.value.code == "unsupported_media_type"
    assert pdf.value.status_code == 415

    with pytest.raises(ValidationError) as unknown:
        validate_image_bytes(
            b"not-an-image",
            max_size_bytes=1024,
            max_width=100,
            max_height=100,
        )
    assert unknown.value.code == "unsupported_media_type"
    assert unknown.value.status_code == 415


def test_validate_image_bytes_rejects_invalid_dimensions() -> None:
    payload = _make_jpeg(64, 64)
    with pytest.raises(ValidationError) as err:
        validate_image_bytes(
            payload,
            max_size_bytes=1024 * 1024,
            max_width=10,
            max_height=10,
        )
    assert err.value.code == "invalid_dimensions"
    assert err.value.status_code == 422


def test_validate_image_bytes_handles_decode_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    class _BrokenImg:
        size = (12, 12)

        def verify(self) -> None:
            raise RuntimeError("boom")

    monkeypatch.setattr("src.security.validation.Image.open", lambda _buf: _BrokenImg())

    with pytest.raises(ValidationError) as jpeg_err:
        validate_image_bytes(
            b"\xff\xd8\xffjunk",
            max_size_bytes=1024,
            max_width=100,
            max_height=100,
        )
    assert jpeg_err.value.code == "image_decode_failed"
    assert jpeg_err.value.status_code == 422

    with pytest.raises(ValidationError) as webp_err:
        validate_image_bytes(
            b"RIFFabcdWEBPjunk",
            max_size_bytes=1024,
            max_width=100,
            max_height=100,
        )
    assert webp_err.value.code == "unsupported_media_type"
    assert webp_err.value.status_code == 415

    with pytest.raises(ValidationError) as heic_err:
        validate_image_bytes(
            b"\x00\x00\x00\x18ftypheicjunk",
            max_size_bytes=1024,
            max_width=100,
            max_height=100,
        )
    assert heic_err.value.code == "unsupported_media_type"
    assert heic_err.value.status_code == 415
