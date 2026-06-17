"""Template with typed nested props — for validation edge-case tests."""

from slides_factory.templating import Template, at
from tests.fixtures.app import app


@app.template(
    "strict",
    name="Strict",
    description="Nested headline props for validation tests",
    grid="grid-rows-1",
    layout_name="Blank",
    tags=["test"],
)
class Strict(Template):
    @at("", kind="text", style="text-xl font-bold text-primary")
    def headline(self): ...
