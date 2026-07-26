"""Manufacturing profiles — defines capabilities and constraints per process."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ManufacturingProfile:
    """Profile defining the capabilities and constraints of a manufacturing process.

    All values in millimeters unless otherwise noted.
    """

    process: str = "fdm"
    nozzle: float = 0.4
    layer_height: float = 0.20
    material: str = "PLA"
    printer_name: str = "Generic FDM"

    # Resolution constraints
    min_line_width: float = 0.4
    min_wall: float = 0.8
    min_gap: float = 0.4
    min_emboss: float = 0.3
    min_deboss: float = 0.2
    max_deboss: float = 0.4
    min_qr_module: float = 0.6
    min_qr_size: float = 22.0
    min_qr_quiet_zone: float = 2.0
    min_text_size: float = 3.0
    min_text_stroke: float = 0.6

    # Supported features
    # "pocket" is the blind insert cavity — carved, so every subtractive
    # process handles it; its wall/lid checks live in kernel/constraints.
    supported_relief_modes: List[str] = field(default_factory=lambda: ["emboss", "deboss", "flush", "cut", "deboss-backed", "pocket"])
    supported_features: List[str] = field(default_factory=lambda: [
        "text-block", "text-pattern", "pattern", "qr", "icon", "shape",
        "hole", "pocket",
    ])

    @classmethod
    def for_nozzle(cls, nozzle: float, layer_height: float = 0.2,
                   process: str = "fdm", material: str = "PLA") -> "ManufacturingProfile":
        """Derive an FDM profile from the actual nozzle diameter.

        The minimum printable XY detail is the nozzle: a single extruded line
        cannot be narrower than the nozzle. Walls want two perimeters, and
        legibility/robustness want a margin above the raw minimum.
        """
        n = max(0.05, nozzle)
        return cls(
            process=process,
            nozzle=n,
            layer_height=layer_height,
            material=material,
            printer_name=f"Generic FDM {n:.2f}mm",
            min_line_width=n,                       # a single line == the nozzle
            min_wall=round(2 * n, 3),               # two perimeters
            min_gap=n,                              # features must clear by a nozzle
            min_emboss=round(max(1.5 * layer_height, 0.3), 3),
            min_deboss=round(max(layer_height, 0.15), 3),
            max_deboss=round(max(2 * layer_height, 0.4), 3),
            min_qr_module=round(1.25 * n, 3),       # a module needs a clean line + edge
            min_qr_size=22.0,
            min_text_size=round(max(2.5, 6 * n), 3),
            min_text_stroke=round(1.25 * n, 3),
        )

    @classmethod
    def fdm_standard(cls) -> "ManufacturingProfile":
        """Standard FDM profile with 0.4mm nozzle."""
        return cls.for_nozzle(0.4, layer_height=0.20)

    @classmethod
    def fdm_fine(cls) -> "ManufacturingProfile":
        """Fine-detail FDM profile with 0.25mm nozzle."""
        return cls(
            process="fdm",
            nozzle=0.25,
            layer_height=0.10,
            material="PLA",
            printer_name="Generic FDM 0.25mm",
            min_line_width=0.25,
            min_wall=0.5,
            min_gap=0.25,
            min_emboss=0.15,
            min_deboss=0.12,
            min_qr_module=0.4,
            min_qr_size=16.0,
            min_text_size=2.0,
        )

    @classmethod
    def sla_standard(cls) -> "ManufacturingProfile":
        """Standard SLA/resin profile."""
        return cls(
            process="sla",
            nozzle=0.0,  # SLA has no nozzle
            layer_height=0.05,
            material="Resin",
            printer_name="Generic SLA",
            min_line_width=0.05,
            min_wall=0.3,
            min_gap=0.1,
            min_emboss=0.05,
            min_deboss=0.05,
            min_qr_module=0.1,
            min_qr_size=10.0,
            min_text_size=1.5,
        )

    def to_dict(self) -> dict:
        return {
            "process": self.process,
            "nozzle": self.nozzle,
            "layer_height": self.layer_height,
            "material": self.material,
            "printer_name": self.printer_name,
            "min_line_width": self.min_line_width,
            "min_wall": self.min_wall,
            "min_gap": self.min_gap,
            "min_emboss": self.min_emboss,
            "min_deboss": self.min_deboss,
            "min_qr_module": self.min_qr_module,
            "min_qr_size": self.min_qr_size,
            "min_text_size": self.min_text_size,
        }
