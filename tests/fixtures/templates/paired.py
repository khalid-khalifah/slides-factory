"""Template with a default frame for resolution tests."""

from slides_factory.templating import Template, at
from tests.fixtures.app import app


@app.template(
    "paired",
    name="Paired",
    description="Template with default_frame=plain",
    grid="grid-rows-1",
    layout_name="Blank",
    default_frame="plain",
)
class Paired(Template):
    @at("", kind="text")
    def headline(self): ...
