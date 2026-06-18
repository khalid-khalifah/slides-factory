"""Minimal headline-and-body class template for core document tests."""

from slides_factory.templating import Template, at
from tests.fixtures.app import app


@app.template(
    "simple",
    name="Simple",
    description="Title and optional body for core tests",
    grid="grid-rows-[1_3] gap-4",
    layout_name="Blank",
    tags=["content", "test"],
)
class Simple(Template):
    @at("", kind="text")
    def headline(self): ...

    @at("", kind="text")
    def body(self): ...
