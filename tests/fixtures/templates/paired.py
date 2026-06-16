"""Template with a default frame for resolution tests."""

from typing import Annotated

from pydantic import Field

from slides_factory.template_input import TemplateInput
from slides_factory.templating import Template, at
from tests.fixtures.app import app


class PairedInput(TemplateInput):
    title: Annotated[str, Field(description="Slide title")]


@app.template(
    "paired",
    name="Paired",
    description="Template with default_frame=plain",
    grid="grid-rows-1",
    layout_name="Blank",
    default_frame="plain",
)
class Paired(Template):
    input_model = PairedInput

    @at("", kind="text", style="text-2xl font-bold text-primary")
    def title(self, data: PairedInput) -> dict:
        return {"text": data.title}
