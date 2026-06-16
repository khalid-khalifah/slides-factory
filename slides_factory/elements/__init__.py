"""Drawable elements placed into grid cells.

An :class:`Element` validates its own Pydantic props and renders into an EMU
box using a resolved :class:`ElementStyle`. Built-ins: ``text`` and ``card``.
"""

from slides_factory.elements.base import Box, Element, element_from_function
from slides_factory.elements.card import CardElement, CardProps
from slides_factory.elements.text import TextElement, TextProps

__all__ = [
    "Box",
    "CardElement",
    "CardProps",
    "Element",
    "TextElement",
    "TextProps",
    "element_from_function",
]
