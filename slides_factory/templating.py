"""Class-based templates — the layer built on top of the grid+element core.

A template declares one ``@at``-decorated method per grid cell. Registration
infers a composite input model: optional template chrome fields (``title``,
``subtitle``) plus one nested element-props object per cell (keyed by method name). Calling the
template with JSON validates the data, builds a :class:`Layout`, and renders
it through the core ``render_layout`` primitive.

Example::

    @app.template(
        "kpi",
        name="KPI",
        description="Heading over a KPI card.",
        grid="grid-cols-1 grid-rows-[1_2] gap-4",
    )
    class Kpi(Template):
        @at("col-span-1", kind="text")
        def heading(self): ...

        @at(kind="card")
        def revenue(self): ...

Input JSON::

    {"title": "Q3", "heading": {"text": "Q3"}, "revenue": {"title": "Revenue", "value": "$1.2M"}}

Classes:
    Template — Base class authors subclass; render() builds + draws a Layout.
    CellDef  — Metadata attached to an @at method (placement, kind).

Functions:
    at — Decorator marking a method as one grid cell.
"""

from __future__ import annotations

from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from pptx.presentation import Presentation
from pptx.slide import Slide
from pydantic import BaseModel

from slides_factory.frame_info import TEMPLATE_CHROME_FIELDS
from slides_factory.layout_spec import CellSpec, ElementSpec, Layout
from slides_factory.render_context import RenderContext

_CELL_ATTR = "__sf_cell__"


@dataclass(frozen=True)
class CellDef:
    """Placement + element/template identity declared by an ``@at`` decorator."""

    placement: str
    name: str
    kind: str | None = None
    template: str | None = None


def _validate_cell_def(
    placement: str,
    name: str,
    kind: str | None,
    template: str | None,
) -> CellDef:
    """Build a CellDef ensuring exactly one of kind/template is set."""
    if kind and template:
        raise TypeError(
            f"@at on {name!r}: 'kind' and 'template' are mutually exclusive"
        )
    if not kind and not template:
        raise TypeError(
            f"@at on {name!r}: one of 'kind' or 'template' is required"
        )
    return CellDef(placement=placement, name=name, kind=kind, template=template)


def at(
    placement: str = "",
    *,
    kind: str | None = None,
    template: str | None = None,
) -> Callable[[Callable], Callable]:
    """Mark a template method as one grid cell.

    ``placement`` holds cell utility classes (e.g. ``col-span-2``).
    One of ``kind`` (registered element kind) or ``template`` (registered
    template id) must be provided; they are mutually exclusive.

    Use ``kind`` to render a single element in the cell.  Use ``template``
    to delegate the cell to a sub-template (template composition).
    """

    def decorator(method: Callable) -> Callable:
        cell = _validate_cell_def(placement, method.__name__, kind, template)
        setattr(method, _CELL_ATTR, cell)
        return method

    return decorator


class Template(ABC):
    """Base class for grid-composed templates.

    Subclasses declare ``@at`` methods only; registration infers ``input_model``
    from cell element kinds plus optional template chrome fields.
    """

    id: ClassVar[str] = ""
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    grid: ClassVar[str] = ""
    default_frame: ClassVar[str | None] = None
    layout_name: ClassVar[str | None] = "Blank"
    tags: ClassVar[tuple[str, ...]] = ()
    input_model: ClassVar[type[BaseModel] | None] = None
    # Set by template_from_class at registration time.
    _app: ClassVar[Any | None] = None

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

    def frame_chrome(self, data: BaseModel) -> dict[str, Any]:
        """Map template chrome fields into a frame-info dict for the active frame."""
        chrome: dict[str, Any] = {}
        for field in TEMPLATE_CHROME_FIELDS:
            if hasattr(data, field):
                chrome[field] = getattr(data, field)
        return chrome

    def frame_style_data(self, data: BaseModel) -> dict[str, Any]:
        """Return optional frame style JSON from validated template input."""
        value = getattr(data, "frame_style", None)
        if isinstance(value, dict):
            return value
        return {}

    def build(self, data: BaseModel) -> Layout:
        """Turn validated input data into a concrete :class:`Layout`."""
        styles_map = getattr(data, "styles", None) or {}
        if not isinstance(styles_map, dict):
            styles_map = {}
        cells: list[CellSpec] = []
        for _, cell in self.cell_defs():
            if cell.template:
                # Sub-template cell — pass raw data dict, no element.
                cell_data = getattr(data, cell.name, None)
                if isinstance(cell_data, BaseModel):
                    cell_data = cell_data.model_dump(mode="json", exclude_none=True)
                elif not isinstance(cell_data, dict):
                    cell_data = {}
                cells.append(
                    CellSpec(
                        at=cell.placement,
                        template=cell.template,
                        cell_data=cell_data,
                    )
                )
            else:
                cell_props = getattr(data, cell.name, None)
                if cell_props is None:
                    props: dict[str, Any] = {}
                elif isinstance(cell_props, BaseModel):
                    props = cell_props.model_dump(mode="json", exclude_none=True)
                elif isinstance(cell_props, dict):
                    props = cell_props
                else:
                    raise TypeError(
                        f"cell {cell.name!r} on {type(self).__name__} must be element props, "
                        f"got {type(cell_props).__name__}"
                    )
                cell_style = styles_map.get(cell.name, {})
                if not isinstance(cell_style, dict):
                    cell_style = {}
                cells.append(
                    CellSpec(
                        at=cell.placement,
                        element=ElementSpec(
                            kind=cell.kind,
                            props=props,
                            style=cell_style,
                        ),
                    )
                )
        return Layout(
            grid=self.grid,
            cells=cells,
            frame_info=self.frame_chrome(data),
            frame_style=self.frame_style_data(data),
        )

    def render(self, slide: Slide, data: BaseModel, ctx: RenderContext) -> None:
        """Build the Layout from data and draw it through the grid core."""
        from slides_factory.layout.render import render_layout

        render_layout(slide, self.build(data), ctx, app=self._app)
