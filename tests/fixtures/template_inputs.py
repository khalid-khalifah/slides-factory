"""TemplateInput models shared by core form tests."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

from slides_factory.template_input import TemplateInput


class ShapeBox(BaseModel):
    label: str
    color: str = "#4472C4"


class BulletsInput(TemplateInput):
    title: Annotated[str, Field(description="Slide title")]
    bullets: Annotated[list[str], Field(description="Bullet items")]
    levels: Annotated[list[int] | None, Field(description="Indent levels")] = None


class BlankShapesInput(TemplateInput):
    heading: str
    boxes: list[ShapeBox]
