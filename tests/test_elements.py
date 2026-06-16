"""Tests for built-in elements rendering into a slide."""

from __future__ import annotations

import pytest
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from slides_factory.elements.card import CardElement, CardProps
from slides_factory.elements.text import TextElement, TextProps
from slides_factory.palette import SlidePalette
from slides_factory.render_context import RenderContext
from slides_factory.styling.tokens import parse_element


@pytest.fixture
def blank_slide():
    prs = Presentation()
    layout = next((lo for lo in prs.slide_layouts if lo.name == "Blank"), prs.slide_layouts[6])
    return prs.slides.add_slide(layout), prs


def _ctx(prs, **kwargs):
    return RenderContext(
        slide_width=int(prs.slide_width), slide_height=int(prs.slide_height), **kwargs
    )


def test_text_element_renders_text_and_bullets(blank_slide):
    slide, prs = blank_slide
    style = parse_element("text-lg font-bold text-primary")
    TextElement().render(
        slide,
        (914400, 914400, 3000000, 1500000),
        style,
        TextProps(text="Heading", bullets=["one", "two"]),
        _ctx(prs),
    )
    boxes = [s for s in slide.shapes if s.has_text_frame]
    assert boxes, "expected a text box"
    paragraphs = [p.text for p in boxes[0].text_frame.paragraphs]
    assert paragraphs[0] == "Heading"
    assert paragraphs[1] == "\u2022 one"
    assert paragraphs[2] == "\u2022 two"


def test_text_element_applies_palette_color(blank_slide):
    slide, prs = blank_slide
    palette = SlidePalette(text="#123456", highlight="#000000", main=("#FFFFFF",), extras=())
    style = parse_element("text-base text-primary")
    TextElement().render(
        slide,
        (0, 0, 2000000, 1000000),
        style,
        TextProps(text="Hi"),
        _ctx(prs, palette=palette),
    )
    box = next(s for s in slide.shapes if s.has_text_frame)
    run = box.text_frame.paragraphs[0].runs[0]
    assert str(run.font.color.rgb) == "123456"
    assert run.font.bold is None or run.font.bold is False


def test_card_element_draws_filled_shape_with_text(blank_slide):
    slide, prs = blank_slide
    palette = SlidePalette(text="#111111", highlight="#222222", main=("#EEEEEE",), extras=())
    style = parse_element("bg-surface rounded-md")
    CardElement().render(
        slide,
        (1000000, 1000000, 3000000, 2000000),
        style,
        CardProps(title="Revenue", value="$1.2M"),
        _ctx(prs, palette=palette),
    )
    shapes = [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE]
    assert shapes, "expected a card auto shape"
    card = shapes[0]
    assert str(card.fill.fore_color.rgb) == "EEEEEE"
    texts = [p.text for p in card.text_frame.paragraphs]
    assert "Revenue" in texts
    assert "$1.2M" in texts


def test_card_element_without_palette_uses_fallback_color(blank_slide):
    slide, prs = blank_slide
    style = parse_element("bg-surface")
    CardElement().render(
        slide,
        (0, 0, 2000000, 1000000),
        style,
        CardProps(value="42"),
        _ctx(prs),
    )
    card = next(s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE)
    assert str(card.fill.fore_color.rgb) == "F3F4F6"
