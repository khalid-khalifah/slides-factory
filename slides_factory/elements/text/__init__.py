"""Rich-text document model, DSL, HTML parser, and render pipeline.

Provides everything needed to build and render rich-text content in slide
elements.  Organised into four submodules:

* ``model`` — Tree models: ``TextRun``, ``Paragraph``, ``ListItem``,
  ``ListStyle``, ``TextBlock``.
* ``dsl`` — Python DSL constructor: ``text()``.
* ``html`` — HTML-like parser: ``parse_html()``.
* ``render`` — Transformation pipeline: ``prepare()``, ``_RenderParagraph``,
  ``_RenderRun``.

For the element itself (``TextProps``, ``TextStyle``, ``render_text``), import
directly from ``slides_factory.elements.text_element``.
"""

from slides_factory.elements.text.dsl import text
from slides_factory.elements.text.html import parse_html
from slides_factory.elements.text.model import (
    ListItem,
    ListStyle,
    Paragraph,
    TextBlock,
    TextRun,
)
from slides_factory.elements.text.render import (
    _RenderParagraph,
    _RenderRun,
    prepare,
)

__all__ = [
    "ListItem",
    "ListStyle",
    "Paragraph",
    "TextBlock",
    "TextRun",
    "_RenderParagraph",
    "_RenderRun",
    "parse_html",
    "prepare",
    "text",
]
