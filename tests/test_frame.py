"""Edge cases for frame resolution helpers."""

from slides_factory.frame import resolve_frame_id


def test_resolve_frame_id_prefers_cli_override():
    assert resolve_frame_id(frame="custom", brand_default="basic") == "custom"


def test_resolve_frame_id_uses_stored_before_template_default():
    assert (
        resolve_frame_id(
            frame=None,
            stored="stored-frame",
            template_default="template-frame",
            brand_default="brand-frame",
        )
        == "stored-frame"
    )


def test_resolve_frame_id_uses_template_default_before_brand():
    assert (
        resolve_frame_id(
            frame=None,
            template_default="template-frame",
            brand_default="brand-frame",
        )
        == "template-frame"
    )


def test_resolve_frame_id_uses_brand_default():
    assert resolve_frame_id(frame=None, brand_default="brand-frame") == "brand-frame"


def test_resolve_frame_id_falls_back_when_unset():
    assert resolve_frame_id(frame=None, brand_default=None) == "basic"
    assert resolve_frame_id(frame=None, brand_default=None, fallback="plain") == "plain"
