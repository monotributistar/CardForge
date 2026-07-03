"""Document loader — loads .cardforge.json files.

v2 path: load_document_v2() sniffs the version, migrates v1 files on the fly,
validates against the v2 schema and returns a typed DocumentV2.

Legacy path: load_document() returns the v1 CardForgeDocument model. It stays
functional until the legacy pipeline is deleted (refactor Phase 5).
"""

import json
from pathlib import Path
from cardforge.document.model import CardForgeDocument


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
        data = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        raise DocumentLoadError(f"Invalid JSON: {e}") from e

    version = detect_version(data)
    if version == "1":
        data = migrate_v1_to_v2(data)
    elif version != "2":
        raise DocumentLoadError(
            f"Not a CardForge document (v1 or v2): {path}")
    return DocumentV2.from_dict(data)


def load_document(path: str) -> CardForgeDocument:
    """Load a .cardforge.json document.

    Args:
        path: Path to the document file.

    Returns:
        Parsed CardForgeDocument.

    Raises:
        DocumentLoadError: If file not found or invalid.
    """
    p = Path(path)
    if not p.exists():
        raise DocumentLoadError(f"Document not found: {path}")
    try:
        data = json.loads(p.read_text())
        return CardForgeDocument.from_dict(data)
    except json.JSONDecodeError as e:
        raise DocumentLoadError(f"Invalid JSON: {e}") from e


def is_document_file(path: str) -> bool:
    """Detect if a file is a .cardforge.json document (has 'objects' key with a 'document' object)."""
    try:
        data = json.loads(Path(path).read_text())
        return "objects" in data and isinstance(data.get("document"), dict)
    except Exception:
        return False


def is_manifest_file(path: str) -> bool:
    """Detect if a file is a publish manifest (has 'score' and 'files' keys)."""
    try:
        data = json.loads(Path(path).read_text())
        return "score" in data and "files" in data and "document" in data
    except Exception:
        return False
