"""Document locale and RTL settings stored in presentation core properties.

Functions:
    normalize_locale       — Normalize locale strings (lowercase, hyphens).
    get_document_locale    — Read stored locale from core_properties.keywords.
    get_document_rtl       — Read stored RTL flag (or infer from locale).
    set_document_settings  — Write locale + RTL markers into core properties.
    resolve_render_settings — Merge CLI flags with document defaults for one slide.

Private:
    _read_keywords  — Parse comma-separated keywords from core properties.
    _write_keywords — Write keywords back to core properties.
"""

from __future__ import annotations

from pptx import Presentation

LOCALE_MARKER = "_sf_locale="
RTL_MARKER = "_sf_rtl="


def normalize_locale(locale: str) -> str:
    """Normalize a locale tag to lowercase with hyphens."""
    return locale.strip().lower().replace("_", "-")


def _read_keywords(prs: Presentation) -> list[str]:
    """Parse core_properties.keywords into a list of trimmed parts."""
    keywords = prs.core_properties.keywords or ""
    return [part.strip() for part in keywords.split(",") if part.strip()]


def _write_keywords(prs: Presentation, parts: list[str]) -> None:
    """Write keywords back to core_properties as a comma-separated string."""
    prs.core_properties.keywords = ", ".join(parts)


def get_document_locale(prs: Presentation) -> str:
    """Return the document locale tag, defaulting to 'en'."""
    for part in _read_keywords(prs):
        if part.startswith(LOCALE_MARKER):
            return part.removeprefix(LOCALE_MARKER)
    return "en"


def get_document_rtl(prs: Presentation) -> bool:
    """Return whether the document defaults to RTL layout and text."""
    for part in _read_keywords(prs):
        if part.startswith(RTL_MARKER):
            return part.removeprefix(RTL_MARKER).lower() == "true"
    locale = get_document_locale(prs)
    return locale.startswith(("ar", "fa", "he", "ur"))


def set_document_settings(prs: Presentation, *, rtl: bool, locale: str) -> None:
    """Persist locale and RTL flags in the presentation's core properties."""
    normalized = normalize_locale(locale)
    if rtl and normalized == "en":
        normalized = "ar"
    parts = [
        part
        for part in _read_keywords(prs)
        if not part.startswith(LOCALE_MARKER) and not part.startswith(RTL_MARKER)
    ]
    parts.append(f"{LOCALE_MARKER}{normalized}")
    parts.append(f"{RTL_MARKER}{str(rtl).lower()}")
    _write_keywords(prs, parts)


def resolve_render_settings(
    prs: Presentation,
    *,
    rtl: bool | None = None,
    locale: str | None = None,
) -> tuple[bool, str]:
    """Resolve effective rtl/locale for one slide from CLI flags or document defaults."""
    active_rtl = get_document_rtl(prs) if rtl is None else rtl
    active_locale = normalize_locale(locale) if locale else get_document_locale(prs)
    if active_rtl and active_locale == "en":
        active_locale = "ar"
    return active_rtl, active_locale
