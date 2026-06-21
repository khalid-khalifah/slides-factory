"""Base class for slide template input schemas."""

from pydantic import BaseModel


class TemplateInput(BaseModel):
    """Base class every template input model subclasses."""
