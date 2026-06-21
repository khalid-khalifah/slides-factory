"""Central slide factory application — registry, CLI, and catalog (FastAPI-style).

Classes:
    SlideFactory — Templates and frames register via @app.template / @app.frame functions.

Functions:
    get_app — Return the active application instance.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from pptx.slide import Slide

from slides_factory.elements.base import Element, element_from_function
from slides_factory.exceptions import AppNotConfiguredError
from slides_factory.frame import FrameTemplate
from slides_factory.palette import SlidePalette
from slides_factory.registration import (
    frame_from_function,
    template_from_class,
    template_from_function,
)
from slides_factory.template import SlideTemplate
from slides_factory.templating import Template

if False:  # typing only — avoid importing pydantic models at module load
    from pydantic import BaseModel

_active_app: SlideFactory | None = None


def get_app() -> SlideFactory:
    """Return the active application instance."""
    if _active_app is None:
        raise AppNotConfiguredError(
            "No slide factory app configured. Import an implementation package "
            "(e.g. mim_slides) before using the catalog or CLI."
        )
    return _active_app


class SlideFactory:
    """Central app: template and frame functions register on import via decorators."""

    def __init__(
        self,
        name: str,
        *,
        help: str | None = None,
        preview_impl_module: str | None = None,
        preview_brand: Path | None = None,
        preview_page_title: str | None = None,
    ) -> None:
        global _active_app
        _active_app = self
        self.name = name
        self.help = help or f"{name} slide factory"
        self.preview_impl_module = preview_impl_module
        self.preview_brand = preview_brand
        self.preview_page_title = preview_page_title
        self._templates: dict[str, SlideTemplate | Template] = {}
        self._frames: dict[str, FrameTemplate] = {}
        self._elements: dict[str, Element] = {}
        self._template_sources: dict[str, Path] = {}
        self._frame_sources: dict[str, Path] = {}
        self._discovered_template_packages: set[str] = set()
        self._discovered_frame_packages: set[str] = set()
        self._register_builtins()
        from slides_factory.cli import build_cli

        self.cli = build_cli(self)

    def _register_builtins(self) -> None:
        """Register the core drawable elements (grid is core, not a template)."""
        from slides_factory.elements.card import CardProps, CardStyle, render_card
        from slides_factory.elements.text import TextProps, TextStyle, render_text

        self._elements["text"] = element_from_function(
            render_text, kind="text", props_model=TextProps, style_model=TextStyle
        )
        self._elements["card"] = element_from_function(
            render_card, kind="card", props_model=CardProps, style_model=CardStyle
        )

    def template(
        self,
        template_id: str,
        /,
        *,
        name: str,
        description: str = "",
        grid: str = "",
        layout_name: str | None = None,
        extract: Callable[[Slide], Any] | None = None,
        tags: Sequence[str] | None = None,
        default_frame: str | None = None,
    ) -> Callable[[Any], Any]:
        """Register a template.

        Decorates either a class-based grid :class:`Template` (recommended:
        ``@at`` cell methods with inferred input, plus ``grid`` classes) or a
        free-form render function ``(slide, ctx, data: TemplateInput)``.
        """

        def decorator(obj: Any) -> Any:
            if isinstance(obj, type) and issubclass(obj, Template):
                self._templates[template_id] = template_from_class(
                    obj,
                    self,
                    template_id=template_id,
                    name=name,
                    description=description,
                    grid=grid,
                    layout_name=layout_name,
                    tags=tags,
                    default_frame=default_frame,
                )
            else:
                self._templates[template_id] = template_from_function(
                    obj,
                    template_id=template_id,
                    name=name,
                    description=description,
                    layout_name=layout_name,
                    extract=extract,
                    tags=tags,
                    default_frame=default_frame,
                )
            self._template_sources[template_id] = Path(inspect.getfile(obj)).resolve()
            return obj

        return decorator

    def frame(
        self,
        frame_id: str,
        /,
        *,
        name: str,
        description: str = "",
        palette: SlidePalette,
        playground: Any = None,
        frame_input: Any = None,
        frame_style: Any = None,
        allows_layout: bool = True,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a frame render function.

        Signatures: ``(slide, ctx)``, ``(slide, ctx, info)``, or
        ``(slide, ctx, info, style)`` when ``frame_style`` is declared.
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._frames[frame_id] = frame_from_function(
                func,
                frame_id=frame_id,
                name=name,
                description=description,
                palette=palette,
                playground=playground,
                frame_input=frame_input,
                frame_style=frame_style,
                allows_layout=allows_layout,
            )
            self._frame_sources[frame_id] = Path(inspect.getfile(func)).resolve()
            return func

        return decorator

    def element(
        self,
        kind: str,
        /,
        *,
        props_model: type[BaseModel],
        style_model: type[BaseModel] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register an element render function ``(slide, box, props, style, ctx)``."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._elements[kind] = element_from_function(
                func, kind=kind, props_model=props_model, style_model=style_model
            )
            return func

        return decorator

    def list_elements(self) -> list[Element]:
        """Return every registered element instance."""
        return list(self._elements.values())

    def get_element(self, kind: str) -> Element:
        """Return an element by kind, or raise KeyError with available kinds."""
        if kind not in self._elements:
            available = ", ".join(sorted(self._elements)) or "(none)"
            raise KeyError(f"Unknown element '{kind}'. Available: {available}")
        return self._elements[kind]

    @property
    def impl_base_package(self) -> str | None:
        """Implementation root package (e.g. ``mim_slides``) when templates were discovered."""
        if not self._discovered_template_packages:
            return None
        pkg = next(iter(self._discovered_template_packages))
        if "." in pkg:
            return pkg.rsplit(".", 1)[0]
        return pkg

    def discover_templates(self, package: str) -> None:
        """Import every template module in a package (@app.template runs on import)."""
        if package in self._discovered_template_packages:
            return
        pkg = importlib.import_module(package)
        if not hasattr(pkg, "__path__"):
            raise ValueError(f"package {package!r} has no submodules to discover")
        for module_info in pkgutil.iter_modules(pkg.__path__):
            if module_info.name.startswith("_"):
                continue
            importlib.import_module(f"{package}.{module_info.name}")
        self._discovered_template_packages.add(package)

    def discover_frames(self, package: str) -> None:
        """Import every frame module in a package (@app.frame runs on import)."""
        if package in self._discovered_frame_packages:
            return
        pkg = importlib.import_module(package)
        if not hasattr(pkg, "__path__"):
            raise ValueError(f"package {package!r} has no submodules to discover")
        for module_info in pkgutil.iter_modules(pkg.__path__):
            if module_info.name.startswith("_"):
                continue
            importlib.import_module(f"{package}.{module_info.name}")
        self._discovered_frame_packages.add(package)

    def _ensure_catalog(self) -> None:
        if not self._discovered_template_packages and not self._discovered_frame_packages:
            raise RuntimeError(
                "No templates or frames registered. Call discover_templates() "
                "and discover_frames() on the app, or import an implementation package."
            )

    def list_templates(self, *, tag: str | None = None) -> list[SlideTemplate | Template]:
        self._ensure_catalog()
        templates = list(self._templates.values())
        if tag is None:
            return templates
        tag_lower = tag.lower()
        return [tpl for tpl in templates if tag_lower in tpl.tags]

    def list_tags(self) -> list[str]:
        self._ensure_catalog()
        tags = {tag for tpl in self._templates.values() for tag in tpl.tags}
        return sorted(tags)

    def get_template(self, template_id: str) -> SlideTemplate | Template:
        self._ensure_catalog()
        if template_id not in self._templates:
            available = ", ".join(sorted(self._templates)) or "(none)"
            raise KeyError(f"Unknown template '{template_id}'. Available: {available}")
        return self._templates[template_id]

    def search_templates(self, query: str) -> list[SlideTemplate | Template]:
        query_lower = query.lower()
        return [
            tpl
            for tpl in self.list_templates()
            if query_lower in tpl.id.lower()
            or query_lower in tpl.name.lower()
            or query_lower in tpl.description.lower()
            or any(query_lower in tag for tag in tpl.tags)
        ]

    def list_frames(self) -> list[FrameTemplate]:
        self._ensure_catalog()
        return list(self._frames.values())

    def get_frame(self, frame_id: str) -> FrameTemplate:
        self._ensure_catalog()
        if frame_id not in self._frames:
            available = ", ".join(sorted(self._frames)) or "(none)"
            raise KeyError(f"Unknown frame '{frame_id}'. Available: {available}")
        return self._frames[frame_id]
