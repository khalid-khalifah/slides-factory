"""SVG converter — render SVG as native python-pptx shapes.

Wraps ``svg2pptx`` to render SVG content as native, editable PowerPoint
shapes on any slide.  Unlike embedding raster images, the result is
fully editable vector artwork.

Usage::

    from slides_factory.converters.svg import render_svg_string, render_svg_file

    # Render an SVG string onto a slide at a given box
    render_svg_string('''<svg ...>...</svg>''', slide, box)

    # Render from a file
    render_svg_file("icon.svg", slide, box)
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from pptx.slide import Slide

from slides_factory.geometry import Box


def _svg_intrinsic_size(
    svg_content: str,
) -> tuple[float, float] | None:
    """Quick-parse SVG to get intrinsic width/height without full parsing.

    Returns ``(width_px, height_px)`` or ``None`` if neither the SVG
    element nor a viewBox defines dimensions.
    """
    import xml.etree.ElementTree as ET

    root = ET.fromstring(svg_content)
    tag = root.tag if "}" not in root.tag else root.tag.split("}", 1)[1]
    if tag != "svg":
        return None

    # Try viewBox first, then width/height attributes.
    vb = root.get("viewBox")
    if vb:
        parts = vb.strip().split()
        if len(parts) == 4:
            w, h = float(parts[2]), float(parts[3])
            if w > 0 and h > 0:
                return w, h

    raw_w = root.get("width")
    raw_h = root.get("height")
    if raw_w and raw_h:
        try:
            return float(raw_w), float(raw_h)
        except ValueError:
            pass

    return None


def _fit_scale(
    svg_w: float,
    svg_h: float,
    box: Box,
) -> tuple[float, int, int]:
    """Compute scale, x-offset, and y-offset to fit SVG inside *box*
    maintaining aspect ratio (``contain`` fit, centred)."""
    from svg2pptx.geometry.units import px_to_emu

    svg_w_emu = px_to_emu(svg_w)
    svg_h_emu = px_to_emu(svg_h)

    if svg_w_emu <= 0 or svg_h_emu <= 0:
        return 1.0, box.left, box.top

    scale_x = box.width / svg_w_emu
    scale_y = box.height / svg_h_emu
    scale = min(scale_x, scale_y)

    # Centre the result in the box.
    final_w = int(svg_w_emu * scale)
    final_h = int(svg_h_emu * scale)
    offset_x = box.left + (box.width - final_w) // 2
    offset_y = box.top + (box.height - final_h) // 2

    return scale, offset_x, offset_y


def render_svg_string(
    svg_content: str,
    slide: Slide,
    box: Box,
    *,
    scale: float | None = None,
) -> None:
    """Render an SVG string as native PowerPoint shapes inside *box*.

    When *scale* is ``None`` (default), the SVG is auto-scaled to fit
    the box with ``contain`` aspect-ratio preservation and centred inside
    the box.

    When *scale* is given, it is used directly and the SVG is placed at
    the box's top-left corner.
    """
    from svg2pptx import Config, SVGConverter

    size = _svg_intrinsic_size(svg_content)

    if scale is not None:
        final_scale = scale
        offset_x = box.left
        offset_y = box.top
    elif size is not None:
        svg_w, svg_h = size
        final_scale, offset_x, offset_y = _fit_scale(svg_w, svg_h, box)
    else:
        # No size info — use 1.0 and place at box origin.
        final_scale = 1.0
        offset_x = box.left
        offset_y = box.top

    config = Config(
        scale=final_scale,
        offset_x=offset_x,
        offset_y=offset_y,
        disable_shadows=True,
    )
    converter = SVGConverter(config=config)
    converter.add_string_to_slide(svg_content, slide)


def render_svg_file(
    path: Union[str, Path],
    slide: Slide,
    box: Box,
    *,
    scale: float | None = None,
) -> None:
    """Read an SVG file and render it as native PowerPoint shapes.

    Accepts the same parameters as :func:`render_svg_string`.
    """
    content = Path(path).read_text(encoding="utf-8")
    render_svg_string(content, slide, box, scale=scale)
