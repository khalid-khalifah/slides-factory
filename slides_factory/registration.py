"""Build template / FrameTemplate wrappers from decorated functions and classes.

Functions:
    input_model_from_function  — Extract the TemplateInput subclass from a template function.
    input_model_from_template  — Build a composite input model from @at cells + FrameInfo fields.
    template_from_function     — Wrap a render function as a SlideTemplate instance.
    template_from_class        — Finalize a class-based grid Template for registration.
    frame_from_function        — Wrap a render function as a FrameTemplate instance.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Sequence
from typing import Any, get_type_hints

from pydantic import BaseModel, Field, create_model
from pptx.slide import Slide

from slides_factory.frame import FrameTemplate
from slides_factory.frame_info import FrameInfo
from slides_factory.palette import SlidePalette
from slides_factory.render_context import RenderContext
from slides_factory.template import SlideTemplate
from slides_factory.template_input import TemplateInput
from slides_factory.typing_utils import unwrap_annotation

_RESERVED_PARAMS = frozenset({"slide", "ctx", "self"})


def _is_template_input_subclass(annotation: Any) -> bool:
    annotation = unwrap_annotation(annotation)
    return isinstance(annotation, type) and issubclass(annotation, TemplateInput)


def _get_function_type_hints(func: Callable[..., Any]) -> dict[str, Any]:
    """Resolve type hints, including TemplateInput classes defined in enclosing scopes."""
    globalns = dict(func.__globals__)
    if func.__closure__:
        for name, cell in zip(func.__code__.co_freevars, func.__closure__):
            globalns[name] = cell.cell_contents
    return get_type_hints(func, globalns=globalns, include_extras=True)


def input_model_from_function(func: Callable[..., Any]) -> type[TemplateInput]:
    """Extract the single TemplateInput subclass parameter from a template function."""
    hints = _get_function_type_hints(func)
    data_params: list[tuple[str, inspect.Parameter]] = []

    for name, param in inspect.signature(func).parameters.items():
        if name in _RESERVED_PARAMS:
            continue
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            raise TypeError(
                f"template function {func.__name__!r} cannot use *args or **kwargs"
            )
        data_params.append((name, param))

    if not data_params:
        raise TypeError(
            f"template function {func.__name__!r} must declare a TemplateInput parameter "
            "besides slide and ctx"
        )
    if len(data_params) != 1:
        names = ", ".join(name for name, _ in data_params)
        raise TypeError(
            f"template function {func.__name__!r} must declare exactly one TemplateInput "
            f"parameter, got: {names}"
        )

    param_name, _ = data_params[0]
    hint = hints.get(param_name, Any)
    annotation = unwrap_annotation(hint)
    if not _is_template_input_subclass(annotation):
        raise TypeError(
            f"template function {func.__name__!r} parameter {param_name!r} must be a "
            f"TemplateInput subclass, got {annotation!r}"
        )
    return annotation


def normalize_tags(tags: Sequence[str] | None) -> tuple[str, ...]:
    """Normalize template tags to a deduplicated lowercase tuple."""
    if not tags:
        return ()
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        tag = raw.strip().lower()
        if not tag:
            raise ValueError("template tags cannot be empty strings")
        if tag not in seen:
            seen.add(tag)
            normalized.append(tag)
    return tuple(normalized)


def input_model_from_template(cls: type, factory: Any) -> type[TemplateInput]:
    """Build a composite TemplateInput from FrameInfo fields and @at cell prop models."""
    from slides_factory.templating import Template

    if not issubclass(cls, Template):
        raise TypeError(f"expected a Template subclass, got {cls!r}")

    cell_defs = cls.cell_defs()
    if not cell_defs:
        raise TypeError(
            f"template class {cls.__name__!r} must declare at least one @at method"
        )

    cell_names = {cell.name for _, cell in cell_defs}
    field_definitions: dict[str, Any] = {}

    for fname, finfo in FrameInfo.model_fields.items():
        if fname in cell_names:
            raise TypeError(
                f"template class {cls.__name__!r}: @at method {fname!r} conflicts "
                "with a FrameInfo field (title, subtitle, page_number, total_pages)"
            )
        field_definitions[fname] = (finfo.annotation, finfo)

    for _, cell in cell_defs:
        try:
            element = factory.get_element(cell.kind)
        except KeyError as exc:
            raise TypeError(
                f"template class {cls.__name__!r}: @at method {cell.name!r} references "
                f"unknown element {cell.kind!r}"
            ) from exc
        props_model = element.props_model
        field_definitions[cell.name] = (
            props_model,
            Field(default_factory=props_model),
        )

    return create_model(f"{cls.__name__}Input", __base__=TemplateInput, **field_definitions)


def template_from_function(
    func: Callable[..., Any],
    *,
    template_id: str,
    name: str,
    description: str,
    layout_name: str | None,
    extract: Callable[[Slide], Any] | None,
    tags: Sequence[str] | None = None,
    default_frame: str | None = None,
) -> SlideTemplate:
    """Wrap a template render function as a SlideTemplate instance."""
    tpl_input_model = input_model_from_function(func)
    render_fn = func
    tpl_name = name
    tpl_description = description
    tpl_layout = layout_name
    tpl_tags = normalize_tags(tags)
    tpl_default_frame = default_frame

    class RegisteredTemplate(SlideTemplate):
        id = template_id
        name = tpl_name
        description = tpl_description
        tags = tpl_tags
        default_frame = tpl_default_frame
        input_model = tpl_input_model
        layout_name = tpl_layout

        def render(self, slide: Slide, data: BaseModel, ctx: RenderContext) -> None:
            render_fn(slide, ctx, data)

        def extract(self, slide: Slide) -> BaseModel:
            if extract is None:
                raise NotImplementedError(
                    f"template {template_id!r} has no extract function"
                )
            result = extract(slide)
            if isinstance(result, tpl_input_model):
                return result
            if isinstance(result, BaseModel):
                return tpl_input_model.model_validate(result.model_dump())
            return tpl_input_model.model_validate(result)

    return RegisteredTemplate()


def template_from_class(
    cls: type,
    factory: Any,
    *,
    template_id: str,
    name: str,
    description: str,
    grid: str = "",
    layout_name: str | None = None,
    tags: Sequence[str] | None = None,
    default_frame: str | None = None,
):
    """Finalize a class-based grid Template: set metadata and return an instance."""
    from slides_factory.templating import Template

    if not (isinstance(cls, type) and issubclass(cls, Template)):
        raise TypeError(
            f"template {template_id!r}: expected a Template subclass, got {cls!r}"
        )

    cls.input_model = input_model_from_template(cls, factory)
    cls.id = template_id
    cls.name = name
    cls.description = description
    cls.grid = grid
    cls.tags = normalize_tags(tags)
    cls.default_frame = default_frame
    if layout_name is not None:
        cls.layout_name = layout_name
    return cls()


def _frame_accepts_info(func: Callable[..., Any]) -> bool:
    """True when a frame function declares an info parameter beyond slide, ctx."""
    positional = [
        param
        for param in inspect.signature(func).parameters.values()
        if param.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    return len(positional) >= 3


def frame_from_function(
    func: Callable[..., Any],
    *,
    frame_id: str,
    name: str,
    description: str,
    palette: SlidePalette,
    playground: Any = None,
    frame_info_model: Any = None,
    allows_layout: bool = True,
) -> FrameTemplate:
    """Wrap a frame render function as a FrameTemplate instance.

    Supports both the legacy ``(slide, ctx)`` signature and the new
    ``(slide, ctx, info)`` signature; the arity is detected from the function.
    """
    from slides_factory.frame import FrameInfo

    render_fn = func
    frm_name = name
    frm_description = description
    frm_palette = palette
    frm_playground = playground
    frm_info_model = frame_info_model or FrameInfo
    frm_allows_layout = allows_layout
    accepts_info = _frame_accepts_info(func)

    class RegisteredFrame(FrameTemplate):
        id = frame_id
        name = frm_name
        description = frm_description
        palette = frm_palette
        playground = frm_playground
        frame_info_model = frm_info_model
        allows_layout = frm_allows_layout

        def render(self, slide: Slide, ctx: RenderContext, info: Any = None) -> None:
            if accepts_info:
                render_fn(slide, ctx, info if info is not None else frm_info_model())
            else:
                render_fn(slide, ctx)

    return RegisteredFrame()
