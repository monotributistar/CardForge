// Canvas coordinates — convert between Document (mm) and Screen (pixels)
//
// Document: top-left origin, mm units, card bounds 0..w, 0..h
// Screen: top-left origin, px units, zoom applied

import type { Feature, Outline } from '../../types/cardforge'
import { DEFAULT_POCKET_CLEARANCE } from '../../types/cardforge'

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
 *
 * transform.scale is part of the box: the kernel's place() scales the
 * feature-local shape about its top-left anchor and only then translates it,
 * so the anchor stays put and the box grows right/down. Leaving it out here
 * is what made a scaled feature draw at its unscaled size while the Core
 * carved the scaled one.
 */
export function getFeatureBoundsMm(feature: Feature, cardW: number, cardH: number): BoundsMm {
  const box = unscaledBoundsMm(feature, cardW, cardH)
  const s = appliedScale(feature)
  return { x: box.x, y: box.y, w: box.w * s, h: box.h * s }
}

/** The scale the Core will actually apply to this feature — 1 where it
 *  places the shape without the transform's scale. */
export function appliedScale(feature: Feature): number {
  // A pocket is sized from a real insert (bore = diameter + clearance) and
  // its depth is z geometry no 2D scale can touch, so the kernel places it
  // unscaled — see build_feature_shapes() in kernel/features.py.
  if (feature.type === 'pocket') return 1
  // A pattern that fills the outline itself never sees the transform — the
  // kernel hands it outline_phys directly (same condition as here).
  if (feature.type === 'pattern' && isFacePattern(feature)) return 1
  return feature.transform.scale ?? 1
}

/** Can this feature be resized by dragging a corner handle?
 *
 *  False for the features whose size is authored numerically because it
 *  mirrors a physical part — a pocket's bore comes from the insert it holds
 *  and a hole's from what passes through it. Both are edited in the
 *  Inspector, in millimetres; a free-scale gesture on them writes a factor
 *  the Inspector never shows and, for a pocket, one the Core ignores.
 */
export function isScalable(feature: Feature): boolean {
  return feature.type !== 'pocket' && feature.type !== 'hole'
}

/** Fills the whole outline rather than a placed box — mirrors the kernel's
 *  `f.region == "face" or not (f.width and f.height)`. */
function isFacePattern(feature: Extract<Feature, { type: 'pattern' }>): boolean {
  return feature.region === 'face' || !(feature.width && feature.height)
}

function unscaledBoundsMm(feature: Feature, cardW: number, cardH: number): BoundsMm {
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
      if (isFacePattern(feature)) return { x: 0, y: 0, w: cardW, h: cardH }
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
    case 'pocket': {
      // The bore, not the insert: what gets cut is what you place. An
      // omitted clearance is not zero — it is the Core's default (see
      // _feature_from_dict in document/schema_v2.py).
      const d = feature.diameter + (feature.clearance ?? DEFAULT_POCKET_CLEARANCE)
      return { x, y, w: d, h: d }
    }
  }
}
