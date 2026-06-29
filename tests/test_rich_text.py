"""Tests for the HTML-like rich text parser (parse_html)."""

from __future__ import annotations

from slides_factory.converters.text import (
    ListItem,
    Paragraph,
    TextBlock,
    TextRun,
    parse_html,
)


def test_plain_text():
    """Plain text with no tags produces one paragraph, one run."""
    block = parse_html("Hello world")
    assert len(block.children) == 1
    child = block.children[0]
    assert isinstance(child, Paragraph)
    assert len(child.runs) == 1
    assert child.runs[0].text == "Hello world"
    assert child.runs[0].bold is None


def test_bold_tag():
    """<b> tags create bold runs."""
    block = parse_html("Hi <b>there</b>!")
    assert len(block.children) == 1
    runs = block.children[0].runs
    assert len(runs) == 3
    assert runs[0].text == "Hi "
    assert runs[0].bold is None
    assert runs[1].text == "there"
    assert runs[1].bold is True
    assert runs[2].text == "!"


def test_italic_tag():
    """<i> tags create italic runs."""
    block = parse_html("<i>italic</i> text")
    assert block.children[0].runs[0].italic is True
    assert block.children[0].runs[0].text == "italic"


def test_underline_tag():
    """<u> tags create underlined runs."""
    block = parse_html("under<u>line</u>")
    assert block.children[0].runs[1].underline is True


def test_strikethrough_tag():
    """<s> tags create strikethrough runs."""
    block = parse_html("<s>strike</s>")
    assert block.children[0].runs[0].strikethrough is True


def test_span_with_attributes():
    """<span> with color and bold creates appropriately styled runs."""
    block = parse_html('Text <span color="accent" bold>styled</span> end')
    runs = block.children[0].runs
    assert len(runs) == 3
    assert runs[1].color == "accent"
    assert runs[1].bold is True


def test_span_boolean_attribute():
    """Presence of a boolean attribute sets it to True."""
    block = parse_html('<span bold>Bold text</span>')
    assert block.children[0].runs[0].bold is True


def test_link_tag():
    """<a href> creates a run with a hyperlink."""
    block = parse_html('Click <a href="https://example.com">here</a>')
    runs = block.children[0].runs
    assert runs[1].link == "https://example.com"
    assert runs[1].text == "here"


def test_multi_paragraph():
    """Double newline separates paragraphs."""
    block = parse_html("First para.\n\nSecond <b>para</b>.")
    assert len(block.children) == 2
    assert isinstance(block.children[0], Paragraph)
    assert isinstance(block.children[1], Paragraph)
    assert block.children[1].runs[1].bold is True


def test_nested_tags():
    """Nested tags inherit parent styles."""
    block = parse_html('<span color="red">Red <b>and bold</b></span>')
    runs = block.children[0].runs
    assert runs[1].color == "red"
    assert runs[1].bold is True


def test_html_entities():
    """HTML entities are decoded."""
    block = parse_html("A &lt; B &gt; C &amp; D")
    assert block.children[0].runs[0].text == "A < B > C & D"


def test_empty_string():
    """Empty string produces no children."""
    block = parse_html("")
    assert len(block.children) == 0


def test_only_tags():
    """Only tags with no text produce no paragraph."""
    block = parse_html("<b></b>")
    assert len(block.children) == 0


# --- List tests ---


def test_unordered_list():
    """<ul> with <li> items creates ListItem nodes with disc marker."""
    block = parse_html("<ul><li>A</li><li>B</li></ul>")
    assert len(block.children) == 2
    for child in block.children:
        assert isinstance(child, ListItem)
        assert child.marker.type == "disc"


def test_ordered_list():
    """<ol> with <li> items creates ListItem nodes with decimal marker."""
    block = parse_html("<ol><li>First</li><li>Second</li></ol>")
    assert len(block.children) == 2
    for child in block.children:
        assert isinstance(child, ListItem)
        assert child.marker.type == "decimal"


def test_list_with_inline_formatting():
    """Inline tags like <b> work inside <li>."""
    block = parse_html("<ul><li><b>Bold</b> item</li></ul>")
    assert len(block.children) == 1
    child = block.children[0]
    assert isinstance(child, ListItem)
    assert len(child.runs) == 2
    assert child.runs[0].bold is True
    assert child.runs[0].text == "Bold"
    assert child.runs[1].text == " item"


# ---------------------------------------------------------------------------
# <div> wrapper — block-level defaults
# ---------------------------------------------------------------------------


def test_div_sets_font_size():
    """<div font-size="14"> sets block.font_size as a float."""
    block = parse_html('<div font-size="14">Large text</div>')
    assert block.font_size == 14.0
    assert len(block.children) == 1


def test_div_sets_color():
    """<div color="muted"> sets block.color."""
    block = parse_html('<div color="muted">Muted text</div>')
    assert block.color == "muted"


def test_div_sets_align():
    """<div align="center"> sets block.align."""
    block = parse_html('<div align="center">Centered</div>')
    assert block.align == "center"


def test_div_sets_bold():
    """<div bold="true"> sets block.bold."""
    block = parse_html('<div bold="true">All bold</div>')
    assert block.bold is True


def test_div_inline_tags_inside():
    """<div> still supports child <b> and <i> tags."""
    block = parse_html('<div color="primary"><b>Bold</b> and <i>italic</i></div>')
    assert block.color == "primary"
    assert len(block.children) == 1
    para = block.children[0]
    assert isinstance(para, Paragraph)
    assert para.runs[0].bold is True
    assert para.runs[1].text == " and "
    assert para.runs[2].italic is True


def test_div_no_div_still_works():
    """Text without <div> has no block-level defaults."""
    block = parse_html("Just text")
    assert block.font_size is None
    assert block.color is None
    assert block.align is None


def test_div_with_list():
    """<div> can wrap lists too."""
    block = parse_html('<div color="secondary"><ul><li>A</li><li>B</li></ul></div>')
    assert block.color == "secondary"
    assert len(block.children) == 2
    assert isinstance(block.children[0], ListItem)


def test_list_mixed_with_paragraphs():
    """Text before and after a list block creates Paragraph nodes."""
    block = parse_html("Intro.\n\n<ul><li>Item</li></ul>\n\nOutro.")
    assert len(block.children) == 3
    assert isinstance(block.children[0], Paragraph)
    assert isinstance(block.children[1], ListItem)
    assert isinstance(block.children[2], Paragraph)
    assert block.children[0].runs[0].text == "Intro."
    assert block.children[2].runs[0].text == "Outro."


def test_empty_list():
    """Empty list block produces no children."""
    block = parse_html("<ul></ul>")
    assert len(block.children) == 0
