"""Tests for frame info models and the frame render signature."""

from __future__ import annotations

from pptx.slide import Slide
from pydantic import BaseModel

from slides_factory.frame import DEFAULT_PLAYGROUND
from slides_factory.frame_info import EmptyFrameInput
from slides_factory.layout.pct import PctBox, resolve_pct_box
from slides_factory.registration import frame_from_function
from slides_factory.render_context import RenderContext
from tests.fixtures.palettes import TEST_LIGHT


class SampleInfo(BaseModel):
    title: str | None = None
    page_number: int | None = None


def _ctx() -> RenderContext:
    return RenderContext(slide_width=9144000, slide_height=6858000)


def test_legacy_two_arg_frame_still_works():
    calls: list[str] = []

    def legacy(slide: Slide, ctx: RenderContext) -> None:
        calls.append("painted")

    frame = frame_from_function(
        legacy, frame_id="legacy", name="Legacy", description="", palette=TEST_LIGHT
    )
    frame.render(Slide.__new__(Slide), _ctx())
    frame.render(Slide.__new__(Slide), _ctx(), SampleInfo(title="x"))
    assert calls == ["painted", "painted"]


def test_three_arg_frame_receives_validated_info():
    received: list[SampleInfo] = []

    def modern(slide: Slide, ctx: RenderContext, info: SampleInfo) -> None:
        received.append(info)

    frame = frame_from_function(
        modern,
        frame_id="modern",
        name="Modern",
        description="",
        palette=TEST_LIGHT,
        frame_input=SampleInfo,
    )
    frame.render(Slide.__new__(Slide), _ctx(), SampleInfo(title="Q3", page_number=2))
    assert received[0].title == "Q3"
    assert received[0].page_number == 2


def test_three_arg_frame_defaults_to_empty_model():
    received: list[EmptyFrameInput] = []

    def modern(slide: Slide, ctx: RenderContext, info: EmptyFrameInput) -> None:
        received.append(info)

    frame = frame_from_function(
        modern, frame_id="modern", name="Modern", description="", palette=TEST_LIGHT
    )
    frame.render(Slide.__new__(Slide), _ctx())
    assert received[0] == EmptyFrameInput()


def test_playground_box_uses_declared_region():
    box = PctBox(left=10, top=25, width=80, height=65)
    frame = frame_from_function(
        (lambda slide, ctx, info: None),
        frame_id="pg",
        name="PG",
        description="",
        palette=TEST_LIGHT,
        playground=box,
        frame_input=EmptyFrameInput,
    )
    ctx = _ctx()
    assert frame.playground_box(ctx) == resolve_pct_box(ctx, box)


def test_playground_box_falls_back_to_default():
    frame = frame_from_function(
        (lambda slide, ctx: None),
        frame_id="nopg",
        name="NoPG",
        description="",
        palette=TEST_LIGHT,
    )
    ctx = _ctx()
    assert frame.playground_box(ctx) == resolve_pct_box(ctx, DEFAULT_PLAYGROUND)


def test_frame_input_validates_fields():
    info = SampleInfo.model_validate({"title": "Hi", "page_number": 3})
    assert info.title == "Hi"
    assert info.page_number == 3
    assert SampleInfo() == SampleInfo(title=None, page_number=None)
