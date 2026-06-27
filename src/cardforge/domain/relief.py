"""Relief model — controls Z-axis treatment of features on a surface."""

from dataclasses import dataclass
from typing import Optional

from cardforge.domain.geometry import ReliefMode


@dataclass
class Relief:
    """How a feature interacts with the base surface in the Z dimension.

    All values in millimeters.

    Constraints for FDM 0.4mm nozzle:
        - emboss height: 0.1–0.6 mm (recommended)
        - deboss depth: 0.1–0.3 mm (recommended)
        - cut depth: must not exceed object thickness
    """

    mode: ReliefMode = ReliefMode.FLUSH
    height: Optional[float] = None  # used for emboss (+Z)
    depth: Optional[float] = None   # used for deboss/cut (−Z)

    def __post_init__(self):
        errors = []
        if self.mode == ReliefMode.EMBOSS:
            if self.height is None:
                errors.append("emboss requires 'height'")
            elif self.height <= 0:
                errors.append(f"emboss height must be > 0, got {self.height}")
            if self.depth is not None:
                errors.append("emboss must not have 'depth'")

        elif self.mode == ReliefMode.DEBOSS:
            if self.depth is None:
                errors.append("deboss requires 'depth'")
            elif self.depth <= 0:
                errors.append(f"deboss depth must be > 0, got {self.depth}")
            if self.height is not None:
                errors.append("deboss must not have 'height'")

        elif self.mode == ReliefMode.CUT:
            if self.depth is None:
                errors.append("cut requires 'depth'")
            elif self.depth <= 0:
                errors.append(f"cut depth must be > 0, got {self.depth}")
            if self.height is not None:
                errors.append("cut must not have 'height'")

        elif self.mode == ReliefMode.FLUSH:
            # flush should not require height/depth, but can have them
            pass

        if errors:
            raise ValueError("; ".join(errors))

    def to_dict(self) -> dict:
        result: dict = {"mode": self.mode.value}
        if self.height is not None:
            result["height"] = self.height
        if self.depth is not None:
            result["depth"] = self.depth
        return result

    @classmethod
    def flush(cls) -> "Relief":
        return cls(mode=ReliefMode.FLUSH)

    @classmethod
    def emboss(cls, height: float) -> "Relief":
        return cls(mode=ReliefMode.EMBOSS, height=height)

    @classmethod
    def deboss(cls, depth: float) -> "Relief":
        return cls(mode=ReliefMode.DEBOSS, depth=depth)

    @classmethod
    def cut(cls, depth: float) -> "Relief":
        return cls(mode=ReliefMode.CUT, depth=depth)
