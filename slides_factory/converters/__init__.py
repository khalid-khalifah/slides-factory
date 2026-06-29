"""Converters — render rich content into python-pptx primitives.

These are **not** elements.  They work directly on python-pptx objects
(``TextFrame``, ``Slide``) so they can be used anywhere — in a shape,
a textbox, a table cell, a grid cell, or standalone.
"""

from slides_factory.converters.svg import render_svg_file, render_svg_string
from slides_factory.converters.text import (
    ListItem,
    ListStyle,
    Paragraph,
    TextBlock,
    TextRun,
    parse_html,
    prepare,
    render_text_block,
    text,
)

__all__ = [
    "ListItem",
    "ListStyle",
    "Paragraph",
    "TextBlock",
    "TextRun",
    "parse_html",
    "prepare",
    "render_svg_file",
    "render_svg_string",
    "render_text_block",
    "text",
]
