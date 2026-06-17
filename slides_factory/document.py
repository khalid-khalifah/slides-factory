"""Document-level operations on .pptx files.

Functions:
    ensure_default_theme — Create or validate the bundled 10" x 7.5" blank theme.
    open_document        — Load a .pptx file into a python-pptx Presentation.
    load_document_brand  — Load brand YAML stored on the document, if configured.
    new_presentation     — Create an in-memory deck shell (no disk write).
    create_document      — Create a new empty deck with optional RTL/locale defaults.
    update_document_rtl  — Toggle document-wide RTL and locale settings.
    save_document        — Write a Presentation to disk (embeds brand fonts).
    delete_slide         — Remove a slide and its package parts.
    insert_slide         — Add a slide at a specific index (not just append).
    add_slide            — Validate JSON, render a template, store metadata.
    edit_slide           — Re-render an existing slide in place with new JSON.
    add_layout_slide     — Render a raw (template-less) grid Layout onto a slide.
    new_grid_slide       — Create an empty grid slide ready for add_cell.
    add_cell             — Append an element to a grid slide and re-render.
    set_cell             — Update one cell's kind/placement/look/props.
    remove_cell          — Drop one cell from a grid slide and re-render.
    set_slide            — Update grid classes / frame info / frame in place.
    remove_slide         — Delete a slide by index with bounds checking.
    get_slide_info       — Read template id + JSON data from a single slide.
    list_slides_info     — Summarize all slides for doc info.
    _clear_slide_shapes  — Wipe custom shapes and placeholder text before re-render.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pptx import Presentation

from slides_factory import template as registry
from slides_factory.brand import BrandTheme, load_brand
from slides_factory.brand.doc import get_document_brand_path, set_document_brand
from slides_factory.frame import DEFAULT_PLAYGROUND, get_frame, resolve_frame_id
from slides_factory.frame_info import FrameInfo
from slides_factory.layout.pct import resolve_pct_box
from slides_factory.layout.render import render_layout
from slides_factory.layout_spec import Layout
from slides_factory.locale import (
    get_document_locale,
    get_document_rtl,
    resolve_render_settings,
    set_document_settings,
)
from slides_factory.metadata import fallback_extract, read_metadata, write_metadata
from slides_factory.render_context import RenderContext

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_THEME = PACKAGE_ROOT / "themes" / "default.pptx"


def ensure_default_theme() -> Path:
    """Create the default theme if it does not exist."""
    from pptx.util import Emu

    if DEFAULT_THEME.exists():
        existing = Presentation(str(DEFAULT_THEME))
        # Regenerate if an older build used a mismatched slide width.
        if int(existing.slide_width) != Emu(9144000):
            DEFAULT_THEME.unlink()
        else:
            return DEFAULT_THEME

    DEFAULT_THEME.parent.mkdir(parents=True, exist_ok=True)
    prs = Presentation()
    # Keep the default 10" x 7.5" size so layout placeholders match slide width.

    # Remove any default slides so the theme is a blank shell.
    while len(prs.slides) > 0:
        delete_slide(prs, 0)

    prs.save(DEFAULT_THEME)
    return DEFAULT_THEME


def open_document(path: Path) -> Presentation:
    """Load an existing .pptx presentation from disk."""
    return Presentation(str(path))


def load_document_brand(prs: Presentation) -> BrandTheme | None:
    """Load brand YAML stored on the document, if configured."""
    brand_path = get_document_brand_path(prs)
    if brand_path is None or not brand_path.is_file():
        return None
    return load_brand(brand_path)


def new_presentation(
    theme: Path | None = None,
    *,
    brand: Path | None = None,
    rtl: bool = False,
    locale: str = "en",
) -> Presentation:
    """Create an in-memory presentation shell without writing to disk."""
    brand_theme: BrandTheme | None = None
    if brand is not None:
        brand_theme = load_brand(brand)

    if theme is not None:
        theme_path = theme
    elif brand_theme and brand_theme.base_pptx is not None:
        theme_path = brand_theme.resolve_base_pptx()
    else:
        theme_path = ensure_default_theme()

    prs = Presentation(str(theme_path))
    if brand_theme is not None:
        brand_theme.apply_page_size(prs)
    while len(prs.slides) > 0:
        delete_slide(prs, 0)
    set_document_settings(prs, rtl=rtl, locale=locale)
    if brand is not None:
        set_document_brand(prs, brand.resolve())
    return prs


def create_document(
    output: Path,
    theme: Path | None = None,
    *,
    brand: Path | None = None,
    rtl: bool = False,
    locale: str = "en",
) -> Presentation:
    """Create a new empty presentation and save it to output."""
    prs = new_presentation(theme=theme, brand=brand, rtl=rtl, locale=locale)
    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output))
    return Presentation(str(output))


def update_document_rtl(
    prs: Presentation,
    *,
    rtl: bool,
    locale: str | None = None,
) -> dict[str, str | bool]:
    """Update document RTL/locale flags stored in core properties."""
    active_locale = locale or get_document_locale(prs)
    set_document_settings(prs, rtl=rtl, locale=active_locale)
    return {"rtl": rtl, "locale": get_document_locale(prs)}


def save_document(prs: Presentation, path: Path) -> None:
    """Persist a presentation to the given path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(path))
    brand = load_document_brand(prs)
    if brand is not None:
        from slides_factory.layout.font_embed import embed_fonts_in_pptx

        fonts = brand.fonts.embeddable_fonts(brand)
        if fonts:
            embed_fonts_in_pptx(path, fonts)


def _clear_slide_shapes(slide) -> None:
    """Remove custom shapes and clear placeholder text before re-render."""
    sp_tree = slide.shapes._spTree
    for shape in list(slide.shapes):
        if shape.is_placeholder:
            if shape.has_text_frame:
                shape.text_frame.clear()
        else:
            sp_tree.remove(shape._element)


def delete_slide(prs: Presentation, index: int) -> None:
    """Remove a slide and clean up its relationships and package parts."""
    slide = prs.slides[index]
    slide_ids = prs.slides._sldIdLst
    r_id = slide_ids[index].rId
    prs.part.drop_rel(r_id)
    del slide_ids[index]
    partname = slide.part.partname
    parts = getattr(prs.part.package, "_parts", None)
    if parts is not None and partname in parts:
        del parts[partname]


def insert_slide(prs: Presentation, layout, index: int):
    """Add a slide and move it to the requested index."""
    prs.slides.add_slide(layout)
    slide_ids = prs.slides._sldIdLst
    new_id = slide_ids[-1]
    slide_ids.remove(new_id)
    slide_ids.insert(index, new_id)
    return prs.slides[index]


def _render_frame(
    slide,
    frame_tpl,
    ctx,
    brand: BrandTheme | None,
    info: FrameInfo | None = None,
) -> None:
    """Render frame chrome and optionally lock shapes added by the frame."""
    if frame_tpl is None:
        return
    existing = {id(s._element) for s in slide.shapes}
    frame_tpl.render(slide, ctx, info if info is not None else FrameInfo())
    if brand is not None and brand.lock_frame_shapes:
        from slides_factory.layout.locks import lock_shapes_added

        lock_shapes_added(slide, existing)


def _attach_playground(ctx: RenderContext, frame_tpl) -> RenderContext:
    """Attach the resolved playground region (frame's, or a default) to ctx."""
    if frame_tpl is not None and not frame_tpl.allows_layout:
        return ctx
    if frame_tpl is not None:
        region = frame_tpl.playground_box(ctx)
    else:
        region = resolve_pct_box(ctx, DEFAULT_PLAYGROUND)
    return ctx.with_playground(region)


def _ensure_frame_allows_layout(frame_tpl) -> None:
    if frame_tpl is not None and not frame_tpl.allows_layout:
        raise ValueError(
            f"Frame {frame_tpl.id!r} does not allow grid layout content. "
            "Use add_frame_slide for this frame type."
        )


def _frame_info_from(validated: Any) -> FrameInfo:
    """Extract a FrameInfo from validated template data, if present."""
    info = getattr(validated, "frame_info", None)
    return info if isinstance(info, FrameInfo) else FrameInfo()


def _resolve_frame_info(template: Any, validated: Any) -> FrameInfo:
    """Resolve frame info from a class template override or nested input field."""
    from slides_factory.templating import Template

    if isinstance(template, Template):
        return template.frame_info(validated)
    return _frame_info_from(validated)


def add_slide(
    prs: Presentation,
    template_id: str,
    data: dict[str, Any],
    *,
    at: int | None = None,
    frame: str | None = None,
    rtl: bool | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    """Add a rendered slide to the presentation and return result metadata."""
    template = registry.get_template(template_id)
    validated = template.validate_data(data)
    layout = template.resolve_layout(prs)
    active_rtl, active_locale = resolve_render_settings(prs, rtl=rtl, locale=locale)
    brand = load_document_brand(prs)
    if frame and brand is None:
        raise ValueError(
            "Cannot use --frame without a brand on the document. "
            "Create the deck with: doc create --brand <theme.yaml>"
        )
    frame_id = resolve_frame_id(
        frame=frame,
        template_default=type(template).default_frame,
        brand_default=brand.default_frame if brand else None,
    )
    frame_tpl = get_frame(frame_id) if brand else None
    ctx = RenderContext.from_presentation(
        prs, rtl=active_rtl, locale=active_locale, brand=brand
    )
    if frame_tpl is not None:
        ctx = ctx.with_palette(frame_tpl.palette)
    ctx = _attach_playground(ctx, frame_tpl)

    if at is None:
        slide = prs.slides.add_slide(layout)
        index = len(prs.slides) - 1
    else:
        slide = insert_slide(prs, layout, at)
        index = at

    _render_frame(slide, frame_tpl, ctx, brand, _resolve_frame_info(template, validated))
    template.render(slide, validated, ctx)
    write_metadata(
        slide,
        template_id,
        validated.model_dump(mode="json"),
        frame_id=frame_id if brand else None,
    )

    result: dict[str, Any] = {
        "slide_index": index,
        "template_id": template_id,
        "rtl": active_rtl,
        "locale": active_locale,
        "data": validated.model_dump(mode="json"),
    }
    if brand is not None:
        result["frame_id"] = frame_id
    return result


def add_frame_slide(
    prs: Presentation,
    frame_id: str,
    data: dict[str, Any],
    *,
    at: int | None = None,
    rtl: bool | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    """Add a frame-only slide (no template, no grid playground) and return metadata."""
    frame_tpl = get_frame(frame_id)
    brand = load_document_brand(prs)
    if brand is None:
        raise ValueError(
            "Cannot add a frame slide without a brand on the document. "
            "Create the deck with: doc create --brand <theme.yaml>"
        )
    validated = frame_tpl.validate_info(data)
    active_rtl, active_locale = resolve_render_settings(prs, rtl=rtl, locale=locale)
    ctx = RenderContext.from_presentation(
        prs, rtl=active_rtl, locale=active_locale, brand=brand
    )
    ctx = ctx.with_palette(frame_tpl.palette)

    pptx_layout = _blank_layout(prs)
    if at is None:
        slide = prs.slides.add_slide(pptx_layout)
        index = len(prs.slides) - 1
    else:
        slide = insert_slide(prs, pptx_layout, at)
        index = at

    _render_frame(slide, frame_tpl, ctx, brand, validated)
    payload = validated.model_dump(mode="json")
    write_metadata(slide, FRAME_SLIDE_ID, payload, frame_id=frame_id)

    return {
        "slide_index": index,
        "kind": "frame",
        "frame_id": frame_id,
        "rtl": active_rtl,
        "locale": active_locale,
        "data": payload,
    }


def edit_frame_slide(
    prs: Presentation,
    index: int,
    data: dict[str, Any],
    *,
    rtl: bool | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    """Re-render an existing frame-only slide in place with new info data."""
    if index < 0 or index >= len(prs.slides):
        raise IndexError(f"Slide index {index} out of range (0-{len(prs.slides) - 1})")

    existing_meta = read_metadata(prs.slides[index])
    if not existing_meta or existing_meta.get("template_id") != FRAME_SLIDE_ID:
        raise ValueError(f"Slide {index} is not a frame-only slide.")
    frame_id = existing_meta.get("frame_id")
    if not frame_id:
        raise ValueError(f"Slide {index} has no frame_id in metadata.")

    frame_tpl = get_frame(frame_id)
    validated = frame_tpl.validate_info(data)
    brand = load_document_brand(prs)
    active_rtl, active_locale = resolve_render_settings(prs, rtl=rtl, locale=locale)
    ctx = RenderContext.from_presentation(
        prs, rtl=active_rtl, locale=active_locale, brand=brand
    )
    ctx = ctx.with_palette(frame_tpl.palette)

    slide = prs.slides[index]
    _clear_slide_shapes(slide)
    _render_frame(slide, frame_tpl, ctx, brand, validated)
    payload = validated.model_dump(mode="json")
    write_metadata(slide, FRAME_SLIDE_ID, payload, frame_id=frame_id)

    return {
        "slide_index": index,
        "kind": "frame",
        "frame_id": frame_id,
        "rtl": active_rtl,
        "locale": active_locale,
        "data": payload,
    }


def edit_slide(
    prs: Presentation,
    index: int,
    data: dict[str, Any],
    *,
    template_id: str | None = None,
    frame: str | None = None,
    rtl: bool | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    """Re-render an existing slide with new data, preserving its index."""
    if index < 0 or index >= len(prs.slides):
        raise IndexError(f"Slide index {index} out of range (0-{len(prs.slides) - 1})")

    existing_meta = read_metadata(prs.slides[index])
    resolved_template_id = template_id or (
        existing_meta.get("template_id") if existing_meta else None
    )
    if not resolved_template_id:
        raise ValueError(
            f"Slide {index} has no template metadata. Pass --template explicitly."
        )

    template = registry.get_template(resolved_template_id)
    validated = template.validate_data(data)
    payload = validated.model_dump(mode="json")

    old_template_id = existing_meta.get("template_id") if existing_meta else None
    active_rtl, active_locale = resolve_render_settings(prs, rtl=rtl, locale=locale)
    brand = load_document_brand(prs)
    if frame and brand is None:
        raise ValueError(
            "Cannot use --frame without a brand on the document. "
            "Create the deck with: doc create --brand <theme.yaml>"
        )
    changing_template = bool(
        template_id and old_template_id and template_id != old_template_id
    )
    stored_frame = None if changing_template else (
        existing_meta.get("frame_id") if existing_meta else None
    )
    frame_id = resolve_frame_id(
        frame=frame,
        stored=stored_frame,
        template_default=type(template).default_frame,
        brand_default=brand.default_frame if brand else None,
    )
    frame_tpl = get_frame(frame_id) if brand else None
    token_ctx = RenderContext.from_presentation(
        prs, rtl=active_rtl, locale=active_locale, brand=brand
    )
    if frame_tpl is not None:
        token_ctx = token_ctx.with_palette(frame_tpl.palette)
    token_ctx = _attach_playground(token_ctx, frame_tpl)
    if template_id and old_template_id and template_id != old_template_id:
        delete_slide(prs, index)
        return add_slide(
            prs,
            resolved_template_id,
            data,
            at=index,
            frame=frame,
            rtl=active_rtl,
            locale=active_locale,
        )

    slide = prs.slides[index]
    _clear_slide_shapes(slide)
    _render_frame(slide, frame_tpl, token_ctx, brand, _resolve_frame_info(template, validated))
    template.render(slide, validated, token_ctx)
    write_metadata(
        slide,
        resolved_template_id,
        payload,
        frame_id=frame_id if brand else None,
    )

    result: dict[str, Any] = {
        "slide_index": index,
        "template_id": resolved_template_id,
        "rtl": active_rtl,
        "locale": active_locale,
        "data": payload,
    }
    if brand is not None:
        result["frame_id"] = frame_id
    return result


# Sentinel so builder helpers can distinguish "leave unchanged" from "set to None".
_UNSET: Any = object()

# Reserved metadata id for raw (template-less) grid layouts authored directly
# via add_layout_slide / the slide-new + el-add CLI builder.
RAW_LAYOUT_ID = "$grid"

# Reserved metadata id for frame-only slides (cover/closing) with no template.
FRAME_SLIDE_ID = "$frame"


def _blank_layout(prs: Presentation):
    """Pick the 'Blank' slide layout, falling back to the first available layout."""
    fallback = None
    for layout in prs.slide_layouts:
        if layout.name == "Blank":
            return layout
        if fallback is None:
            fallback = layout
    if fallback is not None:
        return fallback
    raise ValueError("presentation has no slide layouts to render a grid into")


def _prepare_render(
    prs: Presentation,
    *,
    frame: str | None,
    rtl: bool | None,
    locale: str | None,
    stored_frame: str | None = None,
    template_default: str | None = None,
):
    """Resolve rtl/locale, brand, frame, and a playground-attached RenderContext."""
    active_rtl, active_locale = resolve_render_settings(prs, rtl=rtl, locale=locale)
    brand = load_document_brand(prs)
    if frame and brand is None:
        raise ValueError(
            "Cannot use --frame without a brand on the document. "
            "Create the deck with: doc create --brand <theme.yaml>"
        )
    frame_id = resolve_frame_id(
        frame=frame,
        stored=stored_frame,
        template_default=template_default,
        brand_default=brand.default_frame if brand else None,
    )
    frame_tpl = get_frame(frame_id) if brand else None
    ctx = RenderContext.from_presentation(
        prs, rtl=active_rtl, locale=active_locale, brand=brand
    )
    if frame_tpl is not None:
        ctx = ctx.with_palette(frame_tpl.palette)
    ctx = _attach_playground(ctx, frame_tpl)
    return ctx, frame_tpl, frame_id, brand, active_rtl, active_locale


def add_layout_slide(
    prs: Presentation,
    layout: dict[str, Any],
    *,
    at: int | None = None,
    frame: str | None = None,
    rtl: bool | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    """Render a raw grid Layout (no template) onto a new slide and store it."""
    validated = Layout.model_validate(layout)
    ctx, frame_tpl, frame_id, brand, active_rtl, active_locale = _prepare_render(
        prs, frame=frame, rtl=rtl, locale=locale
    )
    _ensure_frame_allows_layout(frame_tpl)
    pptx_layout = _blank_layout(prs)
    if at is None:
        slide = prs.slides.add_slide(pptx_layout)
        index = len(prs.slides) - 1
    else:
        slide = insert_slide(prs, pptx_layout, at)
        index = at

    _render_frame(slide, frame_tpl, ctx, brand, validated.frame_info)
    render_layout(slide, validated, ctx)
    payload = validated.model_dump(mode="json")
    write_metadata(slide, RAW_LAYOUT_ID, payload, frame_id=frame_id if brand else None)

    result: dict[str, Any] = {
        "slide_index": index,
        "kind": "grid",
        "rtl": active_rtl,
        "locale": active_locale,
        "data": payload,
    }
    if brand is not None:
        result["frame_id"] = frame_id
    return result


def _rerender_layout(
    prs: Presentation,
    index: int,
    layout: dict[str, Any],
    *,
    frame: str | None = None,
    rtl: bool | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    """Re-render an existing raw grid slide in place from a mutated Layout."""
    validated = Layout.model_validate(layout)
    existing_meta = read_metadata(prs.slides[index])
    stored_frame = existing_meta.get("frame_id") if existing_meta else None
    ctx, frame_tpl, frame_id, brand, active_rtl, active_locale = _prepare_render(
        prs, frame=frame, rtl=rtl, locale=locale, stored_frame=stored_frame
    )
    slide = prs.slides[index]
    _clear_slide_shapes(slide)
    _render_frame(slide, frame_tpl, ctx, brand, validated.frame_info)
    render_layout(slide, validated, ctx)
    payload = validated.model_dump(mode="json")
    write_metadata(slide, RAW_LAYOUT_ID, payload, frame_id=frame_id if brand else None)

    result: dict[str, Any] = {
        "slide_index": index,
        "kind": "grid",
        "rtl": active_rtl,
        "locale": active_locale,
        "data": payload,
    }
    if brand is not None:
        result["frame_id"] = frame_id
    return result


def _frame_info_payload(
    *,
    title: Any = _UNSET,
    subtitle: Any = _UNSET,
    page_number: Any = _UNSET,
    total_pages: Any = _UNSET,
    base: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge provided FrameInfo fields onto an optional base dict."""
    info = dict(base or {})
    if title is not _UNSET:
        info["title"] = title
    if subtitle is not _UNSET:
        info["subtitle"] = subtitle
    if page_number is not _UNSET:
        info["page_number"] = page_number
    if total_pages is not _UNSET:
        info["total_pages"] = total_pages
    return info


def _require_grid_data(prs: Presentation, index: int) -> dict[str, Any]:
    """Return a mutable copy of a grid slide's stored spec, or raise."""
    if index < 0 or index >= len(prs.slides):
        raise IndexError(f"Slide index {index} out of range (0-{len(prs.slides) - 1})")
    meta = read_metadata(prs.slides[index])
    if not meta or meta.get("template_id") != RAW_LAYOUT_ID:
        raise ValueError(
            f"Slide {index} is not a raw grid slide; cells can only be edited on slides "
            "created with 'slide new'."
        )
    data = meta.get("data")
    spec: dict[str, Any] = dict(data) if isinstance(data, dict) else {}
    spec["cells"] = [dict(cell) for cell in spec.get("cells", [])]
    return spec


def _validate_element_props(kind: str, props: dict[str, Any]) -> None:
    """Validate raw props against a registered element before re-rendering."""
    from slides_factory.app import get_app

    get_app().get_element(kind).validate_props(props or {})


def new_grid_slide(
    prs: Presentation,
    *,
    grid: str = "",
    frame: str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    page_number: int | None = None,
    total_pages: int | None = None,
    at: int | None = None,
    rtl: bool | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    """Create an empty grid slide ready for ``add_cell`` calls."""
    info = _frame_info_payload(
        title=title if title is not None else _UNSET,
        subtitle=subtitle if subtitle is not None else _UNSET,
        page_number=page_number if page_number is not None else _UNSET,
        total_pages=total_pages if total_pages is not None else _UNSET,
    )
    data: dict[str, Any] = {"frame_info": info, "grid": grid, "cells": []}
    return add_layout_slide(prs, data, at=at, frame=frame, rtl=rtl, locale=locale)


def add_cell(
    prs: Presentation,
    index: int,
    *,
    kind: str,
    at: str = "",
    style: str = "",
    props: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append an element to a grid slide and re-render it in place."""
    spec = _require_grid_data(prs, index)
    props = props or {}
    _validate_element_props(kind, props)
    spec["cells"].append(
        {"at": at, "element": {"kind": kind, "style": style, "props": props}}
    )
    result = _rerender_layout(prs, index, spec)
    result["cell_index"] = len(spec["cells"]) - 1
    return result


def set_cell(
    prs: Presentation,
    index: int,
    cell: int,
    *,
    kind: Any = _UNSET,
    at: Any = _UNSET,
    style: Any = _UNSET,
    props: Any = _UNSET,
) -> dict[str, Any]:
    """Update one cell on a grid slide; only provided fields change."""
    spec = _require_grid_data(prs, index)
    cells = spec["cells"]
    if cell < 0 or cell >= len(cells):
        raise IndexError(f"Cell index {cell} out of range (0-{len(cells) - 1})")

    entry = dict(cells[cell])
    element = dict(entry.get("element", {}))
    if kind is not _UNSET:
        element["kind"] = kind
    if style is not _UNSET:
        element["style"] = style
    if props is not _UNSET:
        element["props"] = props
    if at is not _UNSET:
        entry["at"] = at

    _validate_element_props(element.get("kind", ""), element.get("props") or {})
    entry["element"] = element
    cells[cell] = entry

    result = _rerender_layout(prs, index, spec)
    result["cell_index"] = cell
    return result


def remove_cell(prs: Presentation, index: int, cell: int) -> dict[str, Any]:
    """Remove one cell from a grid slide and re-render it in place."""
    spec = _require_grid_data(prs, index)
    cells = spec["cells"]
    if cell < 0 or cell >= len(cells):
        raise IndexError(f"Cell index {cell} out of range (0-{len(cells) - 1})")
    cells.pop(cell)
    result = _rerender_layout(prs, index, spec)
    result["removed_cell"] = cell
    return result


def set_slide(
    prs: Presentation,
    index: int,
    *,
    grid: Any = _UNSET,
    frame: str | None = None,
    title: Any = _UNSET,
    subtitle: Any = _UNSET,
    page_number: Any = _UNSET,
    total_pages: Any = _UNSET,
    rtl: bool | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    """Update slide-level settings (grid classes, frame info, frame) in place."""
    spec = _require_grid_data(prs, index)
    if grid is not _UNSET:
        spec["grid"] = grid
    spec["frame_info"] = _frame_info_payload(
        title=title,
        subtitle=subtitle,
        page_number=page_number,
        total_pages=total_pages,
        base=spec.get("frame_info") if isinstance(spec.get("frame_info"), dict) else None,
    )
    return _rerender_layout(prs, index, spec, frame=frame, rtl=rtl, locale=locale)


def remove_slide(prs: Presentation, index: int) -> None:
    """Delete a slide by zero-based index."""
    if index < 0 or index >= len(prs.slides):
        raise IndexError(f"Slide index {index} out of range (0-{len(prs.slides) - 1})")
    delete_slide(prs, index)


def get_slide_info(prs: Presentation, index: int) -> dict[str, Any]:
    """Return template id and JSON data for one slide (used by doc get)."""
    if index < 0 or index >= len(prs.slides):
        raise IndexError(f"Slide index {index} out of range (0-{len(prs.slides) - 1})")

    slide = prs.slides[index]
    meta = read_metadata(slide)
    if meta:
        template_id = meta["template_id"]
        if template_id == RAW_LAYOUT_ID:
            validated_layout = Layout.model_validate(meta["data"])
            info = {
                "slide_index": index,
                "template_id": None,
                "kind": "grid",
                "data": validated_layout.model_dump(mode="json"),
            }
            if meta.get("frame_id"):
                info["frame_id"] = meta["frame_id"]
            return info
        if template_id == FRAME_SLIDE_ID:
            frame_id = meta.get("frame_id")
            if not frame_id:
                raise ValueError(f"Slide {index} frame metadata is missing frame_id.")
            frame_tpl = get_frame(frame_id)
            validated = frame_tpl.validate_info(meta["data"])
            return {
                "slide_index": index,
                "template_id": None,
                "kind": "frame",
                "frame_id": frame_id,
                "data": validated.model_dump(mode="json"),
            }
        template = registry.get_template(template_id)
        validated = template.validate_data(meta["data"])
        info: dict[str, Any] = {
            "slide_index": index,
            "template_id": template_id,
            "data": validated.model_dump(mode="json"),
        }
        if meta.get("frame_id"):
            info["frame_id"] = meta["frame_id"]
        return info

    fallback = fallback_extract(slide)
    return {
        "slide_index": index,
        "template_id": None,
        "data": fallback,
        "note": "No template metadata found; returned best-effort extraction",
    }


def list_slides_info(prs: Presentation) -> dict[str, Any]:
    """Return slide count, RTL/locale flags, and per-slide summaries."""
    slides: list[dict[str, Any]] = []
    for index in range(len(prs.slides)):
        slide = prs.slides[index]
        meta = read_metadata(slide)
        raw_layout = bool(meta and meta.get("template_id") == RAW_LAYOUT_ID)
        frame_only = bool(meta and meta.get("template_id") == FRAME_SLIDE_ID)
        title_preview = slide.shapes.title.text if slide.shapes.title else ""
        if not title_preview and meta and isinstance(meta.get("data"), dict):
            data = meta["data"]
            frame_info = data.get("frame_info") if isinstance(data.get("frame_info"), dict) else {}
            title_preview = str(
                data.get("title")
                or data.get("heading")
                or data.get("thank_you_message")
                or frame_info.get("title")
                or ""
            )

        entry: dict[str, Any] = {
            "index": index,
            "template_id": None
            if raw_layout or frame_only
            else (meta.get("template_id") if meta else None),
            "title_preview": title_preview[:80],
        }
        if raw_layout:
            entry["kind"] = "grid"
        if frame_only:
            entry["kind"] = "frame"
        if meta and meta.get("frame_id"):
            entry["frame_id"] = meta["frame_id"]
        slides.append(entry)
    info: dict[str, Any] = {
        "slide_count": len(slides),
        "rtl": get_document_rtl(prs),
        "locale": get_document_locale(prs),
        "slides": slides,
    }
    brand_path = get_document_brand_path(prs)
    if brand_path is not None:
        info["brand"] = str(brand_path)
    return info
