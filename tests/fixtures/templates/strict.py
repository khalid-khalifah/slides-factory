"""Template with required fields only — for validation edge-case tests."""

from typing import Annotated

from pydantic import Field

from slides_factory.template_input import TemplateInput
from slides_factory.templating import Template, at
from tests.fixtures.app import app


class StrictInput(TemplateInput):
    title: Annotated[str, Field(description="Required title")]
    count: Annotated[int, Field(description="Required count")]


@app.template(
    "strict",
    name="Strict",
    description="All fields required",
    grid="grid-rows-1",
    layout_name="Blank",
    tags=["test"],
)
class Strict(Template):
    input_model = StrictInput

    @at("", kind="text", style="text-xl font-bold text-primary")
    def headline(self, data: StrictInput) -> dict:
        return {"text": f"{data.title} ({data.count})"}
