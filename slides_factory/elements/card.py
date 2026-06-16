"""Card element — a filled (optionally rounded/bordered) box with stat text."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR
from pptx.slide import Slide

from slides_factory.brand import hex_to_rgb
from slides_factory.elements.base import Box, Element, style_paragraph
from slides_factory.layout.fonts import apply_shape_font
from slides_factory.render_context import RenderContext
from slides_factory.styling import theme
from slides_factory.styling.tokens import ElementStyle


class CardProps(BaseModel):
    """Props for the card element."""

    title: str = ""
    value: str = ""
    body: str = ""


class CardElement(Element):
    """Render a filled card with optional title / value / body text."""

    kind: ClassVar[str] = "card"
    props_model: ClassVar[type[BaseModel]] = CardProps

    def render(
        self,
        slide: Slide,
        box: Box,
        style: ElementStyle,
        props: BaseModel,
        ctx: RenderContext,
    ) -> None:
        assert isinstance(props, CardProps)
        left, top, width, height = box
        shape_kind = (
            MSO_SHAPE.ROUNDED_RECTANGLE if style.radius else MSO_SHAPE.RECTANGLE
        )
        shape = slide.shapes.add_shape(shape_kind, left, top, width, height)

        if style.radius and shape.adjustments:
            shape.adjustments[0] = min(0.5, max(0.0, style.radius))

        bg_token = style.bg_color or "surface"
        shape.fill.solid()
        shape.fill.fore_color.rgb = hex_to_rgb(theme.resolve_color_token(bg_token, ctx.palette))

        if style.border:
            shape.line.fill.solid()
            border_token = style.text_color or "primary"
            shape.line.color.rgb = hex_to_rgb(theme.resolve_color_token(border_token, ctx.palette))
        else:
            shape.line.fill.background()

        frame = shape.text_frame
        frame.word_wrap = True
        frame.vertical_anchor = MSO_ANCHOR.MIDDLE

        value_size = style.font_size_pt or theme.font_size_pt("2xl")
        value_color = style.text_color or "primary"

        rows: list[tuple[str, float, bool, str]] = []
        if props.title:
            rows.append((props.title, theme.font_size_pt("sm"), False, "muted"))
        if props.value:
            rows.append((props.value, value_size, True, value_color))
        if props.body:
            rows.append((props.body, theme.font_size_pt("base"), False, "primary"))
        if not rows:
            rows.append(("", theme.font_size_pt("base"), False, "primary"))

        for index, (content, size_pt, bold, color_token) in enumerate(rows):
            paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
            paragraph.text = content
            style_paragraph(
                paragraph,
                ctx,
                size_pt=size_pt,
                bold=bold,
                color_token=color_token,
                align=style.align or "center",
            )

        apply_shape_font(shape, ctx)
