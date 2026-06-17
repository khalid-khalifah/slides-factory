"""Core layout model — the engine's render contract.

A :class:`Layout` is what the grid+element core actually draws: a grid utility
string, an ordered list of cells (each = placement classes + one element), and
optional frame information. It is brand-agnostic and has nothing to do with
templates — templates are a higher-level layer that *produces* a Layout.

Authoring stays abstract via utility-class strings. There is no ``class`` key:

* ``Layout.grid``      — grid container classes (``grid-cols-[2_1] grid-rows-2 gap-4``).
* ``CellSpec.at``      — cell placement classes (``col-span-2 items-center``).
* ``ElementSpec.style``— element look classes (``text-2xl font-bold text-primary``).

Classes:
    ElementSpec — kind + style string + raw props for one element.
    CellSpec    — placement string + the element it holds.
    Layout      — full grid layout: frame info + grid string + cells.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

class ElementSpec(BaseModel):
    """One element: its registered kind, look classes, and validated-later props."""

    kind: str = Field(description="Registered element kind, e.g. 'text' or 'card'.")
    style: str = Field(default="", description="Element look utility classes.")
    props: dict[str, Any] = Field(default_factory=dict, description="Raw element props.")


class CellSpec(BaseModel):
    """A grid cell: placement classes plus the element it holds."""

    at: str = Field(default="", description="Cell placement utility classes.")
    element: ElementSpec


class Layout(BaseModel):
    """Full grid layout consumed by the core ``render_layout`` primitive."""

    frame_info: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw frame input stored on the layout; validated against the active frame model at render.",
    )
    grid: str = Field(default="", description="Grid container utility classes.")
    cells: list[CellSpec] = Field(default_factory=list)
