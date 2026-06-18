"""Typer CLI wired to a SlideFactory instance.

The slide surface is flag-driven and built around an incremental grid builder so
LLM agents never have to hand-author JSON blobs:

    doc create  -> slide new  -> el add ... -> el add ...

Discovery commands (`elements list/inspect`, `classes`) let an agent learn the
element props and the utility-class vocabulary before composing a deck.
"""

from __future__ import annotations

import typing
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
from pydantic import BaseModel

from slides_factory import document
from slides_factory.frame_info import EmptyFrameInput
from slides_factory.brand import load_brand
from slides_factory.models import CLIResponse
from slides_factory.styling import theme

if TYPE_CHECKING:
    from slides_factory.app import SlideFactory


def build_cli(factory: "SlideFactory") -> typer.Typer:
    app = typer.Typer(name=factory.name, help=factory.help, no_args_is_help=True)
    frames_app = typer.Typer(help="Browse page frame templates.")
    elements_app = typer.Typer(help="Browse drawable elements and their props.")
    templates_app = typer.Typer(help="Browse and instantiate registered templates.")
    brand_app = typer.Typer(help="Inspect brand YAML themes.")
    doc_app = typer.Typer(help="Create and inspect presentations.")
    slide_app = typer.Typer(help="Create grid slides and edit slide-level settings.")
    el_app = typer.Typer(help="Add, edit, and remove elements inside a grid slide.")

    app.add_typer(frames_app, name="frames")
    app.add_typer(elements_app, name="elements")
    app.add_typer(templates_app, name="templates")
    app.add_typer(brand_app, name="brand")
    app.add_typer(doc_app, name="doc")
    app.add_typer(slide_app, name="slide")
    app.add_typer(el_app, name="el")

    def _emit(response: CLIResponse, as_json: bool, exit_code: int = 0) -> None:
        response.print(as_json)
        if not response.ok:
            raise typer.Exit(code=exit_code)

    def _require_file(path: Path, as_json: bool) -> None:
        if not path.exists():
            _emit(
                CLIResponse(ok=False, error=f"File not found: {path}"),
                as_json,
                exit_code=1,
            )

    def _resolve_output(path: Path, output: Path | None) -> Path:
        return output if output else path

    def _is_list_field(annotation: Any) -> bool:
        return typing.get_origin(annotation) is list

    def _nested_model_type(annotation: Any) -> type[BaseModel] | None:
        from slides_factory.template_input import TemplateInput
        from slides_factory.typing_utils import unwrap_optional_annotation

        annotation, _ = unwrap_optional_annotation(annotation)
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            if not issubclass(annotation, TemplateInput):
                return annotation
        return None

    def _build_model_data(model: type[BaseModel], pairs: list[str]) -> dict[str, Any]:
        """Turn repeated ``key=value`` flags into a dict for a Pydantic model.

        Repeated keys accumulate into a list for list-typed fields; scalar fields
        reject duplicates so mistakes surface instead of silently dropping values.
        """
        accumulated: dict[str, list[str]] = {}
        for pair in pairs:
            if "=" not in pair:
                raise typer.BadParameter(f"--set expects key=value, got: {pair!r}")
            key, value = pair.split("=", 1)
            accumulated.setdefault(key, []).append(value)

        fields = model.model_fields
        out: dict[str, Any] = {}
        for key, values in accumulated.items():
            field = fields.get(key)
            if field is not None and _is_list_field(field.annotation):
                out[key] = values
            elif len(values) > 1:
                raise typer.BadParameter(
                    f"field {key!r} given multiple times but is not a list field"
                )
            else:
                out[key] = values[0]
        return out

    def _build_nested_model_data(model: type[BaseModel], pairs: list[str]) -> dict[str, Any]:
        """Turn ``key=value`` flags into a dict, supporting dotted cell prop paths."""
        scalar_pairs: list[str] = []
        nested_pairs: dict[str, list[str]] = {}
        fields = model.model_fields

        for pair in pairs:
            if "=" not in pair:
                raise typer.BadParameter(f"--set expects key=value, got: {pair!r}")
            key, value = pair.split("=", 1)
            if "." in key:
                top, rest = key.split(".", 1)
                if top not in fields:
                    raise typer.BadParameter(f"unknown field {top!r}")
                nested_model = _nested_model_type(fields[top].annotation)
                if nested_model is None:
                    raise typer.BadParameter(
                        f"field {top!r} is not a nested object; use {top!r}=value"
                    )
                nested_pairs.setdefault(top, []).append(f"{rest}={value}")
            else:
                scalar_pairs.append(pair)

        out = _build_model_data(model, scalar_pairs)
        for top, sub_pairs in nested_pairs.items():
            nested_model = _nested_model_type(fields[top].annotation)
            assert nested_model is not None
            out[top] = _build_model_data(nested_model, sub_pairs)
        return out

    def _build_props(props_model: type[BaseModel], pairs: list[str]) -> dict[str, Any]:
        return _build_model_data(props_model, pairs)

    def _resolve_frame_input(frame_id: str | None) -> type[BaseModel]:
        from slides_factory.frame import get_frame

        if frame_id:
            return get_frame(frame_id).frame_input
        return EmptyFrameInput

    def _grid_slide_frame_input(
        prs: Any, index: int, frame_override: str | None
    ) -> type[BaseModel]:
        if frame_override:
            return _resolve_frame_input(frame_override)
        info = document.get_slide_info(prs, index)
        return _resolve_frame_input(info.get("frame_id"))

    def _resolve_slide_data_model(
        template_id: str | None, frame_id: str | None
    ) -> type[BaseModel]:
        if template_id:
            template = factory.get_template(template_id)
            return type(template).input_model
        if frame_id:
            return _resolve_frame_input(frame_id)
        raise typer.BadParameter("Provide --template or --frame.")

    def _current_cell_kind(prs, index: int, cell: int) -> str:
        info = document.get_slide_info(prs, index)
        cells = info.get("data", {}).get("cells", [])
        if cell < 0 or cell >= len(cells):
            raise typer.BadParameter(f"Cell index {cell} out of range")
        return cells[cell]["element"]["kind"]

    # --- discovery -------------------------------------------------------

    def _element_summary(element) -> dict[str, Any]:
        fields = []
        for name, field in element.props_model.model_fields.items():
            fields.append(
                {
                    "name": name,
                    "list": _is_list_field(field.annotation),
                    "required": field.is_required(),
                }
            )
        return {"kind": element.kind, "props": fields}

    @elements_app.command("list")
    def elements_list(
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """List drawable element kinds and their prop names."""
        items = [_element_summary(el) for el in factory.list_elements()]
        items.sort(key=lambda item: item["kind"])
        _emit(
            CLIResponse(ok=True, data={"elements": items, "count": len(items)}),
            as_json,
        )

    @elements_app.command("inspect")
    def elements_inspect(
        kind: Annotated[str, typer.Argument(help="Element kind, e.g. 'card'.")],
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """Show the full props JSON schema for one element kind."""
        try:
            element = factory.get_element(kind)
        except KeyError as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)
            return
        _emit(
            CLIResponse(
                ok=True,
                data={
                    "kind": element.kind,
                    "props": _element_summary(element)["props"],
                    "json_schema": element.props_model.model_json_schema(),
                },
            ),
            as_json,
        )

    @app.command("classes")
    def classes_cmd(
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """Print the utility-class vocabulary used by --grid and --at."""
        spacing = [str(step) for step in sorted(theme.SPACING_SCALE)]
        aligns = ["start", "center", "end"]
        data = {
            "grid": [
                "grid-cols-N",
                "grid-cols-[a_b_c]",
                "grid-rows-N",
                "grid-rows-[a_b]",
                "gap-{step}",
                "gap-x-{step}",
                "gap-y-{step}",
                "p-{step}",
                "px-{step}",
                "py-{step}",
            ],
            "cell (--at)": [
                "col-span-N",
                "row-span-N",
                "col-start-N",
                "row-start-N",
                f"items-{{{'|'.join(aligns)}}}",
                f"justify-{{{'|'.join(aligns)}}}",
            ],
            "scales": {
                "spacing": spacing,
            },
        }
        _emit(CLIResponse(ok=True, data=data), as_json)

    def _template_summary(template) -> dict[str, Any]:
        cls = type(template)
        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "grid": getattr(cls, "grid", ""),
            "default_frame": cls.default_frame,
            "tags": list(cls.tags),
        }

    @templates_app.command("list")
    def templates_list(
        tag: Annotated[
            str | None, typer.Option("--tag", help="Filter templates by tag.")
        ] = None,
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """List registered templates with their descriptions."""
        try:
            items = [_template_summary(t) for t in factory.list_templates(tag=tag)]
        except RuntimeError as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)
            return
        items.sort(key=lambda item: item["id"])
        data: dict[str, Any] = {"templates": items, "count": len(items)}
        if tag is not None:
            data["tag"] = tag
        _emit(CLIResponse(ok=True, data=data), as_json)

    @templates_app.command("inspect")
    def templates_inspect(
        template_id: Annotated[str, typer.Argument(help="Template id.")],
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """Show a template's grid, description, and input JSON schema."""
        try:
            template = factory.get_template(template_id)
        except KeyError as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)
            return
        cls = type(template)
        _emit(
            CLIResponse(
                ok=True,
                data={
                    **_template_summary(template),
                    "layout_name": cls.layout_name,
                    "json_schema": template.get_json_schema(),
                },
            ),
            as_json,
        )

    @frames_app.command("list")
    def frames_list(
        as_json: Annotated[
            bool, typer.Option("--json", help="Machine-readable JSON output.")
        ] = False,
    ) -> None:
        """List registered page frame templates."""
        items = [
            {"id": frame.id, "name": frame.name, "description": frame.description}
            for frame in factory.list_frames()
        ]
        items.sort(key=lambda item: item["id"])
        _emit(
            CLIResponse(ok=True, data={"frames": items, "count": len(items)}),
            as_json,
        )

    @brand_app.command("inspect")
    def brand_inspect(
        path: Annotated[Path, typer.Argument(help="Path to brand YAML file.")],
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """Show parsed brand theme (colors, fonts, default frame)."""
        _require_file(path, as_json)
        try:
            theme_obj = load_brand(path)
            _emit(
                CLIResponse(
                    ok=True,
                    data={
                        "path": str(path.resolve()),
                        "name": theme_obj.name,
                        "default_frame": theme_obj.default_frame,
                        "base_pptx": (
                            str(theme_obj.resolve_base_pptx())
                            if theme_obj.base_pptx
                            else None
                        ),
                        "page": theme_obj.page.model_dump(),
                        "layout": theme_obj.layout.model_dump(),
                        "colors": theme_obj.colors.model_dump(),
                        "fonts": theme_obj.fonts.model_dump(),
                        "logos": {
                            k: str(theme_obj.resolve_logo(k)) for k in theme_obj.logos
                        },
                    },
                ),
                as_json,
            )
        except Exception as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)

    # --- document --------------------------------------------------------

    @doc_app.command("create")
    def doc_create(
        output: Annotated[
            Path, typer.Option("-o", "--output", help="Output .pptx path.")
        ],
        theme_path: Annotated[
            Path | None,
            typer.Option("--theme", help="Optional base .pptx for slide layouts."),
        ] = None,
        brand: Annotated[
            Path | None,
            typer.Option(
                "--brand", help="Brand YAML (colors, fonts, logos, default frame)."
            ),
        ] = None,
        rtl: Annotated[
            bool,
            typer.Option(
                "--rtl/--no-rtl",
                help="Enable RTL text and mirrored slide layout.",
            ),
        ] = False,
        locale: Annotated[
            str,
            typer.Option(
                "--locale",
                help="Language tag for text runs (defaults to ar when --rtl).",
            ),
        ] = "en",
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """Create a new empty presentation."""
        try:
            document.create_document(
                output, theme_path, brand=brand, rtl=rtl, locale=locale
            )
            data: dict[str, Any] = {
                "path": str(output.resolve()),
                "slide_count": 0,
                "rtl": rtl,
                "locale": "ar" if rtl and locale == "en" else locale,
            }
            if brand is not None:
                loaded = load_brand(brand)
                data["brand"] = str(brand.resolve())
                data["default_frame"] = loaded.default_frame
            _emit(CLIResponse(ok=True, data=data), as_json)
        except Exception as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)

    @doc_app.command("set-rtl")
    def doc_set_rtl(
        path: Annotated[Path, typer.Argument(help="Path to .pptx file.")],
        rtl: Annotated[
            bool,
            typer.Option(
                "--rtl/--no-rtl", help="Enable or disable RTL for future slides."
            ),
        ] = True,
        locale: Annotated[
            str | None,
            typer.Option("--locale", help="Optional language tag, e.g. ar-SA."),
        ] = None,
        output: Annotated[Path | None, typer.Option("-o", "--output")] = None,
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """Set whether the document uses RTL layout and text direction."""
        _require_file(path, as_json)
        try:
            prs = document.open_document(path)
            settings = document.update_document_rtl(prs, rtl=rtl, locale=locale)
            save_path = _resolve_output(path, output)
            document.save_document(prs, save_path)
            settings["path"] = str(save_path.resolve())
            _emit(CLIResponse(ok=True, data=settings), as_json)
        except Exception as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)

    @doc_app.command("info")
    def doc_info(
        path: Annotated[Path, typer.Argument(help="Path to .pptx file.")],
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """List slides in a presentation with per-slide summaries."""
        _require_file(path, as_json)
        try:
            prs = document.open_document(path)
            info = document.list_slides_info(prs)
            info["path"] = str(path.resolve())
            _emit(CLIResponse(ok=True, data=info), as_json)
        except Exception as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)

    @doc_app.command("get")
    def doc_get(
        path: Annotated[Path, typer.Argument(help="Path to .pptx file.")],
        index: Annotated[
            int, typer.Option("--index", help="Zero-based slide index.")
        ],
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """Read a slide's stored spec (grid classes, cells, frame info)."""
        _require_file(path, as_json)
        try:
            prs = document.open_document(path)
            slide_data = document.get_slide_info(prs, index)
            _emit(CLIResponse(ok=True, data=slide_data), as_json)
        except Exception as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)

    # --- slide-level builder --------------------------------------------

    @slide_app.command("new")
    def slide_new(
        path: Annotated[Path, typer.Argument(help="Path to .pptx file.")],
        grid: Annotated[
            str,
            typer.Option(
                "--grid",
                help="Grid classes, e.g. 'grid-cols-[2_1] grid-rows-2 gap-4'.",
            ),
        ] = "",
        frame: Annotated[
            str | None,
            typer.Option(
                "--frame", help="Page frame id (requires doc created with --brand)."
            ),
        ] = None,
        set_pairs: Annotated[
            list[str],
            typer.Option(
                "--set",
                help="Frame info field as key=value (repeatable), e.g. title=Quarterly Review.",
            ),
        ] = [],
        at: Annotated[
            int | None,
            typer.Option("--at", help="Insert at index (default: append)."),
        ] = None,
        rtl: Annotated[
            bool | None,
            typer.Option("--rtl/--no-rtl", help="Override document RTL for this slide."),
        ] = None,
        locale: Annotated[
            str | None,
            typer.Option("--locale", help="Override document locale for this slide."),
        ] = None,
        output: Annotated[Path | None, typer.Option("-o", "--output")] = None,
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """Create an empty grid slide, then populate it with 'el add'."""
        _require_file(path, as_json)
        try:
            info_model = _resolve_frame_input(frame)
            frame_info = (
                _build_model_data(info_model, set_pairs) if set_pairs else None
            )
            prs = document.open_document(path)
            result = document.new_grid_slide(
                prs,
                grid=grid,
                frame=frame,
                frame_info=frame_info,
                at=at,
                rtl=rtl,
                locale=locale,
            )
            save_path = _resolve_output(path, output)
            document.save_document(prs, save_path)
            result["path"] = str(save_path.resolve())
            _emit(CLIResponse(ok=True, data=result), as_json)
        except Exception as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)

    @slide_app.command("add")
    def slide_add(
        path: Annotated[Path, typer.Argument(help="Path to .pptx file.")],
        template_id: Annotated[
            str | None, typer.Option("--template", "-t", help="Registered template id.")
        ] = None,
        set_pairs: Annotated[
            list[str],
            typer.Option(
                "--set",
                help="Field as key=value (repeatable). Use cell.prop for nested element props.",
            ),
        ] = [],
        at: Annotated[
            int | None, typer.Option("--at", help="Insert at index (default: append).")
        ] = None,
        frame: Annotated[
            str | None,
            typer.Option(
                "--frame",
                help="Page frame id (requires doc --brand). With no --template, adds a frame-only slide.",
            ),
        ] = None,
        rtl: Annotated[bool | None, typer.Option("--rtl/--no-rtl")] = None,
        locale: Annotated[str | None, typer.Option("--locale")] = None,
        output: Annotated[Path | None, typer.Option("-o", "--output")] = None,
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """Add a slide from a template or a frame-only slide (cover/closing)."""
        _require_file(path, as_json)
        if not template_id and not frame:
            _emit(
                CLIResponse(ok=False, error="Provide --template or --frame."),
                as_json,
                exit_code=1,
            )
            return
        try:
            data_model = _resolve_slide_data_model(template_id, frame)
            if template_id:
                build_data = _build_nested_model_data
            else:
                build_data = _build_model_data
            data = build_data(data_model, set_pairs)
            prs = document.open_document(path)
            if template_id:
                result = document.add_slide(
                    prs, template_id, data, at=at, frame=frame, rtl=rtl, locale=locale
                )
            else:
                result = document.add_frame_slide(
                    prs, frame, data, at=at, rtl=rtl, locale=locale
                )
            save_path = _resolve_output(path, output)
            document.save_document(prs, save_path)
            result["path"] = str(save_path.resolve())
            _emit(CLIResponse(ok=True, data=result), as_json)
        except Exception as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)

    @slide_app.command("set")
    def slide_set(
        path: Annotated[Path, typer.Argument(help="Path to .pptx file.")],
        index: Annotated[int, typer.Option("--index", help="Zero-based slide index.")],
        grid: Annotated[
            str | None, typer.Option("--grid", help="Replace the grid classes.")
        ] = None,
        frame: Annotated[
            str | None, typer.Option("--frame", help="Switch the page frame.")
        ] = None,
        set_pairs: Annotated[
            list[str],
            typer.Option(
                "--set",
                help="Frame info field as key=value (repeatable). Merges with existing frame info.",
            ),
        ] = [],
        rtl: Annotated[bool | None, typer.Option("--rtl/--no-rtl")] = None,
        locale: Annotated[str | None, typer.Option("--locale")] = None,
        output: Annotated[Path | None, typer.Option("-o", "--output")] = None,
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """Update slide-level settings (grid, frame, frame info) in place."""
        _require_file(path, as_json)
        kwargs: dict[str, Any] = {"frame": frame, "rtl": rtl, "locale": locale}
        if grid is not None:
            kwargs["grid"] = grid
        try:
            prs = document.open_document(path)
            if set_pairs:
                info_model = _grid_slide_frame_input(prs, index, frame)
                kwargs["frame_info"] = _build_model_data(info_model, set_pairs)
            result = document.set_slide(prs, index, **kwargs)
            save_path = _resolve_output(path, output)
            document.save_document(prs, save_path)
            result["path"] = str(save_path.resolve())
            _emit(CLIResponse(ok=True, data=result), as_json)
        except Exception as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)

    @slide_app.command("rm")
    def slide_rm(
        path: Annotated[Path, typer.Argument(help="Path to .pptx file.")],
        index: Annotated[
            int, typer.Option("--index", help="Zero-based slide index to delete.")
        ],
        output: Annotated[Path | None, typer.Option("-o", "--output")] = None,
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """Remove a slide from a presentation."""
        _require_file(path, as_json)
        try:
            prs = document.open_document(path)
            document.remove_slide(prs, index)
            save_path = _resolve_output(path, output)
            document.save_document(prs, save_path)
            _emit(
                CLIResponse(
                    ok=True,
                    data={"path": str(save_path.resolve()), "removed_index": index},
                ),
                as_json,
            )
        except Exception as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)

    # --- element-level builder ------------------------------------------

    @el_app.command("add")
    def el_add(
        path: Annotated[Path, typer.Argument(help="Path to .pptx file.")],
        index: Annotated[
            int, typer.Option("--index", help="Zero-based grid slide index.")
        ],
        kind: Annotated[
            str, typer.Option("--kind", help="Element kind (see 'elements list').")
        ],
        at: Annotated[
            str,
            typer.Option("--at", help="Cell placement classes, e.g. 'col-span-2'."),
        ] = "",
        set_props: Annotated[
            list[str] | None,
            typer.Option("--set", help="Element prop as key=value (repeatable)."),
        ] = None,
        output: Annotated[Path | None, typer.Option("-o", "--output")] = None,
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """Append an element to a grid slide cell."""
        _require_file(path, as_json)
        try:
            element = factory.get_element(kind)
            props = _build_props(element.props_model, set_props or [])
            prs = document.open_document(path)
            result = document.add_cell(
                prs, index, kind=kind, at=at, props=props
            )
            save_path = _resolve_output(path, output)
            document.save_document(prs, save_path)
            result["path"] = str(save_path.resolve())
            _emit(CLIResponse(ok=True, data=result), as_json)
        except Exception as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)

    @el_app.command("set")
    def el_set(
        path: Annotated[Path, typer.Argument(help="Path to .pptx file.")],
        index: Annotated[
            int, typer.Option("--index", help="Zero-based grid slide index.")
        ],
        cell: Annotated[
            int, typer.Option("--cell", help="Zero-based cell index to update.")
        ],
        kind: Annotated[
            str | None, typer.Option("--kind", help="Change the element kind.")
        ] = None,
        at: Annotated[
            str | None, typer.Option("--at", help="Replace cell placement classes.")
        ] = None,
        set_props: Annotated[
            list[str] | None,
            typer.Option("--set", help="Replace props as key=value (repeatable)."),
        ] = None,
        output: Annotated[Path | None, typer.Option("-o", "--output")] = None,
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """Update one cell's element (kind, placement, or props)."""
        _require_file(path, as_json)
        kwargs: dict[str, Any] = {}
        if kind is not None:
            kwargs["kind"] = kind
        if at is not None:
            kwargs["at"] = at
        try:
            prs = document.open_document(path)
            if set_props is not None:
                resolved_kind = kind or _current_cell_kind(prs, index, cell)
                model = factory.get_element(resolved_kind).props_model
                kwargs["props"] = _build_props(model, set_props)
            result = document.set_cell(prs, index, cell, **kwargs)
            save_path = _resolve_output(path, output)
            document.save_document(prs, save_path)
            result["path"] = str(save_path.resolve())
            _emit(CLIResponse(ok=True, data=result), as_json)
        except Exception as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)

    @el_app.command("rm")
    def el_rm(
        path: Annotated[Path, typer.Argument(help="Path to .pptx file.")],
        index: Annotated[
            int, typer.Option("--index", help="Zero-based grid slide index.")
        ],
        cell: Annotated[
            int, typer.Option("--cell", help="Zero-based cell index to remove.")
        ],
        output: Annotated[Path | None, typer.Option("-o", "--output")] = None,
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """Remove one cell's element from a grid slide."""
        _require_file(path, as_json)
        try:
            prs = document.open_document(path)
            result = document.remove_cell(prs, index, cell)
            save_path = _resolve_output(path, output)
            document.save_document(prs, save_path)
            result["path"] = str(save_path.resolve())
            _emit(CLIResponse(ok=True, data=result), as_json)
        except Exception as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)

    @app.command(
        "preview",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
        help="Launch the Streamlit preview app.",
    )
    def preview_cmd(
        ctx: typer.Context,
        brand: Annotated[
            Path | None,
            typer.Option("--brand", help="Brand YAML path (overrides factory default)."),
        ] = None,
    ) -> None:
        """Start the visual preview in Streamlit."""
        from slides_factory.preview.run import run_preview

        try:
            exit_code = run_preview(
                impl_module=factory.preview_impl_module,
                brand_path=brand or factory.preview_brand,
                page_title=factory.preview_page_title,
                extra_args=list(ctx.args),
            )
        except RuntimeError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=1) from exc
        raise typer.Exit(code=exit_code)

    return app
