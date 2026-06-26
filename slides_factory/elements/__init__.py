"""Drawable elements placed into grid cells.

Built-ins: ``text`` and ``card``. Register custom elements via ``@app.element``.
"""

from slides_factory.elements.base import Box, element_from_function
from slides_factory.elements.card import CardProps, CardStyle, render_card
from slides_factory.elements.image import ImageProps, ImageStyle, render_image
from slides_factory.elements.text_element import TextProps, TextStyle, render_text

__all__ = [
    "Box",
    "CardProps",
    "CardStyle",
    "ImageProps",
    "ImageStyle",
    "TextProps",
    "TextStyle",
    "element_from_function",
    "render_card",
    "render_image",
    "render_text",
]
