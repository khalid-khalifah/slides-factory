"""Tree model — the building blocks of rich-text content."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TextRun(BaseModel):
    """One formatted inline segment within a paragraph.

    Maps roughly to a ``<span>`` with inline style attributes.  Every property
    is optional — when left at its default the paragraph-level or element-level
    ``TextStyle`` value is used instead.
    """

    model_config = {"exclude_none": True}

    text: str
    bold: bool | None = None
    italic: bool | None = None
    color: str | None = Field(
        default=None,
        description="Palette token, hex #RRGGBB, or brand fill reference.",
    )
    size_pt: float | None = Field(
        default=None,
        description="Override element-level text_size for this run (points).",
    )
    link: str | None = Field(
        default=None,
        description="Hyperlink URL. When set the run becomes clickable.",
    )
    strikethrough: bool | None = None
    underline: bool | None = None


class ListStyle(BaseModel):
    """Visual style of a list-item marker (bullet or number)."""

    model_config = {"exclude_none": True}

    type: Literal["disc", "circle", "square", "decimal", "hyphen", "none"] = Field(
        default="disc",
        description="Marker shape: disc •, circle ○, square ■, decimal 1., hyphen –, none.",
    )
    level: int = Field(default=0, ge=0, description="Nesting / indent level.")


class Paragraph(BaseModel):
    """A text paragraph — one or more inline runs flowing as a single line.

    Analogous to ``<p>``.  When runs is empty the paragraph renders as an
    empty line (spacer).
    """

    model_config = {"exclude_none": True}

    runs: list[TextRun]


class ListItem(BaseModel):
    """A bullet or numbered list item.

    Analogous to ``<li>``.  Contains inline runs plus marker metadata.
    """

    model_config = {"exclude_none": True}

    runs: list[TextRun]
    marker: ListStyle = ListStyle()


class TextBlock(BaseModel):
    """A rich-text document — ordered sequence of block-level nodes.

    ``children`` may contain ``Paragraph`` and ``ListItem`` nodes.  A flat
    list is preferred for pptx (nested sub-lists can be added later without
    breaking the API).

    The optional default-style fields (``font_size``, ``color``, ``bold``,
    ``align``, ``font_family``) act as fallback defaults for the whole block.
    When set they are used by ``render_text_block`` unless overridden by
    explicit function parameters.  The ``<div>`` tag in ``parse_html``
    populates these fields.
    """

    model_config = {"exclude_none": True}

    children: list[Paragraph | ListItem]

    font_size: float | None = Field(
        default=None,
        description="Default point size for the whole block.",
    )
    font_family: str | None = Field(
        default=None,
        description="Default font family for the whole block.",
    )
    color: str | None = Field(
        default=None,
        description="Default palette colour token or hex.",
    )
    bold: bool | None = Field(
        default=None,
        description="Default bold state for the whole block.",
    )
    align: str | None = Field(
        default=None,
        description="Default paragraph alignment (\"left\", \"center\", \"right\", \"justify\").",
    )
