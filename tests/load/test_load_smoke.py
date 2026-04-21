from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

from PIL import Image

from src.config import settings


def _make_jpeg(color: tuple[int, int, int]) -> bytes:
    img = Image.new("RGB", (24, 24), color)
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_load_smoke_multiple_uploads(client) -> None:
    headers = {"Authorization": f"Bearer {settings.api_key}"}

    def _upload(i: int) -> int:
        payload = _make_jpeg((i * 5 % 255, 50, 80))
        resp = client.post(
            "/api/v1/uploads",
            headers=headers,
            files={"file": (f"img-{i}.jpg", payload, "image/jpeg")},
        )
        return resp.status_code

    with ThreadPoolExecutor(max_workers=6) as pool:
        statuses = list(pool.map(_upload, range(12)))

    assert all(code == 202 for code in statuses)
