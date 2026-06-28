// Canvas coordinates — convert between Document (mm) and Screen (pixels)
//
// Document: top-left origin, mm units, card bounds 0..w, 0..h
// Screen: top-left origin, px units, zoom applied

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
  const PX = 4 // must match CompileService PX_PER_MM
  const scaledW = cardWidth * PX * viewport.zoom
  const scaledH = cardHeight * PX * viewport.zoom
  const cx = (containerWidth - scaledW) / 2 + viewport.offsetX
  const cy = (containerHeight - scaledH) / 2 + viewport.offsetY
  return {
    x: cx + docX * PX * viewport.zoom,
    y: cy + docY * PX * viewport.zoom,
  }
}

/** Convert screen pixel coordinates to document mm coordinates */
export function screenToDocument(
  screenX: number, screenY: number,
  cardWidth: number, cardHeight: number,
  viewport: CanvasViewport,
  containerWidth: number, containerHeight: number,
): { x: number; y: number } {
  const PX = 4
  const scaledW = cardWidth * PX * viewport.zoom
  const scaledH = cardHeight * PX * viewport.zoom
  const cx = (containerWidth - scaledW) / 2 + viewport.offsetX
  const cy = (containerHeight - scaledH) / 2 + viewport.offsetY
  return {
    x: Math.max(0, Math.min(cardWidth, (screenX - cx) / (PX * viewport.zoom))),
    y: Math.max(0, Math.min(cardHeight, (screenY - cy) / (PX * viewport.zoom))),
  }
}

/** Get feature bounds in document mm */
export function getFeatureBounds(feature: any): { x: number; y: number; w: number; h: number } | null {
  if (!feature.position) return null
  const size = feature.size
  const w = typeof size === 'number' ? size : size?.width ?? 20
  const h = typeof size === 'number' ? size : size?.height ?? 10
  return { x: feature.position.x, y: feature.position.y, w, h }
}
