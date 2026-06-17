"""Template chrome fields and the default empty frame input model.

Frames declare their own ``frame_info_model`` (a standalone Pydantic ``BaseModel``).
Templates may add optional top-level ``title`` / ``subtitle`` fields that map into
the active frame's info dict at render time.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

TEMPLATE_CHROME_FIELDS = frozenset({"title", "subtitle"})

TEMPLATE_CHROME_FIELD_DEFS: dict[str, tuple] = {
    "title": (str | None, Field(default=None, description="Primary page title.")),
    "subtitle": (str | None, Field(default=None, description="Secondary page heading.")),
}


class EmptyFrameInput(BaseModel):
    """Default when a frame does not declare ``frame_info_model``."""

    pass
