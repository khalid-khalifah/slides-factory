"""Drawable elements placed into grid cells.

Built-in elements registered via ``@app.element`` in ``app.py``.
"""

from slides_factory.elements.base import Box, element_from_function

__all__ = [
    "Box",
    "element_from_function",
]
