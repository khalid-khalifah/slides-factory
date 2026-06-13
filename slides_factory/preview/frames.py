"""Frame selection helpers for the template preview app."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from slides_factory.template import SlideTemplate


def frame_for_template(
    template: "SlideTemplate",
    *,
    available_frame_ids: list[str],
    brand_default_frame: str | None,
) -> str | None:
    """Pick the preview frame for a template (template default, else brand default)."""
    tpl_default = type(template).default_frame
    if tpl_default and tpl_default in available_frame_ids:
        return tpl_default
    return brand_default_frame
