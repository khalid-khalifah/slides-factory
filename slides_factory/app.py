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

from slides_factory.frame import FrameTemplate
from slides_factory.palette import SlidePalette
from slides_factory.registration import frame_from_function, template_from_function
from slides_factory.template import SlideTemplate

_active_app: SlideFactory | None = None


def get_app() -> SlideFactory:
    """Return the active application instance."""
    if _active_app is None:
        raise RuntimeError(
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
        self._templates: dict[str, SlideTemplate] = {}
        self._frames: dict[str, FrameTemplate] = {}
        self._template_sources: dict[str, Path] = {}
        self._frame_sources: dict[str, Path] = {}
        self._discovered_template_packages: set[str] = set()
        self._discovered_frame_packages: set[str] = set()
        from slides_factory.cli import build_cli

        self.cli = build_cli(self)

    def template(
        self,
        template_id: str,
        /,
        *,
        name: str,
        description: str = "",
        layout_name: str | None = None,
        extract: Callable[[Slide], Any] | None = None,
        tags: Sequence[str] | None = None,
        default_frame: str | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a template render function with a single TemplateInput data parameter."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._templates[template_id] = template_from_function(
                func,
                template_id=template_id,
                name=name,
                description=description,
                layout_name=layout_name,
                extract=extract,
                tags=tags,
                default_frame=default_frame,
            )
            self._template_sources[template_id] = Path(
                inspect.getfile(func)
            ).resolve()
            return func

        return decorator

    def frame(
        self,
        frame_id: str,
        /,
        *,
        name: str,
        description: str = "",
        palette: SlidePalette,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a frame render function (slide, ctx only — no slide JSON input)."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._frames[frame_id] = frame_from_function(
                func,
                frame_id=frame_id,
                name=name,
                description=description,
                palette=palette,
            )
            self._frame_sources[frame_id] = Path(inspect.getfile(func)).resolve()
            return func

        return decorator

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

    def list_templates(self, *, tag: str | None = None) -> list[SlideTemplate]:
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

    def get_template(self, template_id: str) -> SlideTemplate:
        self._ensure_catalog()
        if template_id not in self._templates:
            available = ", ".join(sorted(self._templates)) or "(none)"
            raise KeyError(
                f"Unknown template '{template_id}'. Available: {available}"
            )
        return self._templates[template_id]

    def search_templates(self, query: str) -> list[SlideTemplate]:
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

