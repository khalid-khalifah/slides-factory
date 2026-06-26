"""Streamlit UI for visually previewing slide templates."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from slides_factory.preview.forms import render_template_form, validate_form_values
from slides_factory.preview.frames import frame_for_template
from slides_factory.preview.reload import (
    AUTO_RELOAD_INTERVAL,
    changed_files,
    file_mtimes,
    format_reload_notice,
    reload_changed_sources,
    watch_paths_for_preview,
)
from slides_factory.preview.render import pptx_bytes_to_pngs, render_preview_pptx

if TYPE_CHECKING:
    from slides_factory.app import SlideFactory


def _render_preview_to_session(
    *,
    app: SlideFactory,
    template_id: str,
    input_model: type,
    form_values: dict[str, Any],
    brand_path: Path | None,
    frame_id: str | None,
    rtl: bool,
    locale: str,
    session: Any,
) -> None:
    """Validate form data, render slide bytes, and store PNG preview in session."""
    validated = validate_form_values(input_model, form_values)
    data = validated.model_dump(mode="json")
    pptx_bytes = render_preview_pptx(
        template_id,
        data,
        app=app,
        brand=brand_path,
        frame=frame_id if brand_path else None,
        rtl=rtl,
        locale=locale,
    )
    session.preview_pptx = pptx_bytes
    session.preview_pngs = pptx_bytes_to_pngs(pptx_bytes)
    session.preview_error = None
    session.has_rendered_once = True


def run_preview_app(
    factory: "SlideFactory",
    *,
    brand_path: Path | None = None,
    page_title: str | None = None,
) -> None:
    """Render the template preview Streamlit application."""
    import streamlit as st

    title = page_title or f"{factory.name} Template Preview"
    st.set_page_config(page_title=title, layout="wide")
    st.title(title)
    st.caption(
        "Pick a template and frame, fill in the fields, and render a live slide preview. "
        "With **Auto-reload on save** enabled, editing template or frame `.py` files "
        "refreshes the preview automatically."
    )

    templates = sorted(factory.list_templates(), key=lambda tpl: tpl.name)
    frames = sorted(factory.list_frames(), key=lambda frame: frame.name)
    template_ids = [tpl.id for tpl in templates]
    frame_ids = [frame.id for frame in frames]
    brand_default_frame = frames[0].id if frames else None
    if brand_path is not None:
        from slides_factory.brand import load_brand

        brand_default_frame = load_brand(brand_path).default_frame or brand_default_frame

    def _frame_for_template(tpl) -> str | None:
        return frame_for_template(
            tpl,
            available_frame_ids=frame_ids,
            brand_default_frame=brand_default_frame,
        )

    def _apply_template_selection(tpl_id: str) -> None:
        st.session_state.template_id = tpl_id
        st.session_state.last_template_id = tpl_id
        if brand_path is not None and frame_ids:
            st.session_state.frame_id = _frame_for_template(factory.get_template(tpl_id))
        for key in list(st.session_state.keys()):
            if key.startswith("form:") or key.startswith("upload:"):
                del st.session_state[key]
        st.session_state.watch_mtimes = {}

    if "template_id" not in st.session_state:
        st.session_state.template_id = template_ids[0]
    if "frame_id" not in st.session_state:
        first_tpl = factory.get_template(st.session_state.template_id)
        st.session_state.frame_id = _frame_for_template(first_tpl)
    if "locale" not in st.session_state:
        st.session_state.locale = "en"
    if "last_template_id" not in st.session_state:
        st.session_state.last_template_id = st.session_state.template_id
    if "auto_reload" not in st.session_state:
        st.session_state.auto_reload = True

    with st.sidebar:
        st.header("Catalog")
        template_labels = {tpl.id: f"{tpl.name} ({tpl.id})" for tpl in templates}
        selected_template_id = st.selectbox(
            "Template",
            template_ids,
            index=template_ids.index(st.session_state.template_id),
            format_func=lambda tid: template_labels[tid],
        )
        if selected_template_id != st.session_state.template_id:
            _apply_template_selection(selected_template_id)
            st.rerun()

        selected_template = factory.get_template(st.session_state.template_id)
        st.write(selected_template.description or "_No description_")

        if brand_path is not None and frame_ids:
            frame_labels = {frame.id: f"{frame.name} ({frame.id})" for frame in frames}
            frame_index = (
                frame_ids.index(st.session_state.frame_id)
                if st.session_state.frame_id in frame_ids
                else 0
            )
            st.session_state.frame_id = st.selectbox(
                "Frame",
                frame_ids,
                index=frame_index,
                format_func=lambda fid: frame_labels[fid],
            )
            if st.session_state.frame_id != st.session_state.get("last_frame_id"):
                st.session_state.last_frame_id = st.session_state.frame_id
                st.session_state.watch_mtimes = {}
        elif frame_ids:
            st.info("Provide `brand_path` to preview branded frames.")

        st.session_state.locale = st.selectbox(
            "Locale",
            ["en", "ar"],
            index=0 if st.session_state.locale == "en" else 1,
        )
        rtl_default = st.session_state.locale == "ar"
        rtl = st.checkbox("RTL layout", value=rtl_default)

        st.divider()
        st.session_state.auto_reload = st.checkbox(
            "Auto-reload on save",
            value=st.session_state.auto_reload,
            help=(
                "Watch the current template, frame, render helpers, and brand YAML. "
                f"Poll every {AUTO_RELOAD_INTERVAL.seconds:g}s and refresh the preview "
                "after you save a file."
            ),
        )

        st.divider()
        st.subheader("All templates")
        for tpl in templates:
            if st.button(tpl.name, key=f"pick-{tpl.id}", use_container_width=True):
                if tpl.id != st.session_state.template_id:
                    _apply_template_selection(tpl.id)
                st.rerun()

    col_form, col_preview = st.columns([1, 1], gap="large")

    with col_form:
        st.subheader("Slide data")
        form_values = render_template_form(
            st.session_state.template_id,
            selected_template.input_model,
            st.session_state,
            st,
        )

        with st.expander("JSON schema"):
            st.json(selected_template.get_json_schema())

        render_clicked = st.button("Render preview", type="primary", use_container_width=True)

    watch_paths_for_preview(
        factory,
        template_id=st.session_state.template_id,
        frame_id=st.session_state.frame_id if brand_path else None,
        brand_path=brand_path,
    )

    if st.session_state.get("pending_auto_rerender"):
        st.session_state.pending_auto_rerender = False
        try:
            _render_preview_to_session(
                app=factory,
                template_id=st.session_state.template_id,
                input_model=selected_template.input_model,
                form_values=form_values,
                brand_path=brand_path,
                frame_id=st.session_state.frame_id if brand_path else None,
                rtl=rtl,
                locale=st.session_state.locale,
                session=st.session_state,
            )
        except Exception as exc:
            st.session_state.preview_error = str(exc)
            st.session_state.preview_pptx = None
            st.session_state.preview_pngs = []

    with col_preview:
        st.subheader("Preview")

        notice = st.session_state.pop("reload_notice", None)
        if notice:
            st.success(f"Reloaded {notice}")

        if render_clicked:
            try:
                _render_preview_to_session(
                    app=factory,
                    template_id=st.session_state.template_id,
                    input_model=selected_template.input_model,
                    form_values=form_values,
                    brand_path=brand_path,
                    frame_id=st.session_state.frame_id if brand_path else None,
                    rtl=rtl,
                    locale=st.session_state.locale,
                    session=st.session_state,
                )
            except Exception as exc:
                st.session_state.preview_error = str(exc)
                st.session_state.preview_pptx = None
                st.session_state.preview_pngs = []

        if st.session_state.get("preview_error"):
            st.error(st.session_state.preview_error)

        pptx_bytes = st.session_state.get("preview_pptx")
        if pptx_bytes is None and not render_clicked:
            st.info("Click **Render preview** to generate a slide.")
        else:
            pngs = st.session_state.get("preview_pngs") or []
            if pngs:
                st.image(pngs[0], use_container_width=True)
            elif pptx_bytes:
                st.warning(
                    "Install LibreOffice to see a PNG preview. "
                    "You can still download the .pptx below."
                )

        if pptx_bytes:
            frame_suffix = f"-{st.session_state.frame_id}" if brand_path else ""
            filename = (
                f"{st.session_state.template_id}{frame_suffix}-{st.session_state.locale}.pptx"
            )
            st.download_button(
                "Download .pptx",
                data=pptx_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                use_container_width=True,
            )

    if st.session_state.auto_reload:

        @st.fragment(run_every=AUTO_RELOAD_INTERVAL)
        def _auto_reload_watcher() -> None:
            paths = watch_paths_for_preview(
                factory,
                template_id=st.session_state.template_id,
                frame_id=st.session_state.frame_id if brand_path else None,
                brand_path=brand_path,
            )
            if "watch_mtimes" not in st.session_state:
                st.session_state.watch_mtimes = file_mtimes(paths)
                return

            changed = changed_files(st.session_state.watch_mtimes, paths)
            if not changed:
                return

            py_changed = [path for path in changed if path.suffix == ".py"]
            try:
                if py_changed:
                    reload_changed_sources(factory, py_changed)
            except Exception as exc:
                st.session_state.preview_error = f"Auto-reload failed: {exc}"
                st.session_state.watch_mtimes = file_mtimes(paths)
                st.rerun()
                return

            st.session_state.watch_mtimes = file_mtimes(paths)
            st.session_state.reload_notice = format_reload_notice(changed)
            if st.session_state.get("has_rendered_once"):
                st.session_state.pending_auto_rerender = True
            st.rerun()

        _auto_reload_watcher()
