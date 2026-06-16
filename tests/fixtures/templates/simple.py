"""Minimal title-and-body class template for core document tests."""

from typing import Annotated

from pydantic import Field

from slides_factory.template_input import TemplateInput
from slides_factory.templating import Template, at
from tests.fixtures.app import app


class SimpleInput(TemplateInput):
    title: Annotated[str, Field(description="Slide title")]
    body: Annotated[str, Field(description="Body text")] = ""


@app.template(
    "simple",
    name="Simple",
    description="Title and optional body for core tests",
    grid="grid-rows-[1_3] gap-4",
    layout_name="Blank",
    tags=["content", "test"],
)
class Simple(Template):
    input_model = SimpleInput

    @at("", kind="text", style="text-2xl font-bold text-primary")
    def title(self, data: SimpleInput) -> dict:
        return {"text": data.title}

    @at("", kind="text", style="text-base text-primary")
    def body(self, data: SimpleInput) -> dict:
        return {"text": data.body}
