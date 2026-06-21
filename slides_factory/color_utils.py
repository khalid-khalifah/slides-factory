"""Shared color utilities."""

from pptx.dml.color import RGBColor


def hex_to_rgb(hex_color: str) -> RGBColor:
    """Parse a ``#RRGGBB`` string into a python-pptx RGBColor."""
    value = hex_color.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"invalid hex color: {hex_color!r}")
    return RGBColor(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
