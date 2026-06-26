# slides-factory Implementation Skills

> Step-by-step guides for building an implementation package on top of the
> `slides-factory` core.

An *implementation package* is a Python package that imports `slides-factory`,
creates a `SlideFactory` instance, and registers templates, frames, and
elements to produce branded slide decks. Examples include `mim-slides` or any
organization-specific deck builder.

## Contents

| Guide | What you'll learn |
|-------|-------------------|
| [01 — Project Setup](01-setup.md) | Package structure, `pyproject.toml`, entry points |
| [02 — Elements](02-elements.md) | Custom drawable elements (text, cards, charts, etc.) |
| [03 — Frames](03-frames.md) | Page shells — backgrounds, chrome, info layers |
| [04 — Templates](04-templates.md) | Slide content — class-based grid templates |
| [05 — Brand Theme](05-brand-theme.md) | YAML brand config (colors, fonts, logos, layout) |
| [06 — CLI & Testing](06-cli-and-testing.md) | CLI integration through `SlideFactory`, writing tests |
| [07 — App Lifecycle](07-app-lifecycle.md) | Registration, discovery, and explicit app pattern |

## Quick Start

```python
# my_slides/__init__.py
from slides_factory.app import SlideFactory

app = SlideFactory("my_slides")
# Templates, frames, and elements are auto-discovered lazily
# from my_slides/templates/, my_slides/frames/, my_slides/elements/
```

```console
$ python -m slides_factory my_slides doc create --help
```
