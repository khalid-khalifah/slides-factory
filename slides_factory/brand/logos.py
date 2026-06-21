"""Resolve brand logo files for python-pptx (prefer PNG; rasterize SVG if needed).

Functions:
    resolve_raster_logo      — Return a PNG path suitable for Pillow and python-pptx.
    rasterize_svg            — Convert SVG to PNG using rsvg-convert (librsvg).
    locale_logo_base         — Return ``en`` or ``ar`` from document locale / RTL.
    resolve_logo_key         — Pick logo catalog key from explicit id or locale / RTL.
    resolve_flat_logo_key    — Pick flat icon logo key (``en_flat_white``, ``ar_flat_black``, …).
    _resolve_logo_placement  — Look up percent anchor from locale layout (``en`` or ``ar``).
    place_header_logo        — Place header logo at brand position with fixed cm width.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Literal


def resolve_raster_logo(path: Path) -> Path:
    """Return a PNG path suitable for Pillow and python-pptx.

    Raster images (``.png``, ``.jpg``, …) are returned as-is. For ``.svg``,
    uses a sibling ``.png`` when present or runs ``rsvg-convert`` to create one.
    """
    if path.suffix.lower() != ".svg":
        return path

    png_path = path.with_suffix(".png")
    if png_path.is_file() and png_path.stat().st_mtime >= path.stat().st_mtime:
        return png_path

    if png_path.is_file():
        return png_path

    rasterize_svg(path, png_path)
    return png_path


def rasterize_svg(svg_path: Path, png_path: Path) -> None:
    """Convert SVG to PNG using rsvg-convert (from librsvg)."""
    rsvg = shutil.which("rsvg-convert")
    if not rsvg:
        raise FileNotFoundError(
            f"PNG not found for {svg_path.name} and rsvg-convert is not installed. "
            f"Either commit {png_path.name} next to the SVG or install librsvg "
            "(e.g. brew install librsvg) and run: uv run python scripts/rasterize_logos.py"
        )
    subprocess.run(
        [rsvg, "-w", "2000", str(svg_path.resolve()), "-o", str(png_path.resolve())],
        check=True,
    )


def locale_logo_base(ctx) -> str:
    """Return ``en`` or ``ar`` from document locale / RTL."""
    if ctx.rtl or ctx.locale.startswith(("ar", "fa", "he", "ur")):
        return "ar"
    return "en"


def resolve_logo_key(ctx, explicit: str = "header", *, inverted: bool = False) -> str:
    """Pick logo catalog key from explicit id or document locale / RTL."""
    if explicit != "header":
        return explicit
    base = locale_logo_base(ctx)
    return f"{base}_inverted" if inverted else base


def resolve_flat_logo_key(ctx, *, color: Literal["white", "black"]) -> str:
    """Pick flat icon logo key (``en_flat_white``, ``ar_flat_black``, …)."""
    base = locale_logo_base(ctx)
    suffix = "flat_white" if color == "white" else "flat_black"
    return f"{base}_{suffix}"


def _resolve_logo_placement(brand, logo_key: str):
    """Look up percent anchor from the locale layout (``en`` or ``ar``)."""
    from slides_factory.layout.pct import LogoPlacement

    placement = brand.logo_placement(logo_key)
    if placement is not None:
        return placement
    if logo_key.startswith("ar"):
        return LogoPlacement(left=4.35, top=7.5, mirror_rtl=False)
    return LogoPlacement(right=4.0, top=7.5, mirror_rtl=False)


def place_header_logo(
    slide,
    ctx,
    *,
    key: str = "header",
    inverted: bool = False,
    logo_key: str | None = None,
    width_cm: float | None = None,
    placement=None,
) -> None:
    """Place a header logo (wordmark or flat) at brand position with fixed cm width."""
    from slides_factory.layout.pct import LOGO_WIDTH_CM, resolve_logo_placement

    logo_width = LOGO_WIDTH_CM if width_cm is None else width_cm

    if ctx.brand is None:
        raise ValueError("place_header_logo requires a brand theme on RenderContext")
    brand = ctx.brand

    if logo_key is None:
        logo_key = resolve_logo_key(ctx, key, inverted=inverted)

    try:
        logo_path = brand.resolve_logo_raster(logo_key)
    except (ImportError, OSError, ValueError):
        return
    if logo_path is None or not logo_path.is_file():
        return

    if placement is None:
        placement = _resolve_logo_placement(brand, logo_key)
    left, top, width, height = resolve_logo_placement(
        ctx, placement, logo_path, width_cm=logo_width
    )
    slide.shapes.add_picture(str(logo_path), left, top, width=width, height=height)
