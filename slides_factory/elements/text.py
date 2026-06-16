"""Text element — a titled/body/bulleted text box placed in a cell."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel
from pptx.slide import Slide

from slides_factory.elements.base import (
    Box,
    Element,
    apply_box_padding,
    style_paragraph,
    vertical_anchor,
)
from slides_factory.layout.fonts import apply_shape_font
from slides_factory.render_context import RenderContext
from slides_factory.styling.tokens import ElementStyle


class TextProps(BaseModel):
    """Props for the text element."""

    text: str = ""
    bullets: list[str] = []


class TextElement(Element):
    """Render text and optional bullet lines into a cell box."""

    kind: ClassVar[str] = "text"
    props_model: ClassVar[type[BaseModel]] = TextProps

    def render(
        self,
        slide: Slide,
        box: Box,
        style: ElementStyle,
        props: BaseModel,
        ctx: RenderContext,
    ) -> None:
        assert isinstance(props, TextProps)
        left, top, width, height = apply_box_padding(box, style)
        textbox = slide.shapes.add_textbox(left, top, width, height)
        frame = textbox.text_frame
        frame.word_wrap = True
        frame.vertical_anchor = vertical_anchor(style)

        lines: list[tuple[str, bool]] = []
        if props.text:
            lines.append((props.text, False))
        for bullet in props.bullets:
            lines.append((f"\u2022 {bullet}", True))
        if not lines:
            lines.append(("", False))

        for index, (content, is_bullet) in enumerate(lines):
            paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
            paragraph.text = content
            # Bullet lines fall back to body weight even if the block is bold.
            bold = False if (is_bullet and style.bold) else style.bold
            style_paragraph(
                paragraph,
                ctx,
                size_pt=style.font_size_pt,
                bold=bold,
                color_token=style.text_color,
                align=style.align,
            )

        apply_shape_font(textbox, ctx)
