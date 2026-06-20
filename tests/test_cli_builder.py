"""Tests for the flag-driven incremental grid builder (document + CLI)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from slides_factory import document
from tests.fixtures.app import app as core_app

runner = CliRunner()


# --- document builder helpers ---------------------------------------------


def test_new_grid_slide_starts_empty_document_api(tmp_path: Path):
    output = tmp_path / "deck.pptx"
    prs = document.create_document(output)
    result = document.new_grid_slide(prs, grid="grid-cols-2 gap-4")
    assert result["kind"] == "grid"
    assert result["data"]["grid"] == "grid-cols-2 gap-4"
    assert result["data"]["cells"] == []


# --- CLI surface -----------------------------------------------------------


def _json(result):
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def test_cli_build_deck_round_trip(tmp_path: Path):
    cli = core_app.cli
    deck = tmp_path / "deck.pptx"

    _json(runner.invoke(cli, ["doc", "create", "-o", str(deck), "--json"]))
    _json(
        runner.invoke(
            cli, ["slide", "new", str(deck), "--grid", "grid-cols-2 gap-4", "--json"]
        )
    )
    add = _json(
        runner.invoke(
            cli,
            [
                "el", "add", str(deck), "--index", "0", "--kind", "text",
                "--set", "text=Highlights", "--json",
            ],
        )
    )
    assert add["ok"] is True
    assert add["data"]["cell_index"] == 0

    got = _json(runner.invoke(cli, ["doc", "get", str(deck), "--index", "0", "--json"]))
    cells = got["data"]["data"]["cells"]
    assert cells[0]["element"]["kind"] == "text"
    assert cells[0]["element"]["props"]["text"] == "Highlights"


def test_cli_repeated_set_builds_list(tmp_path: Path):
    cli = core_app.cli
    deck = tmp_path / "deck.pptx"
    runner.invoke(cli, ["doc", "create", "-o", str(deck)])
    runner.invoke(cli, ["slide", "new", str(deck), "--grid", "grid-cols-1"])
    runner.invoke(
        cli,
        [
            "el", "add", str(deck), "--index", "0", "--kind", "text",
            "--set", "bullets=one", "--set", "bullets=two",
        ],
    )
    got = _json(runner.invoke(cli, ["doc", "get", str(deck), "--index", "0", "--json"]))
    assert got["data"]["data"]["cells"][0]["element"]["props"]["bullets"] == ["one", "two"]


def test_cli_slide_add_uses_set_flags(tmp_path: Path):
    cli = core_app.cli
    deck = tmp_path / "deck.pptx"
    runner.invoke(cli, ["doc", "create", "-o", str(deck)])
    payload = _json(
        runner.invoke(
            cli,
            [
                "slide", "add", str(deck), "--template", "simple",
                "--set", "headline.text=Hello", "--set", "body.text=World", "--json",
            ],
        )
    )
    assert payload["data"]["template_id"] == "simple"
    assert payload["data"]["data"]["headline"] == {"text": "Hello", "bullets": []}
    assert payload["data"]["data"]["body"] == {"text": "World", "bullets": []}


def test_cli_elements_and_classes_discovery(tmp_path: Path):
    cli = core_app.cli

    listing = _json(runner.invoke(cli, ["elements", "list", "--json"]))
    kinds = {el["kind"] for el in listing["data"]["elements"]}
    assert {"text", "card"} <= kinds

    inspect = _json(runner.invoke(cli, ["elements", "inspect", "text", "--json"]))
    assert inspect["data"]["kind"] == "text"
    bullets = next(p for p in inspect["data"]["props"] if p["name"] == "bullets")
    assert bullets["list"] is True

    classes = _json(runner.invoke(cli, ["classes", "--json"]))
    assert "grid-cols-N" in classes["data"]["grid"]
    assert "spacing" in classes["data"]["scales"]


def test_cli_slide_new_uses_set_for_frame_info(tmp_path: Path):
    cli = core_app.cli
    deck = tmp_path / "deck.pptx"
    runner.invoke(cli, ["doc", "create", "-o", str(deck)])
    payload = _json(
        runner.invoke(
            cli,
            [
                "slide", "new", str(deck),
                "--grid", "grid-cols-1",
                "--set", "title=Quarterly Review",
                "--json",
            ],
        )
    )
    assert payload["data"]["data"]["frame_info"]["title"] == "Quarterly Review"


def test_cli_el_add_bad_kind_reports_error(tmp_path: Path):
    cli = core_app.cli
    deck = tmp_path / "deck.pptx"
    runner.invoke(cli, ["doc", "create", "-o", str(deck)])
    runner.invoke(cli, ["slide", "new", str(deck)])
    result = runner.invoke(
        cli, ["el", "add", str(deck), "--index", "0", "--kind", "nope", "--json"]
    )
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert "nope" in payload["error"]
