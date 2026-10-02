"""Document loader — loads .cardforge.json files (v1 auto-migrated, v2 native)."""

import json
from pathlib import Path


class DocumentLoadError(Exception):
    pass


def read_document_file(path: str) -> dict:
    """Path → raw dict. Owns the existence check, the UTF-8 decode and the
    JSON error mapping so no caller has to re-implement them.

    Raises DocumentLoadError for a missing file or invalid JSON.
    """
    p = Path(path)
    if not p.is_file():
        raise DocumentLoadError(f"Document not found: {path}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise DocumentLoadError(f"Invalid JSON: {e}") from e


def load_document_v2(path: str):
    """Load any .cardforge.json (v1 or v2) as a resolved, validated DocumentV2.

    v1 documents are migrated in-memory; the file on disk is not touched.
    Goes through `cardforge.service.load_document`, the same path the API and
    the MCP server use, so `cardforge validate` cannot bless a document the
    compiler would reject (an unresolved `{{var}}`, say).

    Raises:
        DocumentLoadError: file missing, invalid JSON, unrecognized format,
            or an unresolvable variable reference.
        DocumentValidationError: v2 schema/referential validation failed.
    """
    from cardforge.service import load_document

    data = read_document_file(path)
    try:
        return load_document(data)
    except ValueError as e:
        raise DocumentLoadError(f"{e}: {path}") from e
