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
    # Linux (containers) — the scan is non-recursive, so list the actual
    # package dirs rather than /usr/share/fonts.
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/truetype/liberation"),
    Path("/usr/share/fonts/truetype/noto"),
]

FALLBACK_FAMILIES = ["Helvetica Neue", "Arial", "Geneva",
                     "DejaVu Sans", "Liberation Sans"]

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
    weight: float = 400.0   # OS/2 usWeightClass (static faces)
    italic: bool = False


def _families_of(font: TTFont) -> List[str]:
    fams = set()
    name = font.get("name")
    if name:
        for nid in (_NAME_TYPO_FAMILY, _NAME_FAMILY):
            rec = name.getDebugName(nid)
            if rec:
                fams.add(rec)
    return list(fams)


def _face_style(f: TTFont) -> Tuple[float, bool]:
    """(usWeightClass, italic) of a loaded face — 400/False when unreadable."""
    weight, italic = 400.0, False
    try:
        os2 = f.get("OS/2")
        if os2:
            weight = float(os2.usWeightClass or 400)
            italic = bool(os2.fsSelection & 0x01)
        elif f.get("head"):
            italic = bool(f["head"].macStyle & 0x02)
    except Exception:
        pass
    return weight, italic


@lru_cache(maxsize=1)
def font_index() -> Dict[str, List[FontFace]]:
    """family (lowercased) → ALL its faces (one per weight/style), scanning
    FONT_DIRS once per process. Keeping every face is what makes `weight`
    work for static families (Bold/Light live in separate faces)."""
    index: Dict[str, List[FontFace]] = {}
    seen_dirs_family_style: set = set()
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
                    # Outline tables required — bitmap-only fonts (emoji,
                    # legacy CJK bitmaps) have no contours to extrude and
                    # would crash the renderer.
                    if "glyf" not in f and "CFF " not in f and "CFF2" not in f:
                        f.close()
                        continue
                    is_var = "fvar" in f
                    weight, italic = _face_style(f)
                    for fam in _families_of(f):
                        key = fam.lower()
                        # One face per (family, weight, italic): the first
                        # FONT_DIR hit wins (assets/fonts overrides system).
                        style_key = (key, weight, italic, is_var)
                        if style_key in seen_dirs_family_style:
                            continue
                        seen_dirs_family_style.add(style_key)
                        index.setdefault(key, []).append(
                            FontFace(str(p), i if n_faces > 1 else -1,
                                     fam, is_var, weight, italic))
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
    out = []
    for faces in font_index().values():
        fam = faces[0].family
        if fam.startswith("."):
            continue
        weights = sorted({f.weight for f in faces if not f.is_variable})
        out.append({"family": fam,
                    "variable": any(f.is_variable for f in faces),
                    "weights": weights})
    return sorted(out, key=lambda e: e["family"].lower())


def _best_face(faces: List[FontFace], weight: Optional[float],
               italic: bool) -> FontFace:
    """Closest face: match italic when possible, then nearest weight.
    A variable face wins outright — it can be instantiated at any weight."""
    target = float(weight) if weight is not None else 400.0
    pool = [f for f in faces if f.italic == italic] or faces
    variable = [f for f in pool if f.is_variable]
    if variable:
        return variable[0]
    return min(pool, key=lambda f: abs(f.weight - target))


def resolve_family(family: str, weight: Optional[float] = None,
                   italic: bool = False) -> FontFace:
    idx = font_index()
    faces = idx.get(family.lower())
    if not faces:
        for fb in FALLBACK_FAMILIES:
            faces = idx.get(fb.lower())
            if faces:
                break
    if not faces:
        raise FontNotFoundError(
            f"Font family '{family}' not found and no fallback available")
    return _best_face(faces, weight, italic)


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
              axes: Optional[Dict[str, float]] = None,
              italic: bool = False) -> Tuple[TTFont, FontFace]:
    """Resolve + load + (if variable) instantiate a font.

    Static families: `weight`/`italic` select the closest real face.
    Variable fonts: `weight` is sugar for axes={"wght": weight}; explicit
    axes win. Returned TTFont objects are cached — treat them as read-only.
    """
    face = resolve_family(family, weight=weight, italic=italic)
    all_axes: Dict[str, float] = {}
    if weight is not None:
        all_axes["wght"] = float(weight)
    if axes:
        all_axes.update({k: float(v) for k, v in axes.items()})
    axes_key = tuple(sorted(all_axes.items()))
    return _load_instantiated(face.path, face.index, axes_key), face
