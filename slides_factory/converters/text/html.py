"""HTML-like parser — turn tagged strings into TextBlock trees."""

from __future__ import annotations

import html as html_mod
import re
from contextlib import suppress

from slides_factory.converters.text.model import ListItem, ListStyle, Paragraph, TextBlock, TextRun


def parse_html(text: str) -> TextBlock:
    """Parse an HTML-like rich-text string into a ``TextBlock``.

    Supported tags and their attribute mappings:

    ============ ==========================================================
    Tag          Effect
    ============ ==========================================================
    ``<b>``      Bold
    ``<i>``      Italic
    ``<u>``      Underline
    ``<s>``      Strikethrough
    ``<a href=``  Hyperlink URL
    ``<span``     Inline span with any of: ``color``, ``bold``, ``italic``,
                 ``underline``, ``strikethrough``, ``size``, ``href``
    ============ ==========================================================

    **Lists:**

    ============ ==========================================================
    Tag          Effect
    ============ ==========================================================
    ``<ul>``     Unordered list — each ``<li>`` becomes a ``ListItem``.
    ``<ol>``     Ordered list — each ``<li>`` becomes a ``ListItem``.
    ``<li>``     List item (inline tags work inside).
    ``</ul>``,``</ol>``  Close list container.
    ============ ==========================================================

    Examples::

        parse_html('<ul><li>A</li><li>B</li></ul>')
        parse_html('Intro.\\n\\n<ol><li><b>First</b></li><li>Second</li></ol>')
    """
    _ATTR_RE = re.compile(
        r"""(?P<key>[a-zA-Z_][a-zA-Z0-9_-]*)\s*=\s*"(?P<val>[^"]*)"|
               (?P<key2>[a-zA-Z_][a-zA-Z0-9_-]*)\s*=\s*'(?P<val2>[^']*)'|
               (?P<key3>[a-zA-Z_][a-zA-Z0-9_-]+)(?=\s|/?>|$)
        """,
        re.VERBOSE,
    )

    _TAG_MAP: dict[str, dict[str, str | bool]] = {
        "b": {"bold": True},
        "i": {"italic": True},
        "u": {"underline": True},
        "s": {"strikethrough": True},
        "a": {},
        "span": {},
    }

    def _parse_tag(tag: str) -> tuple[str, dict[str, str | bool], bool]:
        inner = tag[1:-1].strip()
        if inner.startswith("/"):
            return inner[1:].strip().lower(), {}, True
        parts = inner.split(None, 1)
        name = parts[0].lower()
        attrs: dict[str, str | bool] = {}
        if len(parts) > 1:
            for m in _ATTR_RE.finditer(parts[1]):
                key = m.group("key") or m.group("key2") or m.group("key3")
                value = m.group("val") or m.group("val2")
                if value is not None:
                    attrs[key] = html_mod.unescape(value)
                else:
                    attrs[key] = True
        return name, attrs, False

    def _current_style(stack: list[dict]) -> dict[str, str | bool]:
        style: dict[str, str | bool] = {}
        for s in stack:
            style.update(s)
        return style

    def _parse_inline(content: str) -> list[TextRun]:
        """Parse inline content (text + inline tags) into a list of TextRuns."""
        tokens = re.findall(r"<[^>]+>|[^<]+", content)
        runs: list[TextRun] = []
        style_stack: list[dict] = []

        for token in tokens:
            if token.startswith("<") and token.endswith(">"):
                name, attrs, is_closing = _parse_tag(token)
                if is_closing:
                    for i in range(len(style_stack) - 1, -1, -1):
                        if style_stack[i].get("_tag") == name:
                            style_stack.pop(i)
                            break
                elif name in _TAG_MAP:
                    merged = dict(_TAG_MAP[name])
                    merged.update(attrs)
                    merged["_tag"] = name
                    if name == "a" and "href" in merged:
                        merged["link"] = merged.pop("href")
                    style_stack.append(merged)
            else:
                decoded = html_mod.unescape(token)
                style = _current_style(style_stack)
                run_kwargs: dict = {}
                for key in ("bold", "italic", "underline", "strikethrough"):
                    if key in style:
                        run_kwargs[key] = True
                if "color" in style:
                    run_kwargs["color"] = str(style["color"])
                if "size" in style:
                    with suppress(ValueError, TypeError):
                        run_kwargs["size_pt"] = float(style["size"])
                if "link" in style:
                    run_kwargs["link"] = str(style["link"])
                runs.append(TextRun(text=decoded, **run_kwargs))

        return runs

    # ── Main parse ─────────────────────────────────────────────────────

    children: list[Paragraph | ListItem] = []

    # Extract <ul>...</ul> and <ol>...</ol> blocks as whole segments.
    # Regex matches the <ul> or <ol> tag, its content, and the closing tag.
    list_block_re = re.compile(
        r"<(ul|ol)(?:\s[^>]*)?>(.*?)</\1>", re.DOTALL
    )

    last_end = 0
    for m in list_block_re.finditer(text):
        # Emit text before this list block as paragraphs.
        before = text[last_end : m.start()]
        _emit_paragraphs(before, children, _parse_inline)

        list_type = m.group(1)  # "ul" or "ol"
        inner = m.group(2)  # content between <ul>...</ul>
        marker_type = "disc" if list_type == "ul" else "decimal"

        # Split inner content at <li> boundaries.
        items = re.split(r"</?li[^>]*>", inner)
        for item_text in items:
            item_text = item_text.strip()
            if not item_text:
                continue
            runs = _parse_inline(item_text)
            if runs:
                children.append(
                    ListItem(
                        runs=runs,
                        marker=ListStyle(type=marker_type, level=0),  # type: ignore[arg-type]
                    )
                )

        last_end = m.end()

    # Emit any remaining text after the last list block.
    after = text[last_end:]
    _emit_paragraphs(after, children, _parse_inline)

    return TextBlock(children=children)


def _emit_paragraphs(
    text: str,
    children: list[Paragraph | ListItem],
    parse_inline,
) -> None:
    """Split text by ``\\n\\n`` and append Paragraph nodes."""
    for block in text.strip().split("\n\n"):
        block = block.strip()
        if not block:
            continue
        runs = parse_inline(block)
        if runs:
            children.append(Paragraph(runs=runs))
