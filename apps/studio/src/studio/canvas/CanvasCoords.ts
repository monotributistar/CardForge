// Canvas coordinates — convert between Document (mm) and Screen (pixels)
//
// Document: top-left origin, mm units, card bounds 0..w, 0..h
// Screen: top-left origin, px units, zoom applied

import type { Feature, Outline } from '../../types/cardforge'

export const PX_PER_MM = 4

/** Outline dimensions in mm. Circle is width=height=diameter. */
export function outlineSize(outline: Outline): { width: number; height: number } {
  if (outline.type === 'circle') return { width: outline.diameter, height: outline.diameter }
  return { width: outline.width, height: outline.height }
}

export interface CanvasViewport {
  zoom: number
  offsetX: number
  offsetY: number
}

/** Convert document mm coordinates to screen pixel coordinates */
export function documentToScreen(
  docX: number, docY: number,
  cardWidth: number, cardHeight: number,
  viewport: CanvasViewport,
  containerWidth: number, containerHeight: number,
): { x: number; y: number } {
  const PX = PX_PER_MM
  const scaledW = cardWidth * PX * viewport.zoom
  const scaledH = cardHeight * PX * viewport.zoom
  const cx = (containerWidth - scaledW) / 2 + viewport.offsetX
  const cy = (containerHeight - scaledH) / 2 + viewport.offsetY
  return {
    x: cx + docX * PX * viewport.zoom,
    y: cy + docY * PX * viewport.zoom,
  }
}

/**
 * Convert screen pixel coordinates to document mm coordinates.
 * Clamps to the card bounds unless `clamp` is false (used by the
 * scale/rotate handle drags, which need the raw pointer position).
 */
export function screenToDocument(
  screenX: number, screenY: number,
  cardWidth: number, cardHeight: number,
  viewport: CanvasViewport,
  containerWidth: number, containerHeight: number,
  clamp = true,
): { x: number; y: number } {
  const PX = PX_PER_MM
  const scaledW = cardWidth * PX * viewport.zoom
  const scaledH = cardHeight * PX * viewport.zoom
  const cx = (containerWidth - scaledW) / 2 + viewport.offsetX
  const cy = (containerHeight - scaledH) / 2 + viewport.offsetY
  const x = (screenX - cx) / (PX * viewport.zoom)
  const y = (screenY - cy) / (PX * viewport.zoom)
  if (!clamp) return { x, y }
  return {
    x: Math.max(0, Math.min(cardWidth, x)),
    y: Math.max(0, Math.min(cardHeight, y)),
  }
}

export interface BoundsMm { x: number; y: number; w: number; h: number }

/**
 * Estimate a v2 feature's bounding box in document mm.
 * transform.x/y is treated as the top-left anchor of the box.
 * Text sizes are approximations for editing purposes only — the Core
 * compiles the real geometry.
 */
export function getFeatureBoundsMm(feature: Feature, cardW: number, cardH: number): BoundsMm {
  const { x, y } = feature.transform
  switch (feature.type) {
    case 'text-block': {
      const size = feature.font.size
      const longest = feature.lines.reduce((m, l) => Math.max(m, l.length), 1)
      const w = Math.max(4, longest * size * 0.6)
      const h = Math.max(size * 1.2, feature.lines.length * size * (feature.lineHeight ?? 1.2))
      return { x, y, w, h }
    }
    case 'text-pattern': {
      const size = feature.font.size
      const w = Math.max(10, (feature.text.length || 1) * size * 0.6)
      return { x, y, w, h: size * 1.4 }
    }
    case 'pattern': {
      if (feature.region === 'face') return { x: 0, y: 0, w: cardW, h: cardH }
      return { x, y, w: feature.width ?? 20, h: feature.height ?? 20 }
    }
    case 'qr':
      return { x, y, w: feature.size, h: feature.size }
    case 'icon':
      return { x, y, w: feature.width, h: feature.height ?? feature.width }
    case 'shape': {
      switch (feature.shapeType) {
        case 'circle':
        case 'ring': {
          const d = feature.diameter ?? feature.width ?? 10
          return { x, y, w: d, h: d }
        }
        case 'frame':
        case 'corner-marks':
          return { x, y, w: feature.width ?? cardW, h: feature.height ?? cardH }
        default:
          return { x, y, w: feature.width ?? 20, h: feature.height ?? 10 }
      }
    }
    case 'hole': {
      if (feature.holeType === 'slot') return { x, y, w: feature.width ?? 14, h: feature.height ?? 5 }
      const d = feature.diameter ?? 5
      return { x, y, w: d, h: d }
    }
  }
}
