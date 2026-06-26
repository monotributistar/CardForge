# CardForge

> Generador modular de objetos planos 3D personalizados  
> tarjetas · credenciales · badges · etiquetas · placas · señalética

[![Status](https://img.shields.io/badge/status-MVP%20Design-blue)](#)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://python.org)
[![OpenSCAD](https://img.shields.io/badge/openscad-2021.01-yellow)](https://openscad.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Qué es CardForge

CardForge convierte archivos de configuración JSON en objetos 3D listos para imprimir. Sin Blender. Sin diseño manual. Sin tocar geometría.

Escribís un config declarando qué querés (texto, QR, logo, patrón, colores, relieve) y CardForge genera el STL.

```
config.json  →  [CardForge]  →  tarjeta.stl
```

**Primer caso de uso:** tarjetas de presentación impresas en 3D con texto en relieve, QR funcionales, patrones decorativos y múltiples colores.

**Diseñado para extenderse:** badges de evento, etiquetas de producto, placas de escritorio, llaveros, señalética QR — todo con el mismo motor.

## Filosofía

- **Declarativo.** La config es la fuente de verdad. El STL es un artefacto derivado.
- **Modular.** Cada cara está compuesta de features independientes (texto, QR, logo, patrón).
- **Extensible.** El core no depende de "tarjetas". Soporta cualquier objeto plano.
- **Imprimible por diseño.** Cada decisión respeta las restricciones de FDM con nozzle 0.4 mm.

## Quick Start

```bash
# Clonar
git clone https://github.com/monotributistar/CardForge.git
cd CardForge

# Instalar dependencias
uv sync

# Generar una tarjeta
python scripts/build.py configs/examples/business_card_basic.json

# Ver resultado
ls exports/Javier_Business_Card/stl/
```

## Pipeline

```
CONFIG (JSON)  →  COMPOSE (Python)  →  GEOMETRY (OpenSCAD)  →  EXPORT (STL)
```

1. Lee y valida la configuración
2. Resuelve variables (`{{owner.name}}`)
3. Genera assets (QR SVG, patrones)
4. Genera código OpenSCAD
5. Renderiza con OpenSCAD CLI
6. Exporta STL (simple + separado por color)
7. Genera previews (SVG + PNG)

## Estructura

```
cardforge/
├── docs/               ← Documentación completa
├── configs/examples/   ← Configuraciones de ejemplo
├── src/cardforge/      ← Paquete Python
├── openscad/modules/   ← Módulos de geometría paramétrica
├── scripts/            ← Scripts de utilidad
├── assets/             ← Fuentes, logos, patrones
└── exports/            ← Salidas generadas
```

## Tecnologías

| Herramienta | Rol |
|-------------|-----|
| Python 3.11+ | Orquestación, CLI, generación de assets |
| OpenSCAD | Geometría paramétrica declarativa |
| SVG | Formato intermedio (QR, logos, patrones) |
| JSON | Configuración (fuente de verdad) |
| STL | Formato de salida primario |
| 3MF | Formato futuro (v0.2) |

## Documentación

- [📐 Arquitectura](docs/ARCHITECTURE.md) — Filosofía, pipeline, modelo de componentes
- [🧩 Componentes](docs/COMPONENTS.md) — Contratos de cada feature y sus interfaces
- [⚙️ Pipeline](docs/PIPELINE.md) — Cada etapa del pipeline en detalle
- [🖨️ Guía de Impresión](docs/PRINTING_GUIDELINES.md) — Restricciones FDM 0.4mm
- [🗺️ Roadmap](docs/ROADMAP.md) — Plan por versiones

## Estado

**v0.1 — En diseño.** La arquitectura y documentación están completas. La implementación del pipeline comienza a continuación.

Ver [ROADMAP.md](docs/ROADMAP.md) para el plan detallado.

## Licencia

MIT — Javier Rodriguez, 2026.
