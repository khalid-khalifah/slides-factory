"""Render single-slide previews for visual testing."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from slides_factory import document

if TYPE_CHECKING:
    from slides_factory.app import SlideFactory


def find_soffice() -> Path | None:
    """Return LibreOffice ``soffice`` binary if installed."""
    for candidate in (
        shutil.which("soffice"),
        shutil.which("libreoffice"),
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ):
        if candidate:
            path = Path(candidate)
            if path.is_file():
                return path
    return None


def presentation_to_bytes(prs) -> bytes:
    """Serialize a presentation to bytes (embeds brand fonts when configured)."""
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as handle:
        path = Path(handle.name)
    try:
        document.save_document(prs, path)
        return path.read_bytes()
    finally:
        path.unlink(missing_ok=True)


def render_preview_pptx(
    template_id: str,
    data: dict[str, Any],
    *,
    app: SlideFactory,
    brand: Path | None = None,
    frame: str | None = None,
    rtl: bool = False,
    locale: str = "en",
) -> bytes:
    """Render one slide and return the .pptx file as bytes."""
    prs = document.new_presentation(brand=brand, rtl=rtl, locale=locale)
    document.add_slide(
        prs,
        template_id,
        data,
        app=app,
        frame=frame,
        rtl=rtl,
        locale=locale,
    )
    return presentation_to_bytes(prs)


def pptx_bytes_to_pngs(pptx_bytes: bytes) -> list[bytes]:
    """Convert a single-slide .pptx to PNG bytes via LibreOffice (empty if unavailable)."""
    soffice = find_soffice()
    if soffice is None:
        return []

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        pptx_path = tmp / "preview.pptx"
        outdir = tmp / "out"
        outdir.mkdir()
        pptx_path.write_bytes(pptx_bytes)
        result = subprocess.run(
            [
                str(soffice),
                "--headless",
                "--convert-to",
                "png",
                "--outdir",
                str(outdir),
                str(pptx_path),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return []
        return [path.read_bytes() for path in sorted(outdir.glob("*.png"))]
