"""Text element — a rich text box placed in a grid cell.

The ``TextBlock`` document model and its DSL, HTML parser, and render
pipeline live in ``slides_factory/elements/text/``.
"""

from __future__ import annotations

from pptx.enum.text import MSO_ANCHOR
from pptx.slide import Slide
from pydantic import BaseModel

from slides_factory.elements.base import Box
from slides_factory.elements.text.model import TextBlock
from slides_factory.elements.text.render import prepare
from slides_factory.layout.fonts import apply_shape_font
from slides_factory.render_context import RenderContext
from slides_factory.styling import theme
from slides_factory.styling.models import TextStyle


class TextProps(BaseModel):
    """Content props for the text element.

    ``block`` holds the rich-text document tree.  Element-level styling is
    passed through the separate ``style`` parameter (the element's
    ``style_model``), not embedded in props.
    """

    block: TextBlock = TextBlock(children=[])


def render_text(
    slide: Slide,
    box: Box,
    props: TextProps,
    style: TextStyle,
    ctx: RenderContext,
) -> None:
    """Render rich text content into the given box."""
    left, top, width, height = box
    textbox = slide.shapes.add_textbox(left, top, width, height)
    frame = textbox.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.TOP

    body_size = theme.font_size_pt(style.text_size)

    # Prepare: resolve tree into render-ready paragraphs.
    render_paragraphs = prepare(
        props.block,
        ctx,
        base_size_pt=body_size,
        base_color=style.text_color,
        base_bold=style.bold,
        alignment=style.align,
    )

    if not render_paragraphs:
        from slides_factory.elements.text.render import _RenderParagraph, _RenderRun

        render_paragraphs = [_RenderParagraph(runs=[_RenderRun(text="")])]

    for index, rp in enumerate(render_paragraphs):
        pptx_para = frame.paragraphs[0] if index == 0 else frame.add_paragraph()

        if rp.alignment:
            from pptx.enum.text import PP_ALIGN

            align_map = {
                "left": PP_ALIGN.LEFT,
                "center": PP_ALIGN.CENTER,
                "right": PP_ALIGN.RIGHT,
                "justify": PP_ALIGN.JUSTIFY,
            }
            pptx_para.alignment = align_map.get(rp.alignment)

        if rp.indent_level > 0:
            pptx_para.level = rp.indent_level

        for run_idx, rr in enumerate(rp.runs):
            if run_idx == 0:
                pptx_run = pptx_para.runs[0] if pptx_para.runs else pptx_para.add_run()
            else:
                pptx_run = pptx_para.add_run()

            pptx_run.text = rr.text

            if rr.bold is not None:
                pptx_run.font.bold = rr.bold
            if rr.italic is not None:
                pptx_run.font.italic = rr.italic
            if rr.color_hex is not None:
                from slides_factory.color_utils import hex_to_rgb

                pptx_run.font.color.rgb = hex_to_rgb(rr.color_hex)
            if rr.size_pt is not None:
                from pptx.util import Pt

                pptx_run.font.size = Pt(rr.size_pt)
            if rr.strikethrough is not None:
                pptx_run.font.strikethrough = rr.strikethrough
            if rr.underline is not None:
                pptx_run.font.underline = rr.underline
            if rr.link:
                pptx_run.hyperlink.address = rr.link

    apply_shape_font(textbox, ctx, style.font)
