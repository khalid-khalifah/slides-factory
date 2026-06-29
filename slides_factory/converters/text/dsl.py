"""Python DSL constructor — build TextBlock trees with concise function calls."""

from __future__ import annotations

from slides_factory.converters.text.model import ListItem, Paragraph, TextBlock, TextRun


def text(*args) -> TextBlock:
    """Build a ``TextBlock`` from a concise Python DSL.

    Each positional argument produces one block-level child:

    * ``str`` — plain-text paragraph (single run, no formatting).
    * ``tuple[str, dict]`` — single-run paragraph with style overrides.
    * ``list`` — multi-run paragraph (each element is a ``str`` or ``tuple``).
    * ``Paragraph | ListItem`` — passed through as-is.
    * ``TextBlock`` — its children are inlined (flattened).

    Examples::

        text("Hello")                                         # one paragraph
        text("A", [("B ", {}), ("C", {"bold": True})])       # two paragraphs
    """
    children: list[Paragraph | ListItem] = []
    for arg in args:
        if isinstance(arg, TextBlock):
            children.extend(arg.children)
        elif isinstance(arg, (Paragraph, ListItem)):
            children.append(arg)
        elif isinstance(arg, str):
            children.append(Paragraph(runs=[TextRun(text=arg)]))
        elif isinstance(arg, tuple):
            run_text, run_kwargs = arg
            children.append(
                Paragraph(runs=[TextRun(text=str(run_text), **run_kwargs)])
            )
        elif isinstance(arg, list):
            runs: list[TextRun] = []
            for item in arg:
                if isinstance(item, str):
                    runs.append(TextRun(text=item))
                elif isinstance(item, tuple):
                    runs.append(TextRun(text=str(item[0]), **item[1]))
                elif isinstance(item, TextRun):
                    runs.append(item)
            children.append(Paragraph(runs=runs))
        else:
            raise TypeError(f"unsupported text() argument type: {type(arg).__name__}")
    return TextBlock(children=children)
