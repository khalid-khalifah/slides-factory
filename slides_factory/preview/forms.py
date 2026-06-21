"""Auto-generated Streamlit forms from TemplateInput Pydantic models."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from slides_factory.template_input import TemplateInput
from slides_factory.typing_utils import unwrap_optional_annotation

_LONG_TEXT_FIELDS = frozenset({"body", "quote", "subtitle", "attribution", "heading"})


def _list_inner(annotation: Any) -> Any | None:
    annotation, _ = unwrap_optional_annotation(annotation)
    if get_origin(annotation) is list:
        args = get_args(annotation)
        return args[0] if args else str
    return None


def _is_model_type(annotation: Any) -> type[BaseModel] | None:
    annotation, _ = unwrap_optional_annotation(annotation)
    if (
        isinstance(annotation, type)
        and issubclass(annotation, BaseModel)
        and not issubclass(annotation, TemplateInput)
    ):
        return annotation
    return None


def _field_description(field_name: str, field_info: FieldInfo) -> str:
    if field_info.description:
        return field_info.description
    return field_name.replace("_", " ").title()


def _scalar_default(annotation: Any, optional: bool) -> Any:
    if optional:
        return None
    if annotation is str:
        return ""
    if annotation is int:
        return 0
    if annotation is float:
        return 0.0
    if annotation is bool:
        return False
    return None


def _field_default(model: type[TemplateInput], field_name: str, field_info: FieldInfo) -> Any:
    if not field_info.is_required():
        if field_info.default_factory is not None:
            return field_info.default_factory()
        return field_info.default
    inner = _list_inner(field_info.annotation)
    if inner is not None:
        return []
    annotation, optional = unwrap_optional_annotation(field_info.annotation)
    return _scalar_default(annotation, optional)


def default_form_values(model: type[TemplateInput]) -> dict[str, Any]:
    """Return default values for every field on a TemplateInput model."""
    values: dict[str, Any] = {}
    for name, field_info in model.model_fields.items():
        default = _field_default(model, name, field_info)
        inner = _list_inner(field_info.annotation)
        if inner is not None:
            if default is None:
                values[name] = []
            elif isinstance(default, list):
                values[name] = list(default)
            else:
                values[name] = []
        else:
            values[name] = default
    return values


def validate_form_values(model: type[TemplateInput], values: dict[str, Any]) -> TemplateInput:
    """Validate a raw form dict through the TemplateInput model."""
    return model.model_validate(values)


def _count_key(template_id: str, field_name: str) -> str:
    return f"form:{template_id}:{field_name}:count"


def _item_key(template_id: str, field_name: str, index: int, subfield: str = "") -> str:
    suffix = f":{subfield}" if subfield else ""
    return f"form:{template_id}:{field_name}:{index}{suffix}"


def init_form_state(template_id: str, model: type[TemplateInput], state: Any) -> None:
    """Initialize session state for a template form."""
    defaults = default_form_values(model)
    state.setdefault("active_form_template", template_id)
    if state.get("active_form_template") != template_id:
        state.active_form_template = template_id
        for key in list(state.keys()):
            if key.startswith(f"form:{template_id}:") or key.startswith(f"upload:{template_id}:"):
                del state[key]

    for name, field_info in model.model_fields.items():
        inner = _list_inner(field_info.annotation)
        if inner is not None:
            default_list = defaults.get(name) or []
            count_key = _count_key(template_id, name)
            if count_key not in state:
                state[count_key] = max(len(default_list), 1 if inner is str else 0)
            for index, item in enumerate(default_list):
                nested = _is_model_type(inner)
                if nested is not None and isinstance(item, BaseModel):
                    for sub_name in nested.model_fields:
                        state.setdefault(
                            _item_key(template_id, name, index, sub_name),
                            getattr(item, sub_name),
                        )
                elif nested is None:
                    state.setdefault(_item_key(template_id, name, index), item)
        else:
            annotation, optional = unwrap_optional_annotation(field_info.annotation)
            nested = _is_model_type(annotation)
            if nested is not None:
                default_obj = defaults.get(name)
                if isinstance(default_obj, BaseModel):
                    for sub_name in nested.model_fields:
                        state.setdefault(
                            f"form:{template_id}:{name}:{sub_name}",
                            getattr(default_obj, sub_name),
                        )
                else:
                    for sub_name, sub_info in nested.model_fields.items():
                        state.setdefault(
                            f"form:{template_id}:{name}:{sub_name}",
                            _field_default(nested, sub_name, sub_info),
                        )
            elif annotation is bool:
                state.setdefault(f"form:{template_id}:{name}", bool(defaults.get(name)))
            elif optional and defaults.get(name) is None:
                state.setdefault(f"form:{template_id}:{name}", "")
            else:
                state.setdefault(f"form:{template_id}:{name}", defaults.get(name, ""))


def _render_scalar_field(
    template_id: str,
    field_name: str,
    field_info: FieldInfo,
    state: Any,
    st: Any,
) -> Any:
    annotation, optional = unwrap_optional_annotation(field_info.annotation)
    label = _field_description(field_name, field_info)
    key = f"form:{template_id}:{field_name}"

    if annotation is bool:
        return st.checkbox(label, key=key)

    if annotation in (int, float):
        value = state.get(key, 0)
        if annotation is int:
            return st.number_input(label, value=int(value or 0), step=1, key=key)
        return st.number_input(label, value=float(value or 0), key=key)

    use_text_area = field_name in _LONG_TEXT_FIELDS or (
        field_info.description
        and any(word in field_info.description.lower() for word in ("body", "quote", "text beside"))
    )
    if use_text_area:
        return st.text_area(label, key=key)

    value = st.text_input(label, key=key)
    if optional and value == "":
        return None
    return value


def _render_string_list(
    template_id: str,
    field_name: str,
    field_info: FieldInfo,
    state: Any,
    st: Any,
) -> list[str]:
    label = _field_description(field_name, field_info)
    count_key = _count_key(template_id, field_name)
    count = state[count_key]
    st.markdown(f"**{label}**")
    items: list[str] = []
    for index in range(count):
        col_input, col_remove = st.columns([6, 1])
        with col_input:
            value = st.text_input(
                f"{label} {index + 1}",
                key=_item_key(template_id, field_name, index),
                label_visibility="collapsed",
            )
            items.append(value)
        with col_remove:
            if st.button("×", key=f"rm:{template_id}:{field_name}:{index}"):
                state[count_key] = max(count - 1, 0)
                st.rerun()
    if st.button(f"+ Add {label.lower()}", key=f"add:{template_id}:{field_name}"):
        state[count_key] = count + 1
        st.rerun()
    return [item for item in items if item != ""]


def _render_int_list(
    template_id: str,
    field_name: str,
    field_info: FieldInfo,
    state: Any,
    st: Any,
) -> list[int] | None:
    annotation, optional = unwrap_optional_annotation(field_info.annotation)
    label = _field_description(field_name, field_info)
    count_key = _count_key(template_id, field_name)
    count = state[count_key]
    st.markdown(f"**{label}**")
    items: list[int] = []
    for index in range(count):
        col_input, col_remove = st.columns([6, 1])
        with col_input:
            value = st.number_input(
                f"{label} {index + 1}",
                step=1,
                key=_item_key(template_id, field_name, index),
                label_visibility="collapsed",
            )
            items.append(int(value))
        with col_remove:
            if st.button("×", key=f"rm:{template_id}:{field_name}:{index}"):
                state[count_key] = max(count - 1, 0)
                st.rerun()
    if st.button(f"+ Add {label.lower()}", key=f"add:{template_id}:{field_name}"):
        state[count_key] = count + 1
        st.rerun()
    if not items:
        return None if optional else []
    return items


def _render_model_object(
    template_id: str,
    field_name: str,
    field_info: FieldInfo,
    nested_model: type[BaseModel],
    state: Any,
    st: Any,
) -> dict[str, Any]:
    label = _field_description(field_name, field_info)
    st.markdown(f"**{label}**")
    values: dict[str, Any] = {}
    for sub_name, sub_info in nested_model.model_fields.items():
        sub_label = _field_description(sub_name, sub_info)
        inner = _list_inner(sub_info.annotation)
        if inner is not None and inner is str:
            count_key = _count_key(template_id, f"{field_name}:{sub_name}")
            if count_key not in state:
                state[count_key] = 1
            count = state[count_key]
            items: list[str] = []
            for index in range(count):
                col_input, col_remove = st.columns([6, 1])
                with col_input:
                    value = st.text_input(
                        f"{sub_label} {index + 1}",
                        key=_item_key(template_id, f"{field_name}:{sub_name}", index),
                        label_visibility="collapsed",
                    )
                    items.append(value)
                with col_remove:
                    if st.button("×", key=f"rm:{template_id}:{field_name}:{sub_name}:{index}"):
                        state[count_key] = max(count - 1, 0)
                        st.rerun()
            if st.button(
                f"+ Add {sub_label.lower()}", key=f"add:{template_id}:{field_name}:{sub_name}"
            ):
                state[count_key] = count + 1
                st.rerun()
            values[sub_name] = [item for item in items if item != ""]
        else:
            values[sub_name] = st.text_input(
                sub_label,
                key=f"form:{template_id}:{field_name}:{sub_name}",
            )
    return values


def _render_model_list(
    template_id: str,
    field_name: str,
    field_info: FieldInfo,
    nested_model: type[BaseModel],
    state: Any,
    st: Any,
) -> list[dict[str, Any]]:
    label = _field_description(field_name, field_info)
    count_key = _count_key(template_id, field_name)
    count = state[count_key]
    st.markdown(f"**{label}**")
    items: list[dict[str, Any]] = []
    for index in range(count):
        with st.expander(f"{label} {index + 1}", expanded=True):
            item_values: dict[str, Any] = {}
            for sub_name, sub_info in nested_model.model_fields.items():
                sub_label = _field_description(sub_name, sub_info)
                item_values[sub_name] = st.text_input(
                    sub_label,
                    key=_item_key(template_id, field_name, index, sub_name),
                )
            col_remove = st.columns([6, 1])[1]
            with col_remove:
                if st.button("×", key=f"rm:{template_id}:{field_name}:{index}"):
                    state[count_key] = max(count - 1, 0)
                    st.rerun()
            items.append(item_values)
    if st.button(f"+ Add {label.lower()}", key=f"add:{template_id}:{field_name}"):
        state[count_key] = count + 1
        st.rerun()
    return items


def _render_path_field(
    template_id: str,
    field_name: str,
    field_info: FieldInfo,
    state: Any,
    st: Any,
) -> str:
    label = _field_description(field_name, field_info)
    key = f"form:{template_id}:{field_name}"
    upload_key = f"upload:{template_id}:{field_name}"
    path_value = st.text_input(label, key=key)
    uploaded = st.file_uploader(
        f"Upload {label.lower()}",
        key=upload_key,
        label_visibility="collapsed",
    )
    if uploaded is not None:
        temp_dir = Path(tempfile.gettempdir()) / "slides-factory-preview"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / uploaded.name
        temp_path.write_bytes(uploaded.getvalue())
        return str(temp_path)
    return path_value


def render_template_form(
    template_id: str,
    model: type[TemplateInput],
    state: Any,
    st: Any,
) -> dict[str, Any]:
    """Render Streamlit widgets for a TemplateInput model and return raw field values."""
    init_form_state(template_id, model, state)
    values: dict[str, Any] = {}

    for name, field_info in model.model_fields.items():
        inner = _list_inner(field_info.annotation)
        nested_top = _is_model_type(field_info.annotation)
        if nested_top is not None:
            values[name] = _render_model_object(
                template_id, name, field_info, nested_top, state, st
            )
        elif inner is not None:
            nested = _is_model_type(inner)
            if nested is not None:
                values[name] = _render_model_list(template_id, name, field_info, nested, state, st)
            elif inner is int:
                values[name] = _render_int_list(template_id, name, field_info, state, st)
            else:
                values[name] = _render_string_list(template_id, name, field_info, state, st)
        elif name.endswith("_path"):
            values[name] = _render_path_field(template_id, name, field_info, state, st)
        else:
            values[name] = _render_scalar_field(template_id, name, field_info, state, st)

    return values
