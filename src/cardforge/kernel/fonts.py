"""Font discovery and loading — system fonts + project assets, variable axes.

`load_font(spec)` returns a ready-to-outline TTFont: family resolved against
the index, variable fonts instantiated at the requested weight/axes (cached).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fontTools.ttLib import TTFont, TTLibError

FONT_DIRS = [
    Path("assets/fonts"),  # project-relative, checked first
    Path.home() / "Library" / "Fonts",
    Path("/Library/Fonts"),
    Path("/System/Library/Fonts"),
    Path("/System/Library/Fonts/Supplemental"),
]

FALLBACK_FAMILIES = ["Helvetica Neue", "Arial", "Geneva"]

_NAME_FAMILY = 1
_NAME_TYPO_FAMILY = 16


class FontNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class FontFace:
    path: str
    index: int          # face index inside .ttc collections
    family: str
    is_variable: bool


def _families_of(font: TTFont) -> List[str]:
    fams = set()
    name = font.get("name")
    if name:
        for nid in (_NAME_TYPO_FAMILY, _NAME_FAMILY):
            rec = name.getDebugName(nid)
            if rec:
                fams.add(rec)
    return list(fams)


@lru_cache(maxsize=1)
def font_index() -> Dict[str, FontFace]:
    """family (lowercased) → FontFace, scanning FONT_DIRS once per process."""
    index: Dict[str, FontFace] = {}
    for d in FONT_DIRS:
        if not d.exists():
            continue
        for p in sorted(d.iterdir()):
            if p.suffix.lower() not in (".ttf", ".otf", ".ttc"):
                continue
            try:
                n_faces = 1
                if p.suffix.lower() == ".ttc":
                    from fontTools.ttLib import TTCollection
                    n_faces = len(TTCollection(str(p), lazy=True).fonts)
                for i in range(n_faces):
                    f = TTFont(str(p), fontNumber=i if n_faces > 1 else -1, lazy=True)
                    is_var = "fvar" in f
                    for fam in _families_of(f):
                        key = fam.lower()
                        # First hit wins (assets/fonts first → project overrides)
                        if key not in index:
                            index[key] = FontFace(str(p), i if n_faces > 1 else -1,
                                                  fam, is_var)
                    f.close()
            except (TTLibError, Exception):
                continue
    return index


def list_families() -> List[dict]:
    """User-facing font list: the families the kernel can actually render.

    Internal/hidden families (leading '.', e.g. '.SF NS') are omitted. Each
    entry is {family, variable} so the editor can offer only real, renderable
    fonts and flag the ones with weight/axis support.
    """
    by_family: Dict[str, bool] = {}
    for face in font_index().values():
        if face.family.startswith("."):
            continue
        by_family[face.family] = by_family.get(face.family, False) or face.is_variable
    return [{"family": fam, "variable": var}
            for fam, var in sorted(by_family.items(), key=lambda kv: kv[0].lower())]


def resolve_family(family: str) -> FontFace:
    idx = font_index()
    face = idx.get(family.lower())
    if face:
        return face
    for fb in FALLBACK_FAMILIES:
        face = idx.get(fb.lower())
        if face:
            return face
    raise FontNotFoundError(
        f"Font family '{family}' not found and no fallback available")


@lru_cache(maxsize=32)
def _load_instantiated(path: str, index: int,
                       axes_key: Tuple[Tuple[str, float], ...]) -> TTFont:
    font = TTFont(path, fontNumber=index)
    if axes_key and "fvar" in font:
        from fontTools.varLib.instancer import instantiateVariableFont
        available = {a.axisTag for a in font["fvar"].axes}
        wanted = {tag: val for tag, val in axes_key if tag in available}
        if wanted:
            instantiateVariableFont(font, wanted, inplace=True)
    return font


def load_font(family: str, weight: Optional[float] = None,
              axes: Optional[Dict[str, float]] = None) -> Tuple[TTFont, FontFace]:
    """Resolve + load + (if variable) instantiate a font.

    `weight` is sugar for axes={"wght": weight}; explicit axes win.
    Returned TTFont objects are cached — treat them as read-only.
    """
    face = resolve_family(family)
    all_axes: Dict[str, float] = {}
    if weight is not None:
        all_axes["wght"] = float(weight)
    if axes:
        all_axes.update({k: float(v) for k, v in axes.items()})
    axes_key = tuple(sorted(all_axes.items()))
    return _load_instantiated(face.path, face.index, axes_key), face
