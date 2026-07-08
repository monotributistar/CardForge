"""Geometric measurement — the thinnest printable detail of a 2D shape.

`min_feature_width` estimates the narrowest wall/stroke of a CrossSection via
a morphological opening: eroding then re-dilating by t/2 erases anything
narrower than t. Binary-searching t finds the width at which detail starts to
disappear — i.e. the minimum feature width. This is what lets the
manufacturing analyzer compare real geometry against the nozzle diameter
(a line thinner than the nozzle cannot print), including text strokes that no
per-type rule could see.
"""

from __future__ import annotations

from manifold3d import CrossSection, JoinType

# Simplify tolerance before probing — text glyphs carry thousands of bezier
# points; 0.04mm detail is finer than any nozzle cares about and cuts the
# measurement from ~270ms to ~6ms for a full text block.
_SIMPLIFY_MM = 0.04
_HI_MM = 2.0          # widths at/above this are "thick"; nozzles never care
_ITERS = 7
_BASELINE_T = 0.08    # corner-loss calibration probe (below any real nozzle)
_EXCESS_TOL = 0.03    # area fraction lost beyond the corner baseline
_CORNER_CAP = 0.2     # corner shedding saturates; never credit more than this


def min_feature_width(cs: CrossSection, hi: float = _HI_MM,
                      iters: int = _ITERS) -> float:
    """Estimate the thinnest wall/stroke of `cs`, in mm.

    Returns `hi` when nothing is thinner than `hi` (a solid, thick shape),
    and ~0 when the shape is a hairline that erosion erases entirely.
    Width is invariant to translation/rotation/mirror, so it is safe to
    measure a feature in its pre-placement pose.

    Corners and glyph tips shed a little area under a round opening even
    when every stroke is thick — quadratically in t, and proportionally to
    how many corners the shape has (long text!). That shedding is measured
    at a probe width no nozzle cares about and extrapolated, so only loss
    in EXCESS of it — an actual stroke vanishing — moves the estimate.
    """
    if cs.is_empty():
        return 0.0
    shape = cs.simplify(_SIMPLIFY_MM)
    total = shape.area()
    if total <= 1e-9:
        return 0.0

    def loss(t: float) -> float:
        opened = (shape.offset(-t / 2, JoinType.Round)
                       .offset(t / 2, JoinType.Round))
        return (total - opened.area()) / total

    base = loss(_BASELINE_T)

    def loses(t: float) -> bool:
        corner_est = min(base * (t / _BASELINE_T) ** 2, _CORNER_CAP)
        return loss(t) - corner_est > _EXCESS_TOL

    if not loses(hi):
        return hi
    lo_t, hi_t = 0.0, hi
    for _ in range(iters):
        mid = (lo_t + hi_t) / 2
        if loses(mid):
            hi_t = mid
        else:
            lo_t = mid
    return (lo_t + hi_t) / 2
