"""Shared typing annotation helpers for registration and preview forms."""

from __future__ import annotations

from typing import Annotated, Any, Union, get_args, get_origin


def unwrap_annotation(hint: Any) -> Any:
    """Strip ``Annotated[...]`` wrappers from a type hint."""
    origin = get_origin(hint)
    if origin is Annotated:
        return get_args(hint)[0]
    return hint


def unwrap_optional_annotation(hint: Any) -> tuple[Any, bool]:
    """Unwrap ``Annotated`` and optional ``T | None`` unions.

    Returns ``(inner_type, is_optional)``.
    """
    if get_origin(hint) is Annotated:
        hint = get_args(hint)[0]
    origin = get_origin(hint)
    if origin is Union:
        args = [arg for arg in get_args(hint) if arg is not type(None)]
        if len(args) == 1:
            return args[0], True
    return hint, False
