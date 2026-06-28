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
    supported_relief_modes: List[str] = field(default_factory=lambda: ["emboss", "deboss", "flush", "cut"])
    supported_features: List[str] = field(default_factory=lambda: [
        "text-block", "qr", "pattern", "logo", "frame", "corner",
    ])

    @classmethod
    def fdm_standard(cls) -> "ManufacturingProfile":
        """Standard FDM profile with 0.4mm nozzle."""
        return cls(
            process="fdm",
            nozzle=0.4,
            layer_height=0.20,
            material="PLA",
            printer_name="Generic FDM 0.4mm",
        )

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
