"""Tests for built-in elements rendering into a slide."""

from __future__ import annotations

import pytest
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from slides_factory.elements.card import CardProps, render_card
from slides_factory.elements.image import ImageProps, ImageStyle, render_image
from slides_factory.elements.text_element import TextProps, render_text
from slides_factory.palette import SlidePalette
from slides_factory.render_context import RenderContext
from slides_factory.styling.models import CardStyle, TextStyle


@pytest.fixture
def blank_slide():
    prs = Presentation()
    layout = next((lo for lo in prs.slide_layouts if lo.name == "Blank"), prs.slide_layouts[6])
    return prs.slides.add_slide(layout), prs


def _ctx(prs, **kwargs):
    return RenderContext(
        slide_width=int(prs.slide_width), slide_height=int(prs.slide_height), **kwargs
    )


def test_text_element_renders_text_and_bullets(blank_slide):
    slide, prs = blank_slide
    from slides_factory.elements.text import ListItem, ListStyle, Paragraph, TextBlock, TextRun

    render_text(
        slide,
        (914400, 914400, 3000000, 1500000),
        TextProps(
            block=TextBlock(
                children=[
                    Paragraph(runs=[TextRun(text="Heading")]),
                    ListItem(
                        runs=[TextRun(text="one")],
                        marker=ListStyle(type="disc", level=0),
                    ),
                    ListItem(
                        runs=[TextRun(text="two")],
                        marker=ListStyle(type="disc", level=0),
                    ),
                ]
            )
        ),
        TextStyle(),
        _ctx(prs),
    )
    boxes = [s for s in slide.shapes if s.has_text_frame]
    assert boxes, "expected a text box"
    paragraphs = [p.text for p in boxes[0].text_frame.paragraphs]
    assert paragraphs[0] == "Heading"
    assert paragraphs[1] == "• one"
    assert paragraphs[2] == "• two"


def test_text_element_applies_palette_color(blank_slide):
    slide, prs = blank_slide
    from slides_factory.elements.text import text

    palette = SlidePalette(text="#123456", highlight="#000000", main=("#FFFFFF",), extras=())
    render_text(
        slide,
        (0, 0, 2000000, 1000000),
        TextProps(block=text("Hi")),
        TextStyle(),
        _ctx(prs, palette=palette),
    )
    box = next(s for s in slide.shapes if s.has_text_frame)
    run = box.text_frame.paragraphs[0].runs[0]
    assert str(run.font.color.rgb) == "123456"
    assert run.font.bold is None or run.font.bold is False


def test_text_element_honors_style_overrides(blank_slide):
    slide, prs = blank_slide
    from slides_factory.elements.text import text

    render_text(
        slide,
        (0, 0, 2000000, 1000000),
        TextProps(block=text("Bold")),
        TextStyle(text_size="2xl", bold=True),
        _ctx(prs),
    )
    box = next(s for s in slide.shapes if s.has_text_frame)
    run = box.text_frame.paragraphs[0].runs[0]
    assert run.font.bold is True
    assert int(run.font.size) == 32 * 12700


def test_card_element_draws_filled_shape_with_text(blank_slide):
    slide, prs = blank_slide
    palette = SlidePalette(text="#111111", highlight="#222222", main=("#EEEEEE",), extras=())
    render_card(
        slide,
        (1000000, 1000000, 3000000, 2000000),
        CardProps(title="Revenue", value="$1.2M"),
        CardStyle(),
        _ctx(prs, palette=palette),
    )
    shapes = [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE]
    assert shapes, "expected a card auto shape"
    card = shapes[0]
    assert str(card.fill.fore_color.rgb) == "EEEEEE"
    texts = [p.text for p in card.text_frame.paragraphs]
    assert "Revenue" in texts
    assert "$1.2M" in texts


def test_card_element_without_palette_uses_fallback_color(blank_slide):
    slide, prs = blank_slide
    render_card(
        slide,
        (0, 0, 2000000, 1000000),
        CardProps(value="42"),
        CardStyle(),
        _ctx(prs),
    )
    card = next(s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE)
    assert str(card.fill.fore_color.rgb) == "F3F4F6"


# --- Image element tests ---


@pytest.fixture
def image_path():
    import pathlib

    return (pathlib.Path(__file__).resolve().parent / "fixtures" / "test_image.png")


@pytest.fixture
def portrait_path():
    import pathlib

    return (pathlib.Path(__file__).resolve().parent / "fixtures" / "test_image_portrait.png")


def test_image_contain(blank_slide, image_path):
    """Landscape image in a square cell with contain mode — no distortion, centered."""
    slide, prs = blank_slide
    render_image(
        slide,
        (0, 0, 1000000, 1000000),  # square cell
        ImageProps(src=str(image_path), fit="contain"),
        ImageStyle(),
        _ctx(prs),
    )
    pics = [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert len(pics) == 1
    pic = pics[0]
    # For 200x150 in 1Mx1M: box_aspect=1, img_aspect=1.33 -> wider, fit to width
    # So width=1M, height=1M*(150/200)=750K, centered vertically
    assert pic.width <= 1000000
    assert pic.height <= 1000000
    # Aspect ratio preserved
    ratio = pic.width / pic.height
    assert abs(ratio - 200 / 150) < 0.01
    # Positioned (centered)
    assert pic.left >= 0
    assert pic.top > 0  # should be vertically centered, so top > 0


def test_image_cover(blank_slide, portrait_path):
    """Portrait image in a landscape cell with cover mode — crops applied."""
    slide, prs = blank_slide
    render_image(
        slide,
        (0, 0, 1000000, 500000),  # wide cell
        ImageProps(src=str(portrait_path), fit="cover"),
        ImageStyle(),
        _ctx(prs),
    )
    pics = [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert len(pics) == 1
    pic = pics[0]
    # Cover draws the picture larger than the box and applies crops.
    # For 100x150 portrait in 1000000x500000 cell:
    # img_aspect=0.667 < box_aspect=2.0, so fit to width:
    # draw_w=1000000, draw_h=1500000, crop_t=crop_b=~0.333
    assert pic.width == 1000000
    assert pic.height > 500000  # larger than box, cropped to fit
    assert pic.crop_left == 0.0
    assert pic.crop_top > 0.0  # cropped
    assert pic.crop_right == 0.0
    assert pic.crop_bottom > 0.0  # cropped


def test_image_stretch(blank_slide, image_path):
    """Stretch mode fills box exactly, non-uniform scaling."""
    slide, prs = blank_slide
    render_image(
        slide,
        (0, 0, 1000000, 800000),
        ImageProps(src=str(image_path), fit="stretch"),
        ImageStyle(),
        _ctx(prs),
    )
    pics = [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert len(pics) == 1
    pic = pics[0]
    assert pic.width == 1000000
    assert pic.height == 800000
    # No crops for stretch
    assert pic.crop_left == 0.0
    assert pic.crop_top == 0.0
    assert pic.crop_right == 0.0
    assert pic.crop_bottom == 0.0


def test_image_alt_text(blank_slide, image_path):
    """Alt text is set on the picture via cNvPr descr attribute."""
    slide, prs = blank_slide
    render_image(
        slide,
        (0, 0, 500000, 500000),
        ImageProps(src=str(image_path), alt="A test chart"),
        ImageStyle(),
        _ctx(prs),
    )
    pics = [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert len(pics) == 1
    pic = pics[0]
    from lxml import etree

    ns_p = "http://schemas.openxmlformats.org/presentationml/2006/main"
    nv_pic_pr = pic._element.find(f"{{{ns_p}}}nvPicPr")
    assert nv_pic_pr is not None
    c_nv_pr = nv_pic_pr.find(f"{{{ns_p}}}cNvPr")
    assert c_nv_pr is not None
    assert c_nv_pr.get("descr") == "A test chart"


def test_image_missing_file(blank_slide):
    """Missing file raises FileNotFoundError with a clear message."""
    slide, prs = blank_slide

    with pytest.raises(FileNotFoundError, match="nonexistent.png"):
        render_image(
            slide,
            (0, 0, 500000, 500000),
            ImageProps(src="nonexistent.png"),
            ImageStyle(),
            _ctx(prs),
        )


def test_image_radius(blank_slide, image_path):
    """Non-none radius modifies picture XML to use roundRect preset geometry."""
    slide, prs = blank_slide
    render_image(
        slide,
        (0, 0, 1000000, 1000000),
        ImageProps(src=str(image_path), fit="stretch"),
        ImageStyle(radius="md"),
        _ctx(prs),
    )
    pics = [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert len(pics) == 1
    pic = pics[0]
    from lxml import etree

    ns_p = "http://schemas.openxmlformats.org/presentationml/2006/main"
    ns_a = "http://schemas.openxmlformats.org/drawingml/2006/main"
    sp_pr = pic._element.find(f"{{{ns_p}}}spPr")
    assert sp_pr is not None
    prst_geom = sp_pr.find(f"{{{ns_a}}}prstGeom")
    assert prst_geom is not None
    # Verify the preset was changed to roundRect
    assert prst_geom.get("prst") == "roundRect"
    # Verify an adjustment was added
    av_lst = prst_geom.find(f"{{{ns_a}}}avLst")
    assert av_lst is not None
    gd = av_lst.find(f"{{{ns_a}}}gd")
    assert gd is not None
    assert gd.get("name") == "adj"


def test_image_opacity(blank_slide, image_path):
    """Opacity < 1.0 sets an alpha modifier on the picture's blip."""
    slide, prs = blank_slide
    render_image(
        slide,
        (0, 0, 500000, 500000),
        ImageProps(src=str(image_path)),
        ImageStyle(opacity=0.5),
        _ctx(prs),
    )
    pics = [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert len(pics) == 1
    pic = pics[0]
    from lxml import etree

    ns_a = "http://schemas.openxmlformats.org/drawingml/2006/main"
    blip = pic._element.find(f".//{{{ns_a}}}blip")
    assert blip is not None
    alpha = blip.find(f"{{{ns_a}}}alpha")
    assert alpha is not None
    # 0.5 * 100000 = 50000
    assert alpha.get("val") == "50000"


def test_image_svg_source(blank_slide, tmp_path):
    """SVG input — verify it rasterizes to PNG and renders as picture."""
    import shutil

    rsvg = shutil.which("rsvg-convert")
    if not rsvg:
        pytest.skip("rsvg-convert not installed — cannot test SVG rasterization")

    svg_file = tmp_path / "test.svg"
    svg_file.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50">'
        '<rect width="100" height="50" fill="blue"/></svg>'
    )
    slide, prs = blank_slide
    render_image(
        slide,
        (0, 0, 500000, 500000),
        ImageProps(src=str(svg_file)),
        ImageStyle(),
        _ctx(prs),
    )
    # Should produce a picture shape
    pics = [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert len(pics) == 1


def test_image_cli(image_path):
    """Verify image element is registered and can be instantiated via API."""
    from slides_factory.app import SlideFactory

    app = SlideFactory("test-image-cli", package="tests")
    el = app.get_element("image")
    assert el.kind == "image"
    props = el.validate_props({"src": str(image_path)})
    assert props.src == str(image_path)
    assert props.fit == "contain"
    assert props.alt == ""
    style = el.validate_style({"radius": "lg", "opacity": 0.8})
    assert style.radius == "lg"
    assert style.opacity == 0.8


# --- Rich text integration tests ---


def test_rich_text_basic(blank_slide):
    """parse_html → render_text produces correct bold and italic runs."""
    from slides_factory.elements.text import parse_html

    slide, prs = blank_slide
    render_text(
        slide,
        (0, 0, 3000000, 1000000),
        TextProps(block=parse_html("<b>Bold</b> and <i>italic</i>")),
        TextStyle(),
        _ctx(prs),
    )
    box = next(s for s in slide.shapes if s.has_text_frame)
    paras = list(box.text_frame.paragraphs)
    assert len(paras) >= 1
    runs = list(paras[0].runs)
    assert len(runs) >= 3
    assert runs[0].text == "Bold"
    assert runs[0].font.bold is True
    assert runs[2].text == "italic"
    assert runs[2].font.italic is True


def test_rich_text_colors(blank_slide):
    """parse_html with color attribute resolves against palette."""
    from slides_factory.elements.text import parse_html

    slide, prs = blank_slide
    palette = SlidePalette(text="#111111", highlight="#EAA000", main=("#FFFFFF",), extras=())
    render_text(
        slide,
        (0, 0, 3000000, 1000000),
        TextProps(block=parse_html('<span color="highlight">Highlighted</span>')),
        TextStyle(),
        _ctx(prs, palette=palette),
    )
    box = next(s for s in slide.shapes if s.has_text_frame)
    run = box.text_frame.paragraphs[0].runs[0]
    assert str(run.font.color.rgb) == "EAA000"


def test_rich_text_hyperlink(blank_slide):
    """parse_html with <a> creates clickable hyperlink."""
    from slides_factory.elements.text import parse_html

    slide, prs = blank_slide
    render_text(
        slide,
        (0, 0, 3000000, 1000000),
        TextProps(block=parse_html('<a href="https://example.com">Click</a>')),
        TextStyle(),
        _ctx(prs),
    )
    box = next(s for s in slide.shapes if s.has_text_frame)
    run = box.text_frame.paragraphs[0].runs[0]
    assert run.text == "Click"
    assert run.hyperlink.address == "https://example.com"


def test_rich_text_backward_compat(blank_slide):
    """text() DSL still works alongside parse_html."""
    from slides_factory.elements.text import text

    slide, prs = blank_slide
    render_text(
        slide,
        (0, 0, 3000000, 1000000),
        TextProps(block=text("Plain text works")),
        TextStyle(),
        _ctx(prs),
    )
    box = next(s for s in slide.shapes if s.has_text_frame)
    assert box.text_frame.paragraphs[0].runs[0].text == "Plain text works"


def test_rich_text_multi_run_paragraph(blank_slide):
    """Multiple formatted runs in one paragraph from parse_html."""
    from slides_factory.elements.text import parse_html

    slide, prs = blank_slide
    render_text(
        slide,
        (0, 0, 4000000, 1000000),
        TextProps(block=parse_html("Normal <b>bold</b> <i>italic</i> <u>underlined</u>")),
        TextStyle(),
        _ctx(prs),
    )
    box = next(s for s in slide.shapes if s.has_text_frame)
    runs = list(box.text_frame.paragraphs[0].runs)
    assert len(runs) == 6
    assert runs[0].text == "Normal "
    assert runs[1].text == "bold"
    assert runs[1].font.bold is True
    assert runs[2].text == " "
    assert runs[3].text == "italic"
    assert runs[3].font.italic is True
    assert runs[4].text == " "
    assert runs[5].text == "underlined"
    assert runs[5].font.underline is True
