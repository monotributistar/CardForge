"""Variable resolution for v2 documents — {{var}} and {{assets.x}} substitution.

Harvested from config/resolver.py, adapted to the v2 document layout:
variables resolve against doc["variables"], asset references against
doc["assets"] via the "assets." prefix.
"""

from __future__ import annotations

import copy
import re
from typing import Any, Dict

_VAR_RE = re.compile(r"\{\{(.+?)\}\}")


class UnresolvedVariableError(Exception):
    """Raised when a template variable cannot be resolved."""


def resolve_variables(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of a v2 document dict with all {{var}} patterns resolved.

    Lookup order for a path "a.b":
      1. variables["a.b"] (verbatim key)
      2. assets[x] when path is "assets.x"
      3. dot-path into variables (nested dicts, if ever used)

    Raises UnresolvedVariableError on the first unresolvable reference.
    """
    resolved = copy.deepcopy(doc)
    variables: Dict[str, Any] = resolved.get("variables", {})
    assets: Dict[str, Any] = resolved.get("assets", {})

    def lookup(path: str) -> Any:
        if path in variables:
            return variables[path]
        if path.startswith("assets."):
            key = path[len("assets."):]
            if key in assets:
                return assets[key]
        current: Any = variables
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    def sub(text: str, where: str) -> str:
        def _replace(m: re.Match) -> str:
            path = m.group(1).strip()
            value = lookup(path)
            if value is None:
                raise UnresolvedVariableError(
                    f"Cannot resolve '{{{{{path}}}}}' at {where}")
            return value if isinstance(value, str) else str(value)
        return _VAR_RE.sub(_replace, text)

    def walk(node: Any, where: str) -> Any:
        if isinstance(node, dict):
            return {k: walk(v, f"{where}/{k}") for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v, f"{where}[{i}]") for i, v in enumerate(node)]
        if isinstance(node, str):
            return sub(node, where)
        return node

    # Only faces carry user-facing text; variables/assets themselves stay verbatim.
    if "faces" in resolved:
        resolved["faces"] = walk(resolved["faces"], "faces")
    return resolved
