"""Document loader — loads .cardforge.json files (v1 auto-migrated, v2 native)."""

import json
from pathlib import Path


class DocumentLoadError(Exception):
    pass


def load_document_v2(path: str):
    """Load any .cardforge.json (v1 or v2) as a validated DocumentV2.

    v1 documents are migrated in-memory; the file on disk is not touched.

    Raises:
        DocumentLoadError: file missing, invalid JSON, or unrecognized format.
        DocumentValidationError: v2 schema/referential validation failed.
    """
    from cardforge.document.migrate import detect_version, migrate_v1_to_v2
    from cardforge.document.schema_v2 import DocumentV2

    p = Path(path)
    if not p.exists():
        raise DocumentLoadError(f"Document not found: {path}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise DocumentLoadError(f"Invalid JSON: {e}") from e

    version = detect_version(data)
    if version == "1":
        data = migrate_v1_to_v2(data)
    elif version != "2":
        raise DocumentLoadError(
            f"Not a CardForge document (v1 or v2): {path}")
    return DocumentV2.from_dict(data)
