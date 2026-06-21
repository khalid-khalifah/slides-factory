"""Edge cases for function-to-template registration and input model building."""

from __future__ import annotations

from typing import Annotated

import pytest
from pptx.slide import Slide
from pydantic import BaseModel, Field, ValidationError

from slides_factory.app import SlideFactory
from slides_factory.registration import (
    frame_from_function,
    input_model_from_function,
    normalize_tags,
    template_from_function,
)
from slides_factory.render_context import RenderContext
from slides_factory.template_input import TemplateInput
from tests.fixtures.palettes import TEST_LIGHT


class RenderInput(TemplateInput):
    title: str
    note: str = ""


class StrictInput(TemplateInput):
    title: str
    count: int


class Item(BaseModel):
    label: str
    value: int


class NestedInput(TemplateInput):
    items: list[Item]


class CaptureInput(TemplateInput):
    title: str
    body: str = ""


def _render(slide: Slide, ctx: RenderContext, data: RenderInput) -> None:
    pass


def _render_required(slide: Slide, ctx: RenderContext, data: StrictInput) -> None:
    pass


def _render_no_data(slide: Slide, ctx: RenderContext) -> None:
    pass


def _render_multi(
    slide: Slide,
    ctx: RenderContext,
    data: RenderInput,
    extra: str,
) -> None:
    pass


def _render_nested(slide: Slide, ctx: RenderContext, data: NestedInput) -> None:
    pass


def test_input_model_extracts_template_input_subclass():
    model = input_model_from_function(_render)
    assert model is RenderInput
    instance = model.model_validate({"title": "Hi"})
    assert instance.title == "Hi"
    assert instance.note == ""


def test_input_model_marks_required_fields():
    model = input_model_from_function(_render_required)
    with pytest.raises(ValidationError):
        model.model_validate({"title": "only title"})


class DescribedInput(TemplateInput):
    title: Annotated[str, Field(description="The headline")]


def _render_described(slide: Slide, ctx: RenderContext, data: DescribedInput) -> None:
    pass


def test_input_model_preserves_field_descriptions():
    model = input_model_from_function(_render_described)
    schema = model.model_json_schema()
    assert schema["properties"]["title"]["description"] == "The headline"


def test_input_model_rejects_no_data_parameters():
    with pytest.raises(TypeError, match="TemplateInput parameter"):
        input_model_from_function(_render_no_data)


def test_input_model_rejects_multiple_data_parameters():
    with pytest.raises(TypeError, match="exactly one TemplateInput"):
        input_model_from_function(_render_multi)


def test_input_model_supports_nested_models():
    model = input_model_from_function(_render_nested)
    instance = model.model_validate({"items": [{"label": "a", "value": 1}]})
    assert instance.items[0].label == "a"


def test_normalize_tags_lowercases_and_dedupes():
    assert normalize_tags(["Content", "LIST", "content"]) == ("content", "list")
    assert normalize_tags(None) == ()


def test_normalize_tags_rejects_empty_string():
    with pytest.raises(ValueError, match="empty strings"):
        normalize_tags(["valid", "  "])


def test_template_from_function_stores_tags():
    tpl = template_from_function(
        _render,
        template_id="tagged",
        name="Tagged",
        description="",
        layout_name=None,
        extract=None,
        tags=["Content", "Demo"],
    )
    assert type(tpl).tags == ("content", "demo")


def test_template_render_invokes_function_with_validated_data():
    calls: list[CaptureInput] = []

    def capture(slide: Slide, ctx: RenderContext, data: CaptureInput) -> None:
        calls.append(data)

    tpl = template_from_function(
        capture,
        template_id="cap",
        name="Capture",
        description="",
        layout_name="Title and Content",
        extract=None,
    )
    validated = tpl.input_model.model_validate({"title": "T", "body": "B"})
    tpl.render(Slide.__new__(Slide), validated, RenderContext())  # type: ignore[arg-type]
    assert len(calls) == 1
    assert calls[0].title == "T"
    assert calls[0].body == "B"


def test_template_extract_validates_dict_result():
    def extract(slide: Slide):
        return {"title": "from slide", "note": "text"}

    tpl = template_from_function(
        _render,
        template_id="ext",
        name="Extract",
        description="",
        layout_name=None,
        extract=extract,
    )
    result = tpl.extract(Slide.__new__(Slide))  # type: ignore[arg-type]
    assert result.title == "from slide"
    assert result.note == "text"


def test_template_extract_without_handler_raises():
    tpl = template_from_function(
        _render,
        template_id="no-ext",
        name="No extract",
        description="",
        layout_name=None,
        extract=None,
    )
    with pytest.raises(NotImplementedError, match="no extract"):
        tpl.extract(Slide.__new__(Slide))  # type: ignore[arg-type]


def test_template_from_function_preserves_default_frame():
    tpl = template_from_function(
        _render,
        template_id="with-default",
        name="With default",
        description="",
        layout_name=None,
        extract=None,
        default_frame="plain",
    )
    assert type(tpl).default_frame == "plain"


def test_frame_from_function_wraps_render():
    calls: list[str] = []

    def paint(slide: Slide, ctx: RenderContext) -> None:
        calls.append("painted")

    frame = frame_from_function(
        paint,
        frame_id="paint",
        name="Paint",
        description="",
        palette=TEST_LIGHT,
    )
    frame.render(Slide.__new__(Slide), RenderContext())  # type: ignore[arg-type]
    assert calls == ["painted"]


class DupOneInput(TemplateInput):
    title: str


class DupTwoInput(TemplateInput):
    title: str


def test_duplicate_template_registration_replaces():
    factory = SlideFactory("dup-template")

    @factory.template("dup", name="One")
    def one(slide: Slide, ctx: RenderContext, data: DupOneInput) -> None:
        pass

    @factory.template("dup", name="Two")
    def two(slide: Slide, ctx: RenderContext, data: DupTwoInput) -> None:
        pass

    factory._discovered_template_packages.add("test")
    assert factory.get_template("dup").name == "Two"


def test_duplicate_frame_registration_replaces():
    factory = SlideFactory("dup-frame")

    @factory.frame("dup", name="One", palette=TEST_LIGHT)
    def one(slide: Slide, ctx: RenderContext) -> None:
        pass

    @factory.frame("dup", name="Two", palette=TEST_LIGHT)
    def two(slide: Slide, ctx: RenderContext) -> None:
        pass

    factory._discovered_frame_packages.add("test")
    assert factory.get_frame("dup").name == "Two"
