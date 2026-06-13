"""Base class for slide template input schemas."""

from __future__ import annotations

from pydantic import BaseModel


class TemplateInput(BaseModel):
    """Base class every template input model subclasses."""
