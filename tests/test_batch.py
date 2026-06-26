"""Tests for data-driven slide generation (add_slides_from_rows)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from slides_factory import document
from slides_factory.app import SlideFactory
from slides_factory.exceptions import SlidesFactoryError

# --- Python API tests --------------------------------------------------------


def _make_app() -> SlideFactory:
    """Return a SlideFactory with the core templates loaded."""
    from tests.fixtures.app import app

    return app


def _make_deck(tmp_path: Path) -> Path:
    output = tmp_path / "test.pptx"
    document.create_document(output)
    return output


def test_add_slides_from_rows_creates_correct_count(tmp_path: Path):
    """3 rows → 3 slides."""
    app = _make_app()
    deck = _make_deck(tmp_path)
    prs = document.open_document(deck)
    rows = [
        {"headline": {"block": {"children": [{"runs": [{"text": "Q1"}]}]}}},
        {"headline": {"block": {"children": [{"runs": [{"text": "Q2"}]}]}}},
        {"headline": {"block": {"children": [{"runs": [{"text": "Q3"}]}]}}},
    ]
    results = document.add_slides_from_rows(prs, "simple", rows, app=app)
    document.save_document(prs, deck)

    assert len(results) == 3
    for i, r in enumerate(results):
        assert r["template_id"] == "simple"
        assert r["slide_index"] == i


def test_add_slides_from_rows_validates_each_row(tmp_path: Path):
    """Invalid row raises ValidationError when skip_invalid=False."""
    app = _make_app()
    deck = _make_deck(tmp_path)
    prs = document.open_document(deck)
    # Pass a string instead of a dict for a cell prop — type mismatch.
    rows = [
        {"headline": {"block": {"children": [{"runs": [{"text": "Valid"}]}]}}},
        {"headline": "not-a-dict"},  # wrong type — should fail validation
        {"headline": {"block": {"children": [{"runs": [{"text": "Also valid"}]}]}}},
    ]
    with pytest.raises((ValidationError, SlidesFactoryError, ValueError, TypeError)):
        document.add_slides_from_rows(prs, "simple", rows, app=app, skip_invalid=False)


def test_add_slides_from_rows_skip_invalid(tmp_path: Path):
    """skip_invalid=True skips bad rows and includes errors."""
    app = _make_app()
    deck = _make_deck(tmp_path)
    prs = document.open_document(deck)
    rows = [
        {"headline": {"block": {"children": [{"runs": [{"text": "Valid"}]}]}}},
        {"headline": "not-a-dict"},  # wrong type — triggers validation error
        {"headline": {"block": {"children": [{"runs": [{"text": "Also valid"}]}]}}},
    ]
    results = document.add_slides_from_rows(
        prs, "simple", rows, app=app, skip_invalid=True
    )
    document.save_document(prs, deck)

    assert len(results) == 3
    assert "slide_index" in results[0]  # valid slide has index
    assert results[1]["ok"] is False  # skipped
    assert "error" in results[1]
    assert "slide_index" in results[2]  # valid slide has index
    assert results[0]["slide_index"] == 0
    assert results[2]["slide_index"] == 1


def test_add_slides_from_rows_empty_list(tmp_path: Path):
    """Empty rows list → no slides, no error."""
    app = _make_app()
    deck = _make_deck(tmp_path)
    prs = document.open_document(deck)
    results = document.add_slides_from_rows(prs, "simple", [], app=app)
    assert results == []


# --- CLI tests ---------------------------------------------------------------


@pytest.fixture
def cli_app() -> SlideFactory:
    from tests.fixtures.app import app

    return app


def test_add_many_cli_with_rows_json(tmp_path: Path, cli_app):
    """CLI slide add-many with --rows creates slides."""
    deck = _make_deck(tmp_path)
    runner = CliRunner()
    rows = [
        {"headline": {"block": {"children": [{"runs": [{"text": "Q1"}]}]}}},
        {"headline": {"block": {"children": [{"runs": [{"text": "Q2"}]}]}}},
    ]
    result = runner.invoke(
        cli_app.cli,
        [
            "slide",
            "add-many",
            str(deck),
            "--template",
            "simple",
            "--rows",
            json.dumps(rows),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["data"]["count"] == 2


def test_add_many_cli_with_rows_file(tmp_path: Path, cli_app):
    """CLI slide add-many with --rows-file reads from JSON file."""
    deck = _make_deck(tmp_path)
    rows = [
        {"headline": {"block": {"children": [{"runs": [{"text": "A"}]}]}}},
        {"headline": {"block": {"children": [{"runs": [{"text": "B"}]}]}}},
    ]
    rows_path = tmp_path / "data.json"
    rows_path.write_text(json.dumps(rows), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli_app.cli,
        [
            "slide",
            "add-many",
            str(deck),
            "--template",
            "simple",
            "--rows-file",
            str(rows_path),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["data"]["count"] == 2


def test_add_many_cli_with_batch_yaml(tmp_path: Path, cli_app):
    """CLI slide add-many with --batch reads from YAML file."""
    deck = _make_deck(tmp_path)

    import yaml

    batch = {
        "template": "simple",
        "rows": [
            {"headline": {"block": {"children": [{"runs": [{"text": "Y1"}]}]}}},
            {"headline": {"block": {"children": [{"runs": [{"text": "Y2"}]}]}}},
        ],
    }
    batch_path = tmp_path / "batch.yaml"
    with open(batch_path, "w", encoding="utf-8") as f:
        yaml.dump(batch, f)

    runner = CliRunner()
    result = runner.invoke(
        cli_app.cli,
        [
            "slide",
            "add-many",
            str(deck),
            "--batch",
            str(batch_path),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["data"]["count"] == 2


def test_add_many_cli_no_data_source(tmp_path: Path, cli_app):
    """Missing --rows, --rows-file, and --batch reports an error."""
    deck = _make_deck(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli_app.cli,
        [
            "slide",
            "add-many",
            str(deck),
            "--template",
            "simple",
            "--json",
        ],
    )
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["ok"] is False
    assert "Provide one of" in data["error"]
