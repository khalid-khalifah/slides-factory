"""Percentage-based boxes relative to slide width and height.

Functions:
    _coerce_pct_number      — Coerce int/float/str to a float percent value.
    image_aspect_ratio      — Return image width / height in pixels for logo sizing.
    resolve_pct_box         — Return (left, top, width, height) in EMU for a percent box.
    resolve_logo_placement  — Return EMU box for logo: fixed cm width, height from aspect ratio.

Classes:
    PctBox        — Percent-based bounding box (left, top, width, height).
    LogoPlacement — Logo anchor with optional mirror_rtl flag.
"""

from __future__ import annotations

from pathlib import Path

from pptx.util import Cm
from pydantic import BaseModel, Field, field_validator, model_validator

from slides_factory.geometry import Box
from slides_factory.render_context import RenderContext

LOGO_WIDTH_CM = 3.93
LOGO_WIDTH_PRESENTATION_TITLE_CM = 5.37


class PctBox(BaseModel):
    """Rectangle expressed as percent of slide width (horizontal) and height (vertical)."""

    left: float = Field(ge=0, le=100, description="Distance from left edge, % of slide width.")
    top: float = Field(ge=0, le=100, description="Distance from top edge, % of slide height.")
    width: float = Field(gt=0, le=100, description="Width as % of slide width.")
    height: float = Field(gt=0, le=100, description="Height as % of slide height.")
    mirror_rtl: bool = Field(
        default=True,
        description="When True and ctx.rtl, flip horizontal position for RTL decks.",
    )

    @field_validator("left", "top", "width", "height", mode="before")
    @classmethod
    def _coerce_number(cls, value: object) -> float:
        return _coerce_pct_number(value)


class LogoPlacement(BaseModel):
    """Logo anchor on the slide; horizontal position uses ``left`` or ``right`` % margin."""

    left: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Distance from left edge, % of slide width (Arabic / LTR left anchor).",
    )
    right: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Distance from right edge, % of slide width (English / right anchor).",
    )
    top: float = Field(ge=0, le=100, description="Distance from top edge, % of slide height.")
    width: float = Field(
        default=11.6,
        gt=0,
        le=100,
        description="Legacy width % (logo width is set in cm at render time).",
    )
    mirror_rtl: bool = Field(
        default=True,
        description="When True and ctx.rtl, flip horizontal position for RTL decks.",
    )

    @field_validator("left", "right", "top", "width", mode="before")
    @classmethod
    def _coerce_number(cls, value: object) -> float | None:
        if value is None:
            return None
        return _coerce_pct_number(value)

    @model_validator(mode="after")
    def _require_horizontal_anchor(self) -> LogoPlacement:
        if self.left is None and self.right is None:
            raise ValueError("LogoPlacement requires left or right")
        return self


def _coerce_pct_number(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value.strip().rstrip("%"))
    raise TypeError("expected a number or numeric string")


def image_aspect_ratio(image_path: Path | str) -> float:
    """Return image width / height in pixels (used to preserve logo proportions)."""
    from PIL import Image

    with Image.open(image_path) as img:
        w, h = img.size
    if h <= 0:
        raise ValueError(f"invalid image height: {image_path}")
    return w / h


def resolve_pct_box(ctx: RenderContext, box: PctBox) -> Box:
    """Return a :class:`Box` in EMU for the given percent box."""
    sw = ctx.slide_width
    sh = ctx.slide_height
    if sw <= 0 or sh <= 0:
        raise ValueError("RenderContext must include slide_width and slide_height")

    width = int(sw * box.width / 100)
    height = int(sh * box.height / 100)
    left = int(sw * box.left / 100)
    top = int(sh * box.top / 100)

    if box.mirror_rtl and ctx.rtl:
        left = ctx.mirror_left(left, width)

    left = max(0, min(left, sw - width))
    top = max(0, min(top, sh - height))
    return Box(left, top, width, height)


def resolve_logo_placement(
    ctx: RenderContext,
    placement: LogoPlacement,
    image_path: Path | str,
    *,
    width_cm: float = LOGO_WIDTH_CM,
) -> tuple[int, int, int, int]:
    """Return EMU box for a logo: fixed width in cm, height from image aspect ratio."""
    sw = ctx.slide_width
    sh = ctx.slide_height
    if sw <= 0 or sh <= 0:
        raise ValueError("RenderContext must include slide_width and slide_height")

    width = int(Cm(width_cm))
    ratio = image_aspect_ratio(image_path)
    height = int(width / ratio)
    top = int(sh * placement.top / 100)

    if placement.right is not None:
        margin = int(sw * placement.right / 100)
        left = sw - margin - width
    else:
        left = int(sw * placement.left / 100)
        if placement.mirror_rtl and ctx.rtl:
            left = ctx.mirror_left(left, width)

    left = max(0, min(left, sw - width))
    top = max(0, min(top, sh - height))
    return left, top, width, height
