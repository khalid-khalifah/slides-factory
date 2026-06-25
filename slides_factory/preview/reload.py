"""Hot-reload template and frame modules for the Streamlit preview."""

from __future__ import annotations

import importlib
import sys
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from slides_factory.app import SlideFactory

AUTO_RELOAD_INTERVAL = timedelta(seconds=2)

_HELPER_SUBDIRS = ("render", "frames", "templates/helpers")


def watch_paths_for_preview(
    factory: "SlideFactory",
    *,
    template_id: str,
    frame_id: str | None,
    brand_path: Path | None,
) -> list[Path]:
    """Return filesystem paths whose mtimes should trigger a preview refresh."""
    paths: list[Path] = []

    # Trigger lazy discovery before accessing private source dicts.
    base_pkg = factory.impl_base_package

    tpl_src = factory._template_sources.get(template_id)
    if tpl_src is not None:
        paths.append(tpl_src)

    if frame_id:
        frm_src = factory._frame_sources.get(frame_id)
        if frm_src is not None:
            paths.append(frm_src)

    if brand_path is not None and brand_path.is_file():
        paths.append(brand_path.resolve())
    if base_pkg is not None:
        try:
            base_dir = Path(importlib.import_module(base_pkg).__file__).resolve().parent
        except (ImportError, TypeError):
            base_dir = None
        if base_dir is not None:
            for sub in _HELPER_SUBDIRS:
                directory = base_dir / sub
                if directory.is_dir():
                    paths.extend(sorted(directory.glob("*.py")))

    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen and resolved.is_file():
            seen.add(resolved)
            unique.append(resolved)
    return unique


def file_mtimes(paths: list[Path]) -> dict[str, float]:
    """Map absolute path strings to last-modified timestamps."""
    mtimes: dict[str, float] = {}
    for path in paths:
        if path.is_file():
            mtimes[str(path.resolve())] = path.stat().st_mtime
    return mtimes


def changed_files(old_mtimes: dict[str, float], paths: list[Path]) -> list[Path]:
    """Return watch paths whose mtime differs from *old_mtimes*."""
    current = file_mtimes(paths)
    changed: list[Path] = []
    for path in paths:
        key = str(path.resolve())
        if key not in current:
            continue
        if old_mtimes.get(key) != current[key]:
            changed.append(path)
    return changed


def module_name_for_path(path: Path, factory: "SlideFactory") -> str | None:
    """Map a file under the implementation package to its import name."""
    base_pkg = factory.impl_base_package
    if base_pkg is None:
        return None
    try:
        base_dir = Path(importlib.import_module(base_pkg).__file__).resolve().parent
        rel = path.resolve().relative_to(base_dir)
    except (ImportError, TypeError, ValueError):
        return None
    if rel.suffix != ".py":
        return None
    parts = rel.with_suffix("").parts
    return f"{base_pkg}.{'.'.join(parts)}"


def _reload_order_key(module_name: str) -> tuple[int, str]:
    """Sort modules so helpers reload before templates that import them."""
    if module_name.startswith("slides_factory."):
        return (0, module_name)
    if ".render." in module_name:
        return (1, module_name)
    if ".templates.helpers." in module_name:
        return (2, module_name)
    if ".frames." in module_name:
        return (3, module_name)
    if ".templates." in module_name:
        return (4, module_name)
    return (5, module_name)


def reload_modules(module_names: list[str]) -> list[str]:
    """Reload already-imported modules in dependency-safe order."""
    reloaded: list[str] = []
    for name in sorted(set(module_names), key=_reload_order_key):
        if name in sys.modules:
            importlib.reload(sys.modules[name])
        else:
            importlib.import_module(name)
        reloaded.append(name)
    return reloaded


def reload_changed_sources(
    factory: "SlideFactory",
    changed: list[Path],
) -> list[str]:
    """Reload Python modules backing changed watch paths."""
    module_names: list[str] = []
    for path in changed:
        if path.suffix != ".py":
            continue
        name = module_name_for_path(path, factory)
        if name is not None:
            module_names.append(name)
    if not module_names:
        return []
    return reload_modules(module_names)


def format_reload_notice(changed: list[Path]) -> str:
    """Short user-facing summary of which files triggered reload."""
    names = ", ".join(path.name for path in changed[:3])
    if len(changed) > 3:
        names += f" (+{len(changed) - 3} more)"
    return names
