"""Embed brand font files into a saved .pptx (OpenXML package patch).

Functions:
    embed_fonts_in_pptx          — Patch a .pptx to embed font binaries by family name.
    _font_bytes_for_embedding    — Read ``.fntdata`` or TTF/OTF bytes for embedding.
    _ensure_fntdata_content_type — Add fntdata content type to ``[Content_Types].xml``.
    _enable_embedding            — Set ``embedTrueTypeFonts="1"`` on presentation root.
    _existing_font_count         — Count existing ``ppt/fonts/*.fntdata`` parts.
    _next_rid                    — Compute next relationship id in rels XML.
    _add_relationship            — Append font relationship to rels XML.
    _upsert_embedded_font_list   — Insert or update ``embeddedFontLst`` entries.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from lxml import etree

FONT_REL_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"
)
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"

NSMAP = {"p": P_NS, "r": R_NS}


def embed_fonts_in_pptx(
    pptx_path: Path,
    fonts: list[tuple[str, Path]],
) -> None:
    """Patch a .pptx to embed font binaries referenced by family name.

    Each entry is ``(typeface, font_file_path)``. Duplicate paths are skipped.
    Uses a ``.fntdata`` sibling when present, otherwise the TTF/OTF bytes.
    """
    unique: dict[Path, str] = {}
    for typeface, font_path in fonts:
        resolved = font_path.resolve()
        if resolved.is_file():
            unique[resolved] = typeface

    if not unique:
        return

    original = pptx_path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(original), "r") as zin:
        pres_root = etree.fromstring(zin.read("ppt/presentation.xml"))
        rels_root = etree.fromstring(zin.read("ppt/_rels/presentation.xml.rels"))
        ct_root = etree.fromstring(zin.read("[Content_Types].xml"))

        _ensure_fntdata_content_type(ct_root)
        _enable_embedding(pres_root)

        variant_rids: dict[str, str] = {}
        new_parts: dict[str, bytes] = {}
        font_counter = _existing_font_count(zin)

        for font_path, typeface in unique.items():
            font_counter += 1
            part_name = f"ppt/fonts/font{font_counter}.fntdata"
            rid = _next_rid(rels_root)
            _add_relationship(rels_root, rid, f"fonts/font{font_counter}.fntdata")
            variant_rids[typeface] = rid
            new_parts[part_name] = _font_bytes_for_embedding(font_path)

        _upsert_embedded_font_list(pres_root, variant_rids)

        modifications = {
            "ppt/presentation.xml": etree.tostring(
                pres_root, xml_declaration=True, encoding="UTF-8", standalone=True
            ),
            "ppt/_rels/presentation.xml.rels": etree.tostring(
                rels_root, xml_declaration=True, encoding="UTF-8", standalone=True
            ),
            "[Content_Types].xml": etree.tostring(
                ct_root, xml_declaration=True, encoding="UTF-8", standalone=True
            ),
            **new_parts,
        }

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zout:
            for name in zin.namelist():
                zout.writestr(name, modifications.get(name, zin.read(name)))
            for name, content in modifications.items():
                if name not in zin.namelist():
                    zout.writestr(name, content)

    pptx_path.write_bytes(buffer.getvalue())


def _font_bytes_for_embedding(font_path: Path) -> bytes:
    fntdata = font_path.with_suffix(".fntdata")
    if fntdata.is_file():
        return fntdata.read_bytes()
    return font_path.read_bytes()


def _ensure_fntdata_content_type(ct_root: etree._Element) -> None:
    for default in ct_root.findall(f"{{{CT_NS}}}Default"):
        if default.get("Extension") == "fntdata":
            return
    etree.SubElement(
        ct_root,
        f"{{{CT_NS}}}Default",
        Extension="fntdata",
        ContentType="application/x-fontdata",
    )


def _enable_embedding(pres_root: etree._Element) -> None:
    pres_root.set("embedTrueTypeFonts", "1")
    if "saveSubsetFonts" in pres_root.attrib:
        del pres_root.attrib["saveSubsetFonts"]


def _existing_font_count(zin: zipfile.ZipFile) -> int:
    return sum(
        1
        for name in zin.namelist()
        if name.startswith("ppt/fonts/font") and name.endswith(".fntdata")
    )


def _next_rid(rels_root: etree._Element) -> str:
    max_id = 0
    for rel in rels_root:
        rid = rel.get("Id", "")
        if rid.startswith("rId"):
            max_id = max(max_id, int(rid[3:]))
    return f"rId{max_id + 1}"


def _add_relationship(rels_root: etree._Element, rid: str, target: str) -> None:
    etree.SubElement(
        rels_root,
        f"{{{RELS_NS}}}Relationship",
        Id=rid,
        Type=FONT_REL_TYPE,
        Target=target,
    )


def _upsert_embedded_font_list(
    pres_root: etree._Element,
    variant_rids: dict[str, str],
) -> None:
    existing = pres_root.find("p:embeddedFontLst", NSMAP)
    if existing is None:
        existing = etree.Element(f"{{{P_NS}}}embeddedFontLst")
        default_style = pres_root.find("p:defaultTextStyle", NSMAP)
        if default_style is not None:
            pres_root.insert(list(pres_root).index(default_style), existing)
        else:
            pres_root.append(existing)

    for typeface, rid in variant_rids.items():
        entry = etree.SubElement(existing, f"{{{P_NS}}}embeddedFont")
        etree.SubElement(
            entry,
            f"{{{P_NS}}}font",
            typeface=typeface,
            pitchFamily="2",
            charset="0",
        )
        regular = etree.SubElement(entry, f"{{{P_NS}}}regular")
        regular.set(f"{{{R_NS}}}id", rid)
