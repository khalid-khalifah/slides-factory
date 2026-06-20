"""The Layout Engine — converts high-level layout specifications into PPT shapes.

Classes:
    LayoutEngine — Handles the rendering logic for frames and grid layouts.
"""

from __future__ import annotations

from typing import Any

from pptx import Presentation
from pptx.slide import Slide
from pydantic import BaseModel

from slides_factory.brand import BrandTheme
from slides_factory.frame import DEFAULT_PLAYGROUND, get_frame, resolve_frame_id
from slides_factory.layout.pct import resolve_pct_box
from slides_factory.layout.render import render_layout
from slides_factory.layout_spec import Layout
from slides_factory.render_context import RenderContext


class LayoutEngine:
    """Handles the actual drawing of elements and frames onto a slide."""

    def __init__(self, prs: Presentation):
        self.prs = prs

    def resolve_blank_layout(self) -> Any:
        """Pick the 'Blank' slide layout, falling back to the first available layout."""
        fallback = None
        for layout in self.prs.slide_layouts:
            if layout.name == "Blank":
                return layout
            if fallback is None:
                fallback = layout
        if fallback is not None:
            return fallback
        raise ValueError("presentation has no slide layouts to render a grid into")

    def prepare_render(
        self,
        frame: str | None,
        rtl: bool | None,
        locale: str | None,
        stored_frame: str | None = None,
        template_default: str | None = None,
        frame_style: dict[str, Any] | BaseModel | None = None,
        brand: BrandTheme | None = None,
    ) -> tuple[RenderContext, Any, str, BrandTheme | None, bool, str]:
        """Resolve rtl/locale, brand, frame, and a playground-attached RenderContext."""
        from slides_factory.locale import resolve_render_settings

        active_rtl, active_locale = resolve_render_settings(
            self.prs, rtl=rtl, locale=locale
        )
        # If brand isn't provided, we try to load it from the document
        if brand is None:
            from slides_factory.brand import load_brand
            from slides_factory.brand.doc import get_document_brand_path

            brand_path = get_document_brand_path(self.prs)
            if brand_path and brand_path.is_file():
                brand = load_brand(brand_path)

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
            self.prs, rtl=active_rtl, locale=active_locale, brand=brand
        )
        if frame_tpl is not None:
            ctx = self._with_frame_palette(ctx, frame_tpl, frame_style)
        ctx = self._attach_playground(ctx, frame_tpl)
        return ctx, frame_tpl, frame_id, brand, active_rtl, active_locale

    def _with_frame_palette(
        self, ctx: RenderContext, frame_tpl, frame_style: Any
    ) -> RenderContext:
        """Attach the palette a frame will use at render time."""
        validated_style = (
            frame_tpl.validate_style(frame_style)
            if frame_style is not None
            else frame_tpl.frame_style()
        )
        return ctx.with_palette(frame_tpl.palette_for(ctx, validated_style))

    def _attach_playground(self, ctx: RenderContext, frame_tpl) -> RenderContext:
        """Attach the resolved playground region to ctx."""
        if frame_tpl is not None and not frame_tpl.allows_layout:
            return ctx
        if frame_tpl is not None:
            region = frame_tpl.playground_box(ctx)
        else:
            region = resolve_pct_box(ctx, DEFAULT_PLAYGROUND)
        return ctx.with_playground(region)

    def render_frame(
        self,
        slide: Slide,
        frame_tpl: Any,
        ctx: RenderContext,
        brand: BrandTheme | None,
        info: dict[str, Any] | BaseModel | None = None,
        style: dict[str, Any] | BaseModel | None = None,
    ) -> None:
        """Render frame chrome and optionally lock shapes added by the frame."""
        if frame_tpl is None:
            return
        existing = {id(s._element) for s in slide.shapes}

        if isinstance(info, BaseModel):
            validated_info = info
        elif info is not None:
            validated_info = frame_tpl.validate_info(
                dict(info) if isinstance(info, dict) else {}
            )
        else:
            validated_info = frame_tpl.validate_info({})

        if isinstance(style, BaseModel):
            validated_style = style
        elif style is not None:
            validated_style = frame_tpl.validate_style(
                dict(style) if isinstance(style, dict) else {}
            )
        else:
            validated_style = frame_tpl.frame_style()

        frame_tpl.render(slide, ctx, validated_info, validated_style)
        if brand is not None and brand.lock_frame_shapes:
            from slides_factory.layout.locks import lock_shapes_added

            lock_shapes_added(slide, existing)

    def ensure_frame_allows_layout(self, frame_tpl) -> None:
        if frame_tpl is not None and not frame_tpl.allows_layout:
            raise ValueError(
                f"Frame {frame_tpl.id!r} does not allow grid layout content."
            )

    def render_grid(self, slide: Slide, layout: Layout, ctx: RenderContext) -> None:
        """Core method to draw a grid layout onto a slide."""
        render_layout(slide, layout, ctx)
