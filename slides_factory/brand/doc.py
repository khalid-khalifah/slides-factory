"""Persist brand YAML path on a presentation (core properties keywords).

Functions:
    get_document_brand_path — Read stored brand YAML path.
    set_document_brand      — Store brand path on the presentation.
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation

from slides_factory.locale import _read_keywords, _write_keywords

BRAND_MARKER = "_sf_brand="


def get_document_brand_path(prs: Presentation) -> Path | None:
    """Return the brand YAML path stored on the document, if any."""
    for part in _read_keywords(prs):
        if part.startswith(BRAND_MARKER):
            raw = part.removeprefix(BRAND_MARKER)
            if raw:
                return Path(raw)
    return None


def set_document_brand(prs: Presentation, brand_path: Path) -> None:
    """Store the brand YAML path in presentation core properties."""
    resolved = str(brand_path.resolve())
    parts = [p for p in _read_keywords(prs) if not p.startswith(BRAND_MARKER)]
    parts.append(f"{BRAND_MARKER}{resolved}")
    _write_keywords(prs, parts)
