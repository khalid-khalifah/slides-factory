"""Edge cases for document orchestration using core test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from slides_factory import document
from slides_factory.frame import get_frame
from slides_factory.template import get_template


def test_strict_template_rejects_invalid_nested_props(app):
    template = get_template(app, "strict")
    with pytest.raises(ValidationError):
        template.validate_data({"headline": {"block": {"children": [{"runs": [{"text": 123}]}]}}})


def test_simple_template_round_trip(tmp_path: Path, app):
    output = tmp_path / "roundtrip.pptx"
    data = {
        "headline": {"block": {"children": [{"runs": [{"text": "Hello"}]}]}},
        "body": {"block": {"children": [{"runs": [{"text": "World"}]}]}},
    }
    prs = document.create_document(output)
    document.add_slide(prs, "simple", data, app=app)
    document.save_document(prs, output)

    prs = document.open_document(output)
    info = document.get_slide_info(prs, 0, app=app)
    assert info["template_id"] == "simple"
    assert info["data"]["headline"] == {"block": {"children": [{"runs": [{"text": "Hello"}]}]}}
    assert info["data"]["body"] == {"block": {"children": [{"runs": [{"text": "World"}]}]}}


def test_add_slide_with_frame_requires_brand(tmp_path: Path, app):
    output = tmp_path / "plain.pptx"
    document.create_document(output)
    prs = document.open_document(output)
    with pytest.raises(ValueError, match="--frame"):
        document.add_slide(prs, "simple", {"headline": {"block": {"children": [{"runs": [{"text": "X"}]}]}}}, app=app, frame="plain")


def test_add_slide_applies_frame_when_branded(tmp_path: Path, minimal_brand_yaml: Path, app):
    output = tmp_path / "framed.pptx"
    document.create_document(output, brand=minimal_brand_yaml)
    prs = document.open_document(output)
    document.add_slide(prs, "simple", {"headline": {"block": {"children": [{"runs": [{"text": "Framed"}]}]}}}, app=app, frame="plain")
    document.save_document(prs, output)

    prs = document.open_document(output)
    info = document.get_slide_info(prs, 0, app=app)
    assert info["frame_id"] == "plain"


def test_add_slide_uses_brand_default_frame(tmp_path: Path, minimal_brand_yaml: Path, app):
    output = tmp_path / "default.pptx"
    document.create_document(output, brand=minimal_brand_yaml)
    prs = document.open_document(output)
    document.add_slide(prs, "simple", {"headline": {"block": {"children": [{"runs": [{"text": "T"}]}]}}}, app=app)
    document.save_document(prs, output)

    prs = document.open_document(output)
    info = document.get_slide_info(prs, 0, app=app)
    assert info["frame_id"] == "plain"


def test_add_slide_uses_template_default_frame(tmp_path: Path, minimal_brand_yaml: Path, app):
    brand_path = minimal_brand_yaml.parent / "alt_brand.yaml"
    brand_path.write_text(
        minimal_brand_yaml.read_text(encoding="utf-8").replace(
            "default_frame: plain", "default_frame: alt"
        ),
        encoding="utf-8",
    )
    output = tmp_path / "template_default.pptx"
    document.create_document(output, brand=brand_path)
    prs = document.open_document(output)
    document.add_slide(prs, "paired", {"title": "T", "headline": {"block": {"children": [{"runs": [{"text": "T"}]}]}}}, app=app)
    document.save_document(prs, output)

    prs = document.open_document(output)
    info = document.get_slide_info(prs, 0, app=app)
    assert info["frame_id"] == "plain"


def test_edit_slide_preserves_stored_frame(tmp_path: Path, minimal_brand_yaml: Path, app):
    output = tmp_path / "stored.pptx"
    document.create_document(output, brand=minimal_brand_yaml)
    prs = document.open_document(output)
    document.add_slide(prs, "simple", {"headline": {"block": {"children": [{"runs": [{"text": "One"}]}]}}}, app=app, frame="alt")
    document.edit_slide(prs, 0, {"headline": {"block": {"children": [{"runs": [{"text": "Two"}]}]}}}, app=app)
    document.save_document(prs, output)

    prs = document.open_document(output)
    info = document.get_slide_info(prs, 0, app=app)
    assert info["frame_id"] == "alt"


def test_edit_slide_template_change_uses_new_template_default(
    tmp_path: Path, minimal_brand_yaml: Path, app
):
    output = tmp_path / "change_template.pptx"
    document.create_document(output, brand=minimal_brand_yaml)
    prs = document.open_document(output)
    document.add_slide(prs, "simple", {"headline": {"block": {"children": [{"runs": [{"text": "One"}]}]}}}, app=app, frame="alt")
    document.edit_slide(
        prs, 0, {"title": "Paired", "headline": {"block": {"children": [{"runs": [{"text": "Paired"}]}]}}}, app=app, template_id="paired"
    )
    document.save_document(prs, output)

    prs = document.open_document(output)
    info = document.get_slide_info(prs, 0, app=app)
    assert info["template_id"] == "paired"
    assert info["frame_id"] == "plain"


def test_get_frame_unknown_raises(app):
    with pytest.raises(KeyError, match="Unknown frame"):
        get_frame(app, "not-a-frame")


def test_remove_slide_out_of_range(tmp_path: Path, app):
    output = tmp_path / "deck.pptx"
    document.create_document(output)
    prs = document.open_document(output)
    document.add_slide(prs, "simple", {"headline": {"block": {"children": [{"runs": [{"text": "One"}]}]}}}, app=app)
    with pytest.raises(IndexError):
        document.remove_slide(prs, 5)


def test_edit_slide_requires_template_metadata(tmp_path: Path, app):
    output = tmp_path / "deck.pptx"
    document.create_document(output)
    prs = document.open_document(output)
    document.add_slide(prs, "simple", {"headline": {"block": {"children": [{"runs": [{"text": "One"}]}]}}}, app=app)
    slide = prs.slides[0]
    if slide.has_notes_slide:
        slide.notes_slide.notes_text_frame.text = ""
    with pytest.raises(ValueError, match="no template metadata"):
        document.edit_slide(prs, 0, {"headline": {"block": {"children": [{"runs": [{"text": "Two"}]}]}}}, app=app)


def test_add_slide_locks_frame_shapes_when_enabled(tmp_path: Path, minimal_brand_yaml: Path, app):
    import zipfile

    from lxml import etree

    brand_path = minimal_brand_yaml.parent / "locked_brand.yaml"
    brand_path.write_text(
        minimal_brand_yaml.read_text(encoding="utf-8") + "\nlock_frame_shapes: true\n",
        encoding="utf-8",
    )
    output = tmp_path / "locked.pptx"
    document.create_document(output, brand=brand_path)
    prs = document.open_document(output)
    document.add_slide(prs, "simple", {"headline": {"block": {"children": [{"runs": [{"text": "Locked"}]}]}}}, app=app, frame="chrome")
    document.save_document(prs, output)

    with zipfile.ZipFile(output) as zf:
        slide = etree.fromstring(zf.read("ppt/slides/slide1.xml"))
    sp_locks = slide.xpath(
        "//a:spLocks",
        namespaces={"a": "http://schemas.openxmlformats.org/drawingml/2006/main"},
    )
    assert any(lock.get("noMove") == "1" and lock.get("noResize") == "1" for lock in sp_locks)
