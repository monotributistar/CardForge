"""Document loader — loads .cardforge.json files."""

import json
from pathlib import Path
from cardforge.document.model import CardForgeDocument


class DocumentLoadError(Exception):
    pass


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
    """Detect if a file is a .cardforge.json document (has 'objects' key)."""
    try:
        data = json.loads(Path(path).read_text())
        return "objects" in data and "document" in data
    except Exception:
        return False
