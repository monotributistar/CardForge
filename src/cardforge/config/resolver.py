"""Config variable resolver — {{path.to.var}} template substitution.

Walks the config dict and replaces all {{var}} patterns with their
resolved values from the config's own data tree.
"""

import copy
import re
from typing import Any, Dict


class UnresolvedVariableError(Exception):
    """Raised when a template variable cannot be resolved."""

    pass


# Matches {{path.to.variable}} with optional surrounding text
_VAR_RE = re.compile(r"\{\{(.+?)\}\}")


def resolve_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve all template variables in a config dict.

    Walks the entire config tree looking for {{path.to.var}} patterns
    in string values. Resolves each against the config's own data using
    dot-notation path lookup.

    Args:
        config: Config dict potentially containing template variables.

    Returns:
        A new dict with all variables resolved. The original is not modified.

    Raises:
        UnresolvedVariableError: If any variable cannot be resolved.
    """
    resolved = copy.deepcopy(config)

    # Walk and resolve
    _resolve_in_place(resolved, resolved)

    return resolved


def _resolve_in_place(data: Any, root: Dict[str, Any]) -> None:
    """Recursively walk data and resolve {{var}} patterns in strings."""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = _resolve_string(value, root)
            elif isinstance(value, (dict, list)):
                _resolve_in_place(value, root)

    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, str):
                data[i] = _resolve_string(item, root)
            elif isinstance(item, (dict, list)):
                _resolve_in_place(item, root)


def _resolve_string(text: str, root: Dict[str, Any]) -> str:
    """Replace all {{var}} patterns in a string with resolved values."""

    def _replace(match: re.Match) -> str:
        path = match.group(1).strip()
        value = _lookup_path(path, root)
        if value is None:
            raise UnresolvedVariableError(
                f"Cannot resolve '{{{{{path}}}}}': path not found in config"
            )
        # Convert non-string values to their string representation
        return str(value) if not isinstance(value, str) else value

    return _VAR_RE.sub(_replace, text)


def _lookup_path(path: str, root: Dict[str, Any]) -> Any:
    """Look up a dot-notation path in a nested dict.

    Args:
        path: Dot-separated path like 'owner.contact.email'.
        root: The root dict to search.

    Returns:
        The value at the path, or None if not found.
    """
    parts = path.split(".")
    current = root
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current
