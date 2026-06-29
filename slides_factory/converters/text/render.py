"""Transformation pipeline — turn TextBlock trees into render-ready paragraphs."""

from __future__ import annotations

from slides_factory.converters.text.model import ListItem, Paragraph, TextBlock, TextRun
from slides_factory.render_context import RenderContext
from slides_factory.styling import theme


class _RenderRun:
    """Resolved run ready for python-pptx — all style values are concrete."""

    __slots__ = ("text", "bold", "italic", "color_hex", "size_pt", "link", "strikethrough", "underline")

    def __init__(  # noqa: PLR0913
        self,
        text: str,
        bold: bool | None = None,
        italic: bool | None = None,
        color_hex: str | None = None,
        size_pt: float | None = None,
        link: str | None = None,
        strikethrough: bool | None = None,
        underline: bool | None = None,
    ) -> None:
        self.text = text
        self.bold = bold
        self.italic = italic
        self.color_hex = color_hex
        self.size_pt = size_pt
        self.link = link
        self.strikethrough = strikethrough
        self.underline = underline


class _RenderParagraph:
    """Resolved paragraph ready for python-pptx."""

    __slots__ = ("runs", "indent_level", "alignment", "list_level", "bullet_type")

    def __init__(
        self,
        runs: list[_RenderRun],
        indent_level: int = 0,
        alignment: str | None = None,
        list_level: int = 0,
        bullet_type: str | None = None,
    ) -> None:
        self.runs = runs
        self.indent_level = indent_level
        self.alignment = alignment
        self.list_level = list_level
        self.bullet_type = bullet_type


def prepare(
    block: TextBlock,
    ctx: RenderContext,
    *,
    base_size_pt: float,
    base_color: str = "primary",
    base_bold: bool = False,
    alignment: str = "left",
) -> list[_RenderParagraph]:
    """Normalise a ``TextBlock`` into render-ready ``_RenderParagraph`` values.

    Resolves colour tokens, applies element-level defaults, and converts
    ``ListItem`` nodes to paragraphs with bullet markers.
    """
    base_color_hex = theme.resolve_style_color(base_color, ctx) if base_color else None
    results: list[_RenderParagraph] = []

    for node in block.children:
        if isinstance(node, Paragraph):
            rr = _build_render_paragraph(
                node.runs,
                ctx,
                indent_level=0,
                alignment=alignment,
                base_size_pt=base_size_pt,
                base_color_hex=base_color_hex,
                base_bold=base_bold,
            )
            results.append(rr)

        elif isinstance(node, ListItem):
            rr = _build_render_paragraph(
                node.runs,
                ctx,
                indent_level=node.marker.level,
                list_level=node.marker.level,
                bullet_type=node.marker.type,
                alignment=alignment,
                base_size_pt=base_size_pt,
                base_color_hex=base_color_hex,
                base_bold=base_bold,
            )
            results.append(rr)

    return results



def _build_render_paragraph(
    runs: list[TextRun],
    ctx: RenderContext,
    *,
    indent_level: int = 0,
    list_level: int = 0,
    bullet_type: str | None = None,
    alignment: str,
    base_size_pt: float,
    base_color_hex: str | None,
    base_bold: bool,
) -> _RenderParagraph:
    """Resolve one block node into a ``_RenderParagraph``."""
    resolved_runs: list[_RenderRun] = []

    for tr in runs:
        if tr.color is not None:
            color_hex = theme.resolve_style_color(tr.color, ctx)
        else:
            color_hex = base_color_hex

        resolved_runs.append(
            _RenderRun(
                text=tr.text,
                bold=tr.bold if tr.bold is not None else base_bold,
                italic=tr.italic or False,
                color_hex=color_hex,
                size_pt=tr.size_pt or base_size_pt,
                link=tr.link,
                strikethrough=tr.strikethrough or False,
                underline=tr.underline or False,
            )
        )

    return _RenderParagraph(
        runs=resolved_runs,
        indent_level=indent_level,
        alignment=alignment,
        list_level=list_level,
        bullet_type=bullet_type,
    )
