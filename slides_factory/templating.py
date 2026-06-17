"""Class-based templates — the layer built on top of the grid+element core.

A template declares one ``@at``-decorated method per grid cell. Registration
infers a composite input model: top-level :class:`FrameInfo` fields plus one
nested element-props object per cell (keyed by method name). Calling the
template with JSON validates the data, builds a :class:`Layout`, and renders
it through the core ``render_layout`` primitive.

Example::

    @app.template("kpi", name="KPI", description="Heading over a KPI card.",
                  grid="grid-cols-1 grid-rows-[1_2] gap-4")
    class Kpi(Template):
        @at("col-span-1", kind="text", style="text-3xl font-bold text-primary")
        def heading(self): ...

        @at(kind="card", style="bg-surface rounded-md")
        def revenue(self): ...

Input JSON::

    {
        "title": "Q3",
        "heading": {"text": "Q3"},
        "revenue": {"title": "Revenue", "value": "$1.2M"}
    }

Classes:
    Template — Base class authors subclass; render() builds + draws a Layout.
    CellDef  — Metadata attached to an @at method (placement, kind, style).

Functions:
    at — Decorator marking a method as one grid cell.
"""

from __future__ import annotations

from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from pydantic import BaseModel
from pptx.presentation import Presentation
from pptx.slide import Slide

from slides_factory.layout_spec import CellSpec, ElementSpec, Layout
from slides_factory.frame_info import FrameInfo
from slides_factory.render_context import RenderContext

_CELL_ATTR = "__sf_cell__"


@dataclass(frozen=True)
class CellDef:
    """Placement + element identity declared by an ``@at`` decorator."""

    placement: str
    kind: str
    style: str
    name: str


def at(placement: str = "", *, kind: str, style: str = "") -> Callable[[Callable], Callable]:
    """Mark a template method as one grid cell.

    ``placement`` holds cell utility classes (e.g. ``col-span-2``); ``kind`` is a
    registered element kind; ``style`` holds element look classes. The decorated
    method receives validated data and returns that element's props dict.
    """

    def decorator(method: Callable) -> Callable:
        setattr(
            method,
            _CELL_ATTR,
            CellDef(placement=placement, kind=kind, style=style, name=method.__name__),
        )
        return method

    return decorator


class Template(ABC):
    """Base class for grid-composed templates.

    Subclasses declare ``@at`` methods only; registration infers ``input_model``
    from cell element kinds plus FrameInfo fields.
    """

    id: ClassVar[str] = ""
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    grid: ClassVar[str] = ""
    default_frame: ClassVar[str | None] = None
    layout_name: ClassVar[str | None] = "Blank"
    tags: ClassVar[tuple[str, ...]] = ()
    input_model: ClassVar[type[BaseModel] | None] = None

    @classmethod
    def validate_data(cls, data: dict[str, Any]) -> BaseModel:
        """Validate raw JSON against this template's typed input model."""
        if cls.input_model is None:
            raise RuntimeError(
                f"template {cls.id!r} has no input_model; register via @app.template"
            )
        return cls.input_model.model_validate(data)

    @classmethod
    def get_json_schema(cls) -> dict[str, Any]:
        """Return JSON schema for the template's input model (CLI / preview)."""
        if cls.input_model is None:
            raise RuntimeError(
                f"template {cls.id!r} has no input_model; register via @app.template"
            )
        return cls.input_model.model_json_schema()

    @classmethod
    def resolve_layout(cls, prs: Presentation):
        """Pick ``layout_name`` (default 'Blank'), falling back to the first layout."""
        fallback = None
        for layout in prs.slide_layouts:
            if cls.layout_name and layout.name == cls.layout_name:
                return layout
            if fallback is None:
                fallback = layout
        if fallback is not None:
            return fallback
        raise ValueError(f"template {cls.id!r} found no slide layouts to render into")

    @classmethod
    def cell_defs(cls) -> list[tuple[Callable, CellDef]]:
        """Return (method, CellDef) pairs in declaration order across the MRO."""
        ordered: dict[str, tuple[Callable, CellDef]] = {}
        for klass in reversed(cls.__mro__):
            for attr_name, value in vars(klass).items():
                cell = getattr(value, _CELL_ATTR, None)
                if cell is not None:
                    ordered[attr_name] = (value, cell)
        return list(ordered.values())

    def frame_info(self, data: BaseModel) -> FrameInfo:
        """Read frame chrome fields from the validated composite input."""
        return FrameInfo(
            title=getattr(data, "title", None),
            subtitle=getattr(data, "subtitle", None),
            page_number=getattr(data, "page_number", None),
            total_pages=getattr(data, "total_pages", None),
        )

    def build(self, data: BaseModel) -> Layout:
        """Turn validated input data into a concrete :class:`Layout`."""
        cells: list[CellSpec] = []
        for _, cell in self.cell_defs():
            cell_props = getattr(data, cell.name, None)
            if cell_props is None:
                props: dict[str, Any] = {}
            elif isinstance(cell_props, BaseModel):
                props = cell_props.model_dump(mode="json")
            elif isinstance(cell_props, dict):
                props = cell_props
            else:
                raise TypeError(
                    f"cell {cell.name!r} on {type(self).__name__} must be element props, "
                    f"got {type(cell_props).__name__}"
                )
            cells.append(
                CellSpec(
                    at=cell.placement,
                    element=ElementSpec(kind=cell.kind, style=cell.style, props=props),
                )
            )
        return Layout(grid=self.grid, cells=cells, frame_info=self.frame_info(data))

    def render(self, slide: Slide, data: BaseModel, ctx: RenderContext) -> None:
        """Build the Layout from data and draw it through the grid core."""
        from slides_factory.layout.render import render_layout

        render_layout(slide, self.build(data), ctx)
