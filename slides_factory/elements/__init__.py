"""Drawable elements placed into grid cells.

Built-ins: ``text`` and ``card``. Register custom elements via ``@app.element``.
"""

from slides_factory.elements.base import Box, element_from_function
from slides_factory.elements.card import CardProps, CardStyle, render_card
from slides_factory.elements.text import TextProps, TextStyle, render_text

__all__ = [
    "Box",
    "CardProps",
    "CardStyle",
    "TextProps",
    "TextStyle",
    "element_from_function",
    "render_card",
    "render_text",
]
