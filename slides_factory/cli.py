"""Typer CLI wired to a SlideFactory instance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer

from slides_factory import document
from slides_factory.brand import load_brand
from slides_factory.models import CLIResponse

if TYPE_CHECKING:
    from slides_factory.app import SlideFactory


def build_cli(factory: "SlideFactory") -> typer.Typer:
    app = typer.Typer(name=factory.name, help=factory.help, no_args_is_help=True)
    templates_app = typer.Typer(help="Browse and inspect slide templates.")
    frames_app = typer.Typer(help="Browse page frame templates.")
    brand_app = typer.Typer(help="Inspect brand YAML themes.")
    doc_app = typer.Typer(help="Create and inspect presentations.")
    slide_app = typer.Typer(help="Add, edit, and remove slides.")

    app.add_typer(templates_app, name="templates")
    app.add_typer(frames_app, name="frames")
    app.add_typer(brand_app, name="brand")
    app.add_typer(doc_app, name="doc")
    app.add_typer(slide_app, name="slide")

    def _emit(response: CLIResponse, as_json: bool, exit_code: int = 0) -> None:
        response.print(as_json)
        if not response.ok:
            raise typer.Exit(code=exit_code)

    def _load_json_data(
        data_path: Path | None, data_inline: str | None
    ) -> dict[str, Any]:
        if data_path and data_inline:
            raise typer.BadParameter("Use either --data or --data-json, not both.")
        if data_path:
            return json.loads(data_path.read_text(encoding="utf-8"))
        if data_inline:
            return json.loads(data_inline)
        raise typer.BadParameter(
            "Provide slide content via --data <file.json> or --data-json '{...}'."
        )

    def _resolve_output(path: Path, output: Path | None) -> Path:
        return output if output else path

    def _template_summary(template) -> dict[str, Any]:
        schema = template.get_json_schema()
        field_count = len(schema.get("properties", {}))
        cls = type(template)
        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "tags": list(cls.tags),
            "default_frame": cls.default_frame,
            "field_count": field_count,
        }

    @templates_app.command("list")
    def templates_list(
        tag: Annotated[
            str | None,
            typer.Option("--tag", help="Filter templates that include this tag."),
        ] = None,
        as_json: Annotated[
            bool, typer.Option("--json", help="Machine-readable JSON output.")
        ] = False,
    ) -> None:
        """List all registered slide templates."""
        items = [_template_summary(template) for template in factory.list_templates(tag=tag)]
        items.sort(key=lambda item: item["id"])
        data: dict[str, Any] = {"templates": items, "count": len(items)}
        if tag is not None:
            data["tag"] = tag
        _emit(CLIResponse(ok=True, data=data), as_json)

    @templates_app.command("tags")
    def templates_tags(
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """List all template tags with usage counts."""
        counts: dict[str, int] = {}
        for template in factory.list_templates():
            for tag in type(template).tags:
                counts[tag] = counts.get(tag, 0) + 1
        items = [
            {"tag": tag, "count": counts[tag]}
            for tag in sorted(counts)
        ]
        _emit(
            CLIResponse(ok=True, data={"tags": items, "count": len(items)}),
            as_json,
        )

    @templates_app.command("inspect")
    def templates_inspect(
        template_id: Annotated[
            str, typer.Argument(help="Template id, e.g. 'bullets'.")
        ],
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """Show JSON schema and layout info for a template."""
        try:
            template = factory.get_template(template_id)
        except KeyError as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)

        cls = type(template)
        _emit(
            CLIResponse(
                ok=True,
                data={
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "tags": list(cls.tags),
                    "default_frame": cls.default_frame,
                    "layout_name": cls.layout_name,
                    "json_schema": template.get_json_schema(),
                },
            ),
            as_json,
        )

    @templates_app.command("search")
    def templates_search(
        query: Annotated[
            str, typer.Argument(help="Search term for id, name, or description.")
        ],
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """Search the template catalog."""
        matches = factory.search_templates(query)
        items = [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "tags": list(type(t).tags),
                "default_frame": type(t).default_frame,
            }
            for t in matches
        ]
        _emit(
            CLIResponse(
                ok=True,
                data={"query": query, "matches": items, "count": len(matches)},
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
        if not path.exists():
            _emit(
                CLIResponse(ok=False, error=f"File not found: {path}"),
                as_json,
                exit_code=1,
            )
        try:
            theme = load_brand(path)
            _emit(
                CLIResponse(
                    ok=True,
                    data={
                        "path": str(path.resolve()),
                        "name": theme.name,
                        "default_frame": theme.default_frame,
                        "base_pptx": (
                            str(theme.resolve_base_pptx())
                            if theme.base_pptx
                            else None
                        ),
                        "page": theme.page.model_dump(),
                        "layout": theme.layout.model_dump(),
                        "colors": theme.colors.model_dump(),
                        "fonts": theme.fonts.model_dump(),
                        "logos": {
                            k: str(theme.resolve_logo(k)) for k in theme.logos
                        },
                    },
                ),
                as_json,
            )
        except Exception as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)

    @doc_app.command("create")
    def doc_create(
        output: Annotated[
            Path, typer.Option("-o", "--output", help="Output .pptx path.")
        ],
        theme: Annotated[
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
            document.create_document(output, theme, brand=brand, rtl=rtl, locale=locale)
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
        if not path.exists():
            _emit(
                CLIResponse(ok=False, error=f"File not found: {path}"),
                as_json,
                exit_code=1,
            )
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
        """List slides in a presentation with template summaries."""
        if not path.exists():
            _emit(
                CLIResponse(ok=False, error=f"File not found: {path}"),
                as_json,
                exit_code=1,
            )
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
        """Read a slide's template id and JSON content."""
        if not path.exists():
            _emit(
                CLIResponse(ok=False, error=f"File not found: {path}"),
                as_json,
                exit_code=1,
            )
        try:
            prs = document.open_document(path)
            slide_data = document.get_slide_info(prs, index)
            _emit(CLIResponse(ok=True, data=slide_data), as_json)
        except Exception as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)

    @slide_app.command("add")
    def slide_add(
        path: Annotated[Path, typer.Argument(help="Path to .pptx file.")],
        template_id: Annotated[
            str, typer.Option("--template", "-t", help="Template id.")
        ],
        data_file: Annotated[
            Path | None,
            typer.Option("--data", help="JSON file with slide content."),
        ] = None,
        data_json: Annotated[
            str | None,
            typer.Option("--data-json", help="Inline JSON string with slide content."),
        ] = None,
        at: Annotated[
            int | None,
            typer.Option("--at", help="Insert at index (default: append)."),
        ] = None,
        output: Annotated[
            Path | None,
            typer.Option("-o", "--output", help="Save to a different file."),
        ] = None,
        locale: Annotated[
            str | None,
            typer.Option(
                "--locale", help="Override document language tag for this slide."
            ),
        ] = None,
        rtl: Annotated[
            bool | None,
            typer.Option(
                "--rtl/--no-rtl", help="Override document RTL setting for this slide."
            ),
        ] = None,
        frame: Annotated[
            str | None,
            typer.Option(
                "--frame", help="Page frame id (requires doc created with --brand)."
            ),
        ] = None,
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """Add a slide to a presentation."""
        if not path.exists():
            _emit(
                CLIResponse(ok=False, error=f"File not found: {path}"),
                as_json,
                exit_code=1,
            )
        try:
            data = _load_json_data(data_file, data_json)
            prs = document.open_document(path)
            result = document.add_slide(
                prs, template_id, data, at=at, frame=frame, rtl=rtl, locale=locale
            )
            save_path = _resolve_output(path, output)
            document.save_document(prs, save_path)
            result["path"] = str(save_path.resolve())
            _emit(CLIResponse(ok=True, data=result), as_json)
        except Exception as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)

    @slide_app.command("edit")
    def slide_edit(
        path: Annotated[Path, typer.Argument(help="Path to .pptx file.")],
        index: Annotated[
            int, typer.Option("--index", help="Zero-based slide index to replace.")
        ],
        data_file: Annotated[Path | None, typer.Option("--data")] = None,
        data_json: Annotated[str | None, typer.Option("--data-json")] = None,
        template_id: Annotated[
            str | None,
            typer.Option("--template", "-t", help="Optional new template id."),
        ] = None,
        output: Annotated[Path | None, typer.Option("-o", "--output")] = None,
        locale: Annotated[
            str | None,
            typer.Option(
                "--locale", help="Override document language tag for this slide."
            ),
        ] = None,
        rtl: Annotated[
            bool | None,
            typer.Option(
                "--rtl/--no-rtl", help="Override document RTL setting for this slide."
            ),
        ] = None,
        frame: Annotated[
            str | None,
            typer.Option(
                "--frame", help="Page frame id (requires doc created with --brand)."
            ),
        ] = None,
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """Replace a slide's content (and optionally its template)."""
        if not path.exists():
            _emit(
                CLIResponse(ok=False, error=f"File not found: {path}"),
                as_json,
                exit_code=1,
            )
        try:
            data = _load_json_data(data_file, data_json)
            prs = document.open_document(path)
            result = document.edit_slide(
                prs,
                index,
                data,
                template_id=template_id,
                frame=frame,
                rtl=rtl,
                locale=locale,
            )
            save_path = _resolve_output(path, output)
            document.save_document(prs, save_path)
            result["path"] = str(save_path.resolve())
            _emit(CLIResponse(ok=True, data=result), as_json)
        except Exception as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)

    @slide_app.command("remove")
    def slide_remove(
        path: Annotated[Path, typer.Argument(help="Path to .pptx file.")],
        index: Annotated[
            int, typer.Option("--index", help="Zero-based slide index to delete.")
        ],
        output: Annotated[Path | None, typer.Option("-o", "--output")] = None,
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """Remove a slide from a presentation."""
        if not path.exists():
            _emit(
                CLIResponse(ok=False, error=f"File not found: {path}"),
                as_json,
                exit_code=1,
            )
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

    @slide_app.command("validate")
    def slide_validate(
        template_id: Annotated[str, typer.Option("--template", "-t")],
        data_file: Annotated[Path | None, typer.Option("--data")] = None,
        data_json: Annotated[str | None, typer.Option("--data-json")] = None,
        as_json: Annotated[bool, typer.Option("--json")] = False,
    ) -> None:
        """Validate slide JSON against a template schema without modifying a file."""
        try:
            data = _load_json_data(data_file, data_json)
            template = factory.get_template(template_id)
            validated = template.validate_data(data)
            _emit(
                CLIResponse(
                    ok=True,
                    data={
                        "template_id": template_id,
                        "valid": True,
                        "data": validated.model_dump(mode="json"),
                    },
                ),
                as_json,
            )
        except Exception as exc:
            _emit(CLIResponse(ok=False, error=str(exc)), as_json, exit_code=1)

    @app.command(
        "preview",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
        help="Launch the Streamlit template preview app.",
    )
    def preview_cmd(
        ctx: typer.Context,
        brand: Annotated[
            Path | None,
            typer.Option("--brand", help="Brand YAML path (overrides factory default)."),
        ] = None,
    ) -> None:
        """Start the visual template preview in Streamlit."""
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
