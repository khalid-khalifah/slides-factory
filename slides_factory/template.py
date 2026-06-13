"""Slide template protocol.

Classes:
    SlideTemplate — Abstract base every template implements (render + extract).

Functions:
    list_templates    — Return instances of every registered slide template.
    list_tags         — Return all unique template tags.
    get_template      — Return a template instance by id, or raise KeyError.
    search_templates  — Return templates matching id, name, description, or tags.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Type

from pydantic import BaseModel
from pptx.presentation import Presentation
from pptx.slide import Slide

from slides_factory.render_context import RenderContext


class SlideTemplate(ABC):
    """Protocol every slide template must implement."""

    id: ClassVar[str]
    name: ClassVar[str]
    description: ClassVar[str]
    tags: ClassVar[tuple[str, ...]] = ()
    default_frame: ClassVar[str | None] = None
    input_model: ClassVar[Type[BaseModel]]
    layout_name: ClassVar[str | None] = None

    @classmethod
    def validate_data(cls, data: dict[str, Any]) -> BaseModel:
        """Validate raw JSON dict against this template's Pydantic input model."""
        return cls.input_model.model_validate(data)

    @classmethod
    def get_json_schema(cls) -> dict[str, Any]:
        """Return JSON schema for agents to learn required slide fields."""
        return cls.input_model.model_json_schema()

    @classmethod
    def resolve_layout(cls, prs: Presentation):
        """Pick the PowerPoint slide layout by name from the presentation theme."""
        if cls.layout_name:
            for layout in prs.slide_layouts:
                if layout.name == cls.layout_name:
                    return layout
        raise ValueError(
            f"Template '{cls.id}' could not resolve layout "
            f"(layout_name={cls.layout_name!r})"
        )

    @abstractmethod
    def render(self, slide: Slide, data: BaseModel, ctx: RenderContext) -> None:
        """Fill slide placeholders/shapes from validated data."""

    @abstractmethod
    def extract(self, slide: Slide) -> BaseModel:
        """Read slide content back into the input model for doc get / edit."""


def list_templates(*, tag: str | None = None) -> list[SlideTemplate]:
    """Return instances of every registered slide template, optionally filtered by tag."""
    from slides_factory.app import get_app

    return get_app().list_templates(tag=tag)


def list_tags() -> list[str]:
    """Return all unique template tags, sorted."""
    from slides_factory.app import get_app

    return get_app().list_tags()


def get_template(template_id: str) -> SlideTemplate:
    """Return a template instance by id, or raise KeyError with available ids."""
    from slides_factory.app import get_app

    return get_app().get_template(template_id)


def search_templates(query: str) -> list[SlideTemplate]:
    """Return templates whose id, name, or description matches the query."""
    from slides_factory.app import get_app

    return get_app().search_templates(query)
