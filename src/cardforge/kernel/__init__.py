"""CardForge geometry kernel — document → per-material solid partition.

Coordinate conventions (fixed, everything depends on these):

- Document space (schema v2): millimetres, origin at the object's TOP-LEFT,
  y grows DOWNWARD (matches the 2D editor canvas).
- Physical space (kernel output): millimetres, origin at the object's
  BOTTOM-LEFT, y grows UPWARD, z grows away from the print bed.
  doc (x, y) → phys (x, object_height − y).
- Feature-local 2D space: y-up, the feature's ANCHOR (its document top-left
  corner) at (0, 0); content extends x ∈ [0, w], y ∈ [−h, 0].
- The back face is authored in its own document space (as seen when flipping
  the card over around its VERTICAL edge); the compiler mirrors it into place.
"""
