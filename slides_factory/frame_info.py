"""Information layer passed from a slide spec into a frame.

Classes:
    FrameInfo — Page-level data (title, subtitle, page number) a frame may draw.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FrameInfo(BaseModel):
    """Page-level data a frame draws in its information layer.

    All fields are optional so frames can decide which to render and any
    template input may omit the block entirely.
    """

    title: str | None = Field(default=None, description="Primary page title.")
    subtitle: str | None = Field(default=None, description="Secondary page heading.")
    page_number: int | None = Field(
        default=None, ge=0, description="1-based page number for footer chrome."
    )
    total_pages: int | None = Field(
        default=None, ge=0, description="Total deck length for 'x of y' footers."
    )
