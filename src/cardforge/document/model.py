"""CardForge Document model — the editable source-of-truth format."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DocumentMetadata:
    id: str = ""
    name: str = ""
    version: str = "0.1.0"


@dataclass
class DocumentAsset:
    id: str
    path: str


@dataclass
class DocumentManufacturing:
    profile: str = "fdm-standard"
    process: str = "fdm"
    nozzle: float = 0.4
    layer_height: float = 0.2
    material: str = "PLA"


@dataclass
class DocumentExport:
    preview: bool = True
    manufacturing_report: bool = True
    single_stl: bool = True
    color_separated_stl: bool = False
    three_mf: bool = False


@dataclass
class DocumentObject:
    id: str
    type: str = "business-card"
    width: float = 85.0
    height: float = 54.0
    thickness: float = 1.8
    corner_radius: float = 4.0
    theme: Dict[str, str] = field(default_factory=dict)
    faces: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CardForgeDocument:
    """Top-level CardForge document — the editable source of truth.

    Contains metadata, variables, assets, manufacturing settings,
    objects (cards, badges, etc.), and export configuration.
    """

    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    manufacturing: DocumentManufacturing = field(default_factory=DocumentManufacturing)
    variables: Dict[str, str] = field(default_factory=dict)
    assets: Dict[str, str] = field(default_factory=dict)
    objects: List[DocumentObject] = field(default_factory=list)
    exports: DocumentExport = field(default_factory=DocumentExport)

    @classmethod
    def from_dict(cls, data: dict) -> "CardForgeDocument":
        doc_data = data.get("document", {})
        metadata = DocumentMetadata(
            id=doc_data.get("id", ""),
            name=doc_data.get("name", ""),
            version=doc_data.get("version", "0.1.0"),
        )
        mfg_data = data.get("manufacturing", {})
        manufacturing = DocumentManufacturing(
            profile=mfg_data.get("profile", "fdm-standard"),
            process=mfg_data.get("process", "fdm"),
            nozzle=mfg_data.get("nozzle", 0.4),
            layer_height=mfg_data.get("layerHeight", 0.2),
            material=mfg_data.get("material", "PLA"),
        )
        variables = data.get("variables", {})
        assets = {k: v for k, v in data.get("assets", {}).items()}

        objects = []
        for obj_data in data.get("objects", []):
            objects.append(DocumentObject(
                id=obj_data.get("id", ""),
                type=obj_data.get("type", "business-card"),
                width=obj_data.get("width", 85.0),
                height=obj_data.get("height", 54.0),
                thickness=obj_data.get("thickness", 1.8),
                corner_radius=obj_data.get("cornerRadius", 4.0),
                theme=obj_data.get("theme", {}),
                faces=obj_data.get("faces", {}),
            ))

        exp_data = data.get("exports", {})
        exports = DocumentExport(
            preview=exp_data.get("preview", True),
            manufacturing_report=exp_data.get("manufacturingReport", True),
            single_stl=exp_data.get("singleStl", True),
            color_separated_stl=exp_data.get("colorSeparatedStl", False),
            three_mf=exp_data.get("threeMf", False),
        )

        return cls(
            metadata=metadata,
            manufacturing=manufacturing,
            variables=variables,
            assets=assets,
            objects=objects,
            exports=exports,
        )

    def to_dict(self) -> dict:
        return {
            "document": {
                "id": self.metadata.id,
                "name": self.metadata.name,
                "version": self.metadata.version,
            },
            "manufacturing": {
                "profile": self.manufacturing.profile,
                "process": self.manufacturing.process,
                "nozzle": self.manufacturing.nozzle,
                "layerHeight": self.manufacturing.layer_height,
                "material": self.manufacturing.material,
            },
            "variables": self.variables,
            "assets": self.assets,
            "objects": [
                {
                    "id": o.id,
                    "type": o.type,
                    "width": o.width,
                    "height": o.height,
                    "thickness": o.thickness,
                    "cornerRadius": o.corner_radius,
                    "theme": o.theme,
                    "faces": o.faces,
                }
                for o in self.objects
            ],
            "exports": {
                "preview": self.exports.preview,
                "manufacturingReport": self.exports.manufacturing_report,
                "singleStl": self.exports.single_stl,
                "colorSeparatedStl": self.exports.color_separated_stl,
                "threeMf": self.exports.three_mf,
            },
        }
