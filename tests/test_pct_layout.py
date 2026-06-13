"""Edge cases for percent-based layout helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
from pptx.util import Cm, Inches

from slides_factory.brand.logos import resolve_flat_logo_key, resolve_logo_key
from slides_factory.layout.pct import (
    LOGO_WIDTH_CM,
    LogoPlacement,
    PctBox,
    image_aspect_ratio,
    resolve_logo_placement,
    resolve_pct_box,
)
from slides_factory.render_context import RenderContext


def test_resolve_pct_box_ltr_and_rtl():
    sw = int(Inches(13.333))
    sh = int(Inches(7.5))
    box = PctBox(left=84.4, top=7.5, width=11.6, height=5.9, mirror_rtl=True)
    ctx_ltr = RenderContext(rtl=False, slide_width=sw, slide_height=sh)
    left_ltr, top, width, height = resolve_pct_box(ctx_ltr, box)
    assert left_ltr == int(sw * 84.4 / 100)
    assert top == int(sh * 7.5 / 100)
    assert width == int(sw * 11.6 / 100)

    ctx_rtl = RenderContext(rtl=True, slide_width=sw, slide_height=sh)
    left_rtl, _, _, _ = resolve_pct_box(ctx_rtl, box)
    assert left_rtl != left_ltr
    assert left_rtl < left_ltr


def test_resolve_logo_keys_from_locale():
    sw, sh = 1000, 750
    assert (
        resolve_logo_key(RenderContext(rtl=False, locale="en", slide_width=sw, slide_height=sh))
        == "en"
    )
    assert (
        resolve_logo_key(RenderContext(rtl=True, locale="ar", slide_width=sw, slide_height=sh))
        == "ar"
    )
    assert (
        resolve_logo_key(
            RenderContext(rtl=False, locale="en", slide_width=sw, slide_height=sh),
            inverted=True,
        )
        == "en_inverted"
    )


def test_resolve_flat_logo_key_from_locale():
    sw, sh = 1000, 750
    assert (
        resolve_flat_logo_key(
            RenderContext(rtl=False, locale="en", slide_width=sw, slide_height=sh),
            color="white",
        )
        == "en_flat_white"
    )
    assert (
        resolve_flat_logo_key(
            RenderContext(rtl=True, locale="ar", slide_width=sw, slide_height=sh),
            color="black",
        )
        == "ar_flat_black"
    )


def test_logo_placement_preserves_aspect_ratio(tmp_path: Path):
    from PIL import Image

    logo = tmp_path / "logo.png"
    Image.new("RGB", (400, 100), color="white").save(logo)

    sw = int(Inches(10))
    sh = int(Inches(7.5))
    ctx = RenderContext(rtl=False, slide_width=sw, slide_height=sh)
    placement = LogoPlacement(left=10, top=5, width=20, mirror_rtl=False)
    _, _, width, height = resolve_logo_placement(ctx, placement, logo)

    assert width == int(Cm(LOGO_WIDTH_CM))
    assert height == pytest.approx(int(width / image_aspect_ratio(logo)))
