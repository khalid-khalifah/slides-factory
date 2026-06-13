"""Shared response models for CLI JSON output.

Classes:
    CLIResponse — Standard { ok, data, error } envelope for all --json output.

Methods:
    print — Emit JSON or human-readable output depending on --json flag.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


class CLIResponse(BaseModel):
    """Uniform response wrapper so agents can parse every CLI command the same way."""

    ok: bool
    data: Any | None = None
    error: str | None = None
    details: list[Any] | None = None

    def print(self, as_json: bool) -> None:
        """Print the response as JSON or plain text."""
        if as_json:
            print(
                json.dumps(
                    self.model_dump(exclude_none=True),
                    indent=2,
                    ensure_ascii=False,
                )
            )
        elif self.ok:
            if self.data is not None:
                print(json.dumps(self.data, indent=2, ensure_ascii=False))
        else:
            print(f"Error: {self.error}")
            if self.details:
                for detail in self.details:
                    print(f"  - {detail}")
