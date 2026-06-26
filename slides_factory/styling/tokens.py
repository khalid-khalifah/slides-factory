"""Parse Tailwind-like utility-class strings into resolved layout style objects.

Two parsers — each strict (unknown tokens raise):

* ``parse_grid`` — grid container: columns/rows tracks, gaps, padding.
* ``parse_cell`` — cell placement: spans, explicit start, alignment.
"""

from __future__ import annotations

from dataclasses import dataclass

from slides_factory.styling import theme

_ALIGN_VALUES = {"start", "center", "end"}


@dataclass(frozen=True)
class GridStyle:
    """Resolved grid container: track ratios and gap/padding fractions."""

    columns: tuple[float, ...] = (1.0,)
    rows: tuple[float, ...] = (1.0,)
    auto_rows: bool = False
    col_gap: float = 0.0
    row_gap: float = 0.0
    pad_x: float = 0.0
    pad_y: float = 0.0


@dataclass(frozen=True)
class CellStyle:
    """Resolved cell placement within the grid."""

    col_span: int = 1
    row_span: int = 1
    col_start: int | None = None
    row_start: int | None = None
    align_x: str = "stretch"
    align_y: str = "stretch"


def _tokens(class_str: str) -> list[str]:
    return class_str.split()


def _as_int(value: str, token: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"expected an integer in token {token!r}") from exc


def _parse_track(value: str, token: str) -> tuple[float, ...]:
    """Parse a track spec: ``3`` (equal columns) or ``[2_1_1]`` (ratios)."""
    if value.startswith("[") and value.endswith("]"):
        parts = [p for p in value[1:-1].split("_") if p != ""]
        if not parts:
            raise ValueError(f"empty track list in token {token!r}")
        ratios: list[float] = []
        for part in parts:
            try:
                ratio = float(part)
            except ValueError as exc:
                raise ValueError(f"invalid ratio {part!r} in token {token!r}") from exc
            if ratio <= 0:
                raise ValueError(f"track ratios must be > 0 in token {token!r}")
            ratios.append(ratio)
        return tuple(ratios)
    count = _as_int(value, token)
    if count < 1:
        raise ValueError(f"track count must be >= 1 in token {token!r}")
    return tuple(1.0 for _ in range(count))


def _align(value: str, token: str) -> str:
    if value not in _ALIGN_VALUES:
        allowed = ", ".join(sorted(_ALIGN_VALUES))
        raise ValueError(f"invalid alignment {value!r} in token {token!r}; allowed: {allowed}")
    return value


def parse_grid(class_str: str) -> GridStyle:
    """Parse grid-container utility classes into a :class:`GridStyle`."""
    columns: tuple[float, ...] = (1.0,)
    rows: tuple[float, ...] = (1.0,)
    auto_rows = False
    col_gap = row_gap = pad_x = pad_y = 0.0

    for token in _tokens(class_str):
        if token.startswith("grid-cols-"):
            columns = _parse_track(token[len("grid-cols-") :], token)
        elif token == "grid-rows-auto":
            if rows != (1.0,):
                raise ValueError(
                    "grid-rows-auto is mutually exclusive with explicit grid-rows-N"
                )
            auto_rows = True
        elif token.startswith("grid-rows-"):
            if auto_rows:
                raise ValueError(
                    "grid-rows-N is mutually exclusive with grid-rows-auto"
                )
            rows = _parse_track(token[len("grid-rows-") :], token)
        elif token.startswith("gap-x-"):
            col_gap = theme.spacing(_as_int(token[len("gap-x-") :], token))
        elif token.startswith("gap-y-"):
            row_gap = theme.spacing(_as_int(token[len("gap-y-") :], token))
        elif token.startswith("gap-"):
            col_gap = row_gap = theme.spacing(_as_int(token[len("gap-") :], token))
        elif token.startswith("px-"):
            pad_x = theme.spacing(_as_int(token[len("px-") :], token))
        elif token.startswith("py-"):
            pad_y = theme.spacing(_as_int(token[len("py-") :], token))
        elif token.startswith("p-"):
            pad_x = pad_y = theme.spacing(_as_int(token[len("p-") :], token))
        else:
            raise ValueError(f"unknown grid utility class: {token!r}")

    return GridStyle(
        columns=columns,
        rows=rows,
        auto_rows=auto_rows,
        col_gap=col_gap,
        row_gap=row_gap,
        pad_x=pad_x,
        pad_y=pad_y,
    )


def parse_cell(class_str: str) -> CellStyle:
    """Parse cell-placement utility classes into a :class:`CellStyle`."""
    col_span = row_span = 1
    col_start: int | None = None
    row_start: int | None = None
    align_x = align_y = "stretch"

    for token in _tokens(class_str):
        if token.startswith("col-span-"):
            col_span = _positive(token[len("col-span-") :], token)
        elif token.startswith("row-span-"):
            row_span = _positive(token[len("row-span-") :], token)
        elif token.startswith("col-start-"):
            col_start = _positive(token[len("col-start-") :], token)
        elif token.startswith("row-start-"):
            row_start = _positive(token[len("row-start-") :], token)
        elif token.startswith("justify-"):
            align_x = _align(token[len("justify-") :], token)
        elif token.startswith("items-"):
            align_y = _align(token[len("items-") :], token)
        else:
            raise ValueError(f"unknown cell utility class: {token!r}")

    return CellStyle(
        col_span=col_span,
        row_span=row_span,
        col_start=col_start,
        row_start=row_start,
        align_x=align_x,
        align_y=align_y,
    )


def _positive(value: str, token: str) -> int:
    number = _as_int(value, token)
    if number < 1:
        raise ValueError(f"value must be >= 1 in token {token!r}")
    return number
