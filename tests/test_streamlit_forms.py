"""Tests for TemplateInput form helpers (no Streamlit runtime)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from slides_factory.preview.forms import (
    default_form_values,
    validate_form_values,
)
from tests.fixtures.template_inputs import BlankShapesInput, BulletsInput


def test_default_form_values_scalar_and_lists():
    defaults = default_form_values(BulletsInput)
    assert defaults["title"] == ""
    assert defaults["bullets"] == []
    assert defaults["levels"] is None


def test_validate_form_values_accepts_list_fields():
    validated = validate_form_values(
        BulletsInput,
        {
            "title": "Highlights",
            "bullets": ["One", "Two"],
            "levels": [0, 1],
        },
    )
    assert validated.title == "Highlights"
    assert validated.bullets == ["One", "Two"]
    assert validated.levels == [0, 1]


def test_validate_form_values_nested_models():
    validated = validate_form_values(
        BlankShapesInput,
        {
            "heading": "Overview",
            "boxes": [{"label": "A", "color": "#FF0000"}],
        },
    )
    assert validated.heading == "Overview"
    assert validated.boxes[0].label == "A"


def test_validate_form_values_rejects_missing_required():
    with pytest.raises(ValidationError):
        validate_form_values(BulletsInput, {"bullets": ["only bullets"]})
