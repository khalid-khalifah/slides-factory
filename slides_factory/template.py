"""Slide template protocols and registry facade.

The engine supports two template flavors that both expose ``render(slide, data,
ctx)`` and a typed ``input_model``:

* :class:`SlideTemplate` — a free-form render function (draws anything).
* :class:`slides_factory.templating.Template` — a grid-composed class built on
  top of the grid+element core (the recommended authoring style).

Classes:
    SlideTemplate — Abstract base for free-form render-function templates.

Functions:
    list_templates    — Return instances of every registered template.
    list_tags         — Return all unique template tags.
    get_template      — Return a template instance by id, or raise KeyError.
    search_templates  — Return templates matching id, name, description, or tags.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Type

from pydantic import BaseModel
from pptx.presentation import Presentation
from pptx.slide import Slide

from slides_factory.render_context import RenderContext

if TYPE_CHECKING:
    from slides_factory.templating import Template

AnyTemplate = "SlideTemplate | Template"


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


def list_templates(*, tag: str | None = None, app: object | None = None) -> list[Any]:
    """Return instances of every registered template, optionally filtered by tag."""
    if app is not None:
        if hasattr(app, "list_templates"):
            return app.list_templates(tag=tag)
        from slides_factory.app import get_app

        return get_app().list_templates(tag=tag)
    from slides_factory.app import get_app

    return get_app().list_templates(tag=tag)


def list_tags(*, app: object | None = None) -> list[str]:
    """Return all unique template tags, sorted."""
    if app is not None:
        if hasattr(app, "list_tags"):
            return app.list_tags()
        from slides_factory.app import get_app

        return get_app().list_tags()
    from slides_factory.app import get_app

    return get_app().list_tags()


def get_template(template_id: str, *, app: object | None = None) -> Any:
    """Return a template instance by id, or raise KeyError with available ids."""
    if app is not None:
        if hasattr(app, "get_template"):
            return app.get_template(template_id)
        from slides_factory.app import get_app

        return get_app().get_template(template_id)
    from slides_factory.app import get_app

    return get_app().get_template(template_id)


def search_templates(query: str, *, app: object | None = None) -> list[Any]:
    """Return templates whose id, name, or description matches the query."""
    if app is not None:
        if hasattr(app, "search_templates"):
            return app.search_templates(query)
        from slides_factory.app import get_app

        return get_app().search_templates(query)
    from slides_factory.app import get_app

    return get_app().search_templates(query)
