"""
OSCAL Parser & Validation Engine
--------------------------------
Parst importierte OSCAL-Catalog-JSON-Dateien (NIST OSCAL 1.1.0 Schema) und
ueberfuehrt Gruppen/Kontrollen in das relationale Datenmodell der Anwendung.

Erwartete Struktur (vereinfachtes OSCAL-Catalog-Schema):
{
  "catalog": {
    "uuid": "...",
    "metadata": {"title": "...", "version": "..."},
    "groups": [
      {
        "id": "art21-2",
        "title": "...",
        "groups": [ ... ],           # optional verschachtelt
        "controls": [
          {
            "id": "21.2d",
            "title": "...",
            "parts": [{"name": "statement", "prose": "..."}]
          }
        ]
      }
    ]
  }
}
"""
from sqlalchemy.orm import Session
from ..models import Catalog, Control


class OscalValidationError(Exception):
    pass


def _extract_prose(node: dict) -> str | None:
    for part in node.get("parts", []) or []:
        if part.get("name") == "statement" and part.get("prose"):
            return part["prose"]
    return node.get("prose")


def _walk(db: Session, catalog_id: int, node: dict, parent_id: int | None,
          is_group: bool, order_counter: list[int]) -> Control:
    order_counter[0] += 1
    control = Control(
        catalog_id=catalog_id,
        parent_id=parent_id,
        code=node.get("id", f"n{order_counter[0]}"),
        title=node.get("title", "(ohne Titel)"),
        prose=_extract_prose(node),
        is_group=is_group,
        sort_order=order_counter[0],
    )
    db.add(control)
    db.flush()  # obtain control.id for children

    for sub_group in node.get("groups", []) or []:
        _walk(db, catalog_id, sub_group, control.id, True, order_counter)

    for leaf in node.get("controls", []) or []:
        _walk(db, catalog_id, leaf, control.id, False, order_counter)

    return control


def validate_oscal_catalog(data: dict) -> dict:
    if "catalog" not in data:
        raise OscalValidationError(
            "Ungueltiges OSCAL-Dokument: Top-Level-Schluessel 'catalog' fehlt."
        )
    catalog = data["catalog"]
    if "metadata" not in catalog or "title" not in catalog.get("metadata", {}):
        raise OscalValidationError("Ungueltiges OSCAL-Dokument: 'catalog.metadata.title' fehlt.")
    if "groups" not in catalog and "controls" not in catalog:
        raise OscalValidationError(
            "Ungueltiges OSCAL-Dokument: weder 'groups' noch 'controls' vorhanden."
        )
    return catalog


def parse_and_store(db: Session, data: dict, source_label: str) -> Catalog:
    """Validiert und persistiert einen OSCAL-Katalog inkl. verschachtelter Gruppen/Kontrollen."""
    catalog_data = validate_oscal_catalog(data)
    metadata = catalog_data.get("metadata", {})

    catalog = Catalog(
        title=metadata.get("title", "Unbenannter Katalog"),
        source=source_label,
        version=metadata.get("version"),
    )
    db.add(catalog)
    db.flush()

    order_counter = [0]
    for group in catalog_data.get("groups", []) or []:
        _walk(db, catalog.id, group, None, True, order_counter)
    for leaf in catalog_data.get("controls", []) or []:
        _walk(db, catalog.id, leaf, None, False, order_counter)

    db.commit()
    db.refresh(catalog)
    return catalog
