"""Class-based templates built on top of the grid+element core.

Demonstrates the recommended authoring style: a typed input model plus one
``@at`` method per cell. The template is registered on a local factory so it
does not pollute the shared test catalog.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pptx.enum.shapes import MSO_SHAPE_TYPE
from typer.testing import CliRunner

import slides_factory.app as app_module
from slides_factory import document
from slides_factory.app import SlideFactory
from slides_factory.frame_info import FrameInfo
from slides_factory.layout_spec import Layout
from slides_factory.template_input import TemplateInput
from slides_factory.templating import Template, at

runner = CliRunner()


class KpiInput(TemplateInput):
    heading: str
    revenue: str
    customers: str


def _make_factory() -> SlideFactory:
    factory = SlideFactory("kpi-app")

    @factory.template(
        "kpi-duo",
        name="KPI Duo",
        description="A bold heading over two KPI cards side by side.",
        grid="grid-cols-2 grid-rows-[1_2] gap-4",
    )
    class KpiDuo(Template):
        input_model = KpiInput

        def frame_info(self, data: KpiInput) -> FrameInfo:
            return FrameInfo(title=data.heading)

        @at("col-span-2", kind="text", style="text-3xl font-bold text-primary")
        def heading(self, data: KpiInput) -> dict:
            return {"text": data.heading}

        @at("", kind="card", style="bg-surface rounded-md")
        def revenue(self, data: KpiInput) -> dict:
            return {"title": "Revenue", "value": data.revenue}

        @at("", kind="card", style="bg-surface rounded-md")
        def customers(self, data: KpiInput) -> dict:
            return {"title": "Customers", "value": data.customers}

    # Mark discovery so list_templates/get_template work on this isolated factory.
    factory._discovered_template_packages.add("test")
    return factory


@pytest.fixture
def kpi_factory():
    previous = app_module._active_app
    factory = _make_factory()
    app_module._active_app = factory
    try:
        yield factory
    finally:
        app_module._active_app = previous


def test_build_maps_typed_data_to_layout(kpi_factory: SlideFactory):
    template = kpi_factory.get_template("kpi-duo")
    data = template.validate_data(
        {"heading": "Q3", "revenue": "$1.2M", "customers": "8,400"}
    )
    layout = template.build(data)

    assert isinstance(layout, Layout)
    assert layout.grid == "grid-cols-2 grid-rows-[1_2] gap-4"
    assert layout.frame_info.title == "Q3"
    kinds = [c.element.kind for c in layout.cells]
    assert kinds == ["text", "card", "card"]
    assert layout.cells[0].at == "col-span-2"
    assert layout.cells[1].element.props == {"title": "Revenue", "value": "$1.2M"}


def test_template_round_trips_typed_input(kpi_factory: SlideFactory, tmp_path: Path):
    output = tmp_path / "kpi.pptx"
    prs = document.create_document(output)
    data = {"heading": "Q3", "revenue": "$1.2M", "customers": "8,400"}
    result = document.add_slide(prs, "kpi-duo", data)
    document.save_document(prs, output)

    assert result["template_id"] == "kpi-duo"

    prs = document.open_document(output)
    info = document.get_slide_info(prs, 0)
    assert info["template_id"] == "kpi-duo"
    # Metadata stores the typed input, not the expanded layout.
    assert info["data"] == data

    slide = prs.slides[0]
    cards = [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE]
    assert len(cards) == 2


def test_at_method_must_return_dict(kpi_factory: SlideFactory):
    factory = kpi_factory

    @factory.template("bad", name="Bad", description="", grid="grid-cols-1")
    class Bad(Template):
        input_model = KpiInput

        @at("", kind="text", style="")
        def oops(self, data: KpiInput) -> dict:
            return "not a dict"  # type: ignore[return-value]

    template = factory.get_template("bad")
    with pytest.raises(TypeError, match="must return a props dict"):
        template.build(template.validate_data(
            {"heading": "h", "revenue": "r", "customers": "c"}
        ))


def test_template_class_requires_input_model(kpi_factory: SlideFactory):
    with pytest.raises(TypeError, match="must set 'input_model'"):

        @kpi_factory.template("no-model", name="No Model", description="")
        class NoModel(Template):
            @at("", kind="text", style="")
            def x(self, data) -> dict:
                return {"text": "x"}


def test_cli_lists_and_inspects_templates(kpi_factory: SlideFactory):
    cli = kpi_factory.cli

    listing = json.loads(runner.invoke(cli, ["templates", "list", "--json"]).output)
    ids = {t["id"] for t in listing["data"]["templates"]}
    assert "kpi-duo" in ids
    summary = next(t for t in listing["data"]["templates"] if t["id"] == "kpi-duo")
    assert summary["grid"] == "grid-cols-2 grid-rows-[1_2] gap-4"
    assert "two KPI cards" in summary["description"]

    inspect = json.loads(
        runner.invoke(cli, ["templates", "inspect", "kpi-duo", "--json"]).output
    )
    props = inspect["data"]["json_schema"]["properties"]
    assert {"heading", "revenue", "customers"} <= set(props)


def test_cli_slide_add_from_template(kpi_factory: SlideFactory, tmp_path: Path):
    cli = kpi_factory.cli
    deck = tmp_path / "deck.pptx"
    runner.invoke(cli, ["doc", "create", "-o", str(deck)])

    data = {"heading": "Q3", "revenue": "$1.2M", "customers": "8,400"}
    result = runner.invoke(
        cli,
        ["slide", "add", str(deck), "--template", "kpi-duo",
         "--data-json", json.dumps(data), "--json"],
    )
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["data"]["template_id"] == "kpi-duo"

    got = json.loads(
        runner.invoke(cli, ["doc", "get", str(deck), "--index", "0", "--json"]).output
    )
    assert got["data"]["template_id"] == "kpi-duo"
    assert got["data"]["data"] == data
