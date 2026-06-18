"""Drawable elements placed into grid cells.

Built-ins: ``text`` and ``card``. Register custom elements via ``@app.element``.
"""

from slides_factory.elements.base import Box, element_from_function
from slides_factory.elements.card import CardProps, render_card
from slides_factory.elements.text import TextProps, render_text

__all__ = [
    "Box",
    "CardProps",
    "TextProps",
    "element_from_function",
    "render_card",
    "render_text",
]
