"""Tests for preview frame selection when switching templates."""

from __future__ import annotations

from pptx.slide import Slide

from slides_factory.preview.frames import frame_for_template
from slides_factory.registration import template_from_function
from slides_factory.render_context import RenderContext
from slides_factory.template_input import TemplateInput


class _TitleInput(TemplateInput):
    title: str


def _render(slide: Slide, ctx: RenderContext, data: _TitleInput) -> None:
    pass


def test_frame_for_template_uses_template_default():
    tpl = template_from_function(
        _render,
        template_id="paired",
        name="Paired",
        description="",
        layout_name=None,
        extract=None,
        default_frame="thank-you",
    )
    assert (
        frame_for_template(
            tpl,
            available_frame_ids=["basic", "thank-you"],
            brand_default_frame="basic",
        )
        == "thank-you"
    )


def test_frame_for_template_falls_back_to_brand_default():
    tpl = template_from_function(
        _render,
        template_id="generic",
        name="Generic",
        description="",
        layout_name=None,
        extract=None,
    )
    assert (
        frame_for_template(
            tpl,
            available_frame_ids=["basic", "thank-you"],
            brand_default_frame="basic",
        )
        == "basic"
    )


def test_frame_for_template_ignores_unknown_template_default():
    tpl = template_from_function(
        _render,
        template_id="paired",
        name="Paired",
        description="",
        layout_name=None,
        extract=None,
        default_frame="missing-frame",
    )
    assert (
        frame_for_template(
            tpl,
            available_frame_ids=["basic"],
            brand_default_frame="basic",
        )
        == "basic"
    )
