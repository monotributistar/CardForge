// SVG import — file → inline SVG, fill-color detection, and color→material
// mapping. Mirrors the kernel's parsing rules (svg.py): shapes without an
// explicit fill (or fill="none") are skipped, and colors are normalized to
// lowercase #rrggbb so the colorMap keys match svgelements' hexrgb output.

import type { DocumentV2, Feature, Material } from '../../types/cardforge'

const SHAPE_SELECTOR = 'path, rect, circle, ellipse, polygon, polyline'

let _ctx: CanvasRenderingContext2D | null = null

/** Any CSS color → lowercase #rrggbb (null if unparseable). */
export function normalizeColor(c: string): string | null {
  if (!_ctx) _ctx = document.createElement('canvas').getContext('2d')
  if (!_ctx) return null
  _ctx.fillStyle = '#000'
  _ctx.fillStyle = c
  const v = _ctx.fillStyle
  if (v.startsWith('#')) return v.length === 4
    ? `#${v[1]}${v[1]}${v[2]}${v[2]}${v[3]}${v[3]}`.toLowerCase()
    : v.slice(0, 7).toLowerCase()
  const m = v.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/)
  if (!m) return null
  const hex = (n: string) => Number(n).toString(16).padStart(2, '0')
  return `#${hex(m[1])}${hex(m[2])}${hex(m[3])}`
}

function fillOf(el: Element): string | null {
  const style = el.getAttribute('style')
  const styleFill = style?.match(/fill\s*:\s*([^;]+)/)?.[1]?.trim()
  const fill = styleFill
    ?? el.getAttribute('fill')
    ?? el.closest('[fill]')?.getAttribute('fill')
    ?? null
  if (!fill || fill === 'none') return null
  return normalizeColor(fill)
}

/** Distinct fill colors of an SVG in document order (#rrggbb, lowercase). */
export function extractSvgFillColors(svgText: string): string[] {
  const dom = new DOMParser().parseFromString(svgText, 'image/svg+xml')
  if (dom.querySelector('parsererror')) return []
  const out: string[] = []
  const seen = new Set<string>()
  dom.querySelectorAll(SHAPE_SELECTOR).forEach(el => {
    const hex = fillOf(el)
    if (hex && !seen.has(hex)) { seen.add(hex); out.push(hex) }
  })
  return out
}

/** Concatenated `d` data of every <path> — for `path` outlines. */
export function extractSvgPathD(svgText: string): string {
  const dom = new DOMParser().parseFromString(svgText, 'image/svg+xml')
  if (dom.querySelector('parsererror')) return ''
  return [...dom.querySelectorAll('path')]
    .map(p => p.getAttribute('d') ?? '')
    .filter(Boolean)
    .join(' ')
}

function uniqueMaterialId(doc: DocumentV2, base: string): string {
  if (!doc.materials.some(m => m.id === base)) return base
  let n = 2
  while (doc.materials.some(m => m.id === `${base}-${n}`)) n++
  return `${base}-${n}`
}

/** Material for every color — reuses same-color materials, creates the
 * missing ones (next free slot). Returns the colorMap {hex → material id}. */
export function ensureMaterialsForColors(doc: DocumentV2, colors: string[]): Record<string, string> {
  const map: Record<string, string> = {}
  for (const hex of colors) {
    let mat = doc.materials.find(m => m.color.toLowerCase() === hex)
    if (!mat) {
      const used = new Set(doc.materials.map(m => m.slot).filter((s): s is number => s != null))
      let slot = 1
      while (used.has(slot)) slot++
      mat = {
        id: uniqueMaterialId(doc, `svg-${hex.slice(1)}`),
        name: `SVG ${hex}`,
        color: hex,
        slot,
        role: 'detail',
      } satisfies Material
      doc.materials.push(mat)
    }
    map[hex] = mat.id
  }
  return map
}

/** Set an SVG on a feature (icon or svg-pattern): stores it inline and maps
 * every fill color to a material, creating materials as needed. Use inside
 * applyEdit. Returns the number of colors found. */
export function applySvgToFeature(doc: DocumentV2, featureId: string, svgText: string): number {
  for (const face of Object.values(doc.faces)) {
    const f = face?.features.find((x: Feature) => x.id === featureId)
    if (!f) continue
    const colors = extractSvgFillColors(svgText)
    const anyF = f as Feature & { svgInline?: string; svgAsset?: string; colorMap?: Record<string, string> }
    anyF.svgInline = svgText
    delete anyF.svgAsset
    if (colors.length) anyF.colorMap = ensureMaterialsForColors(doc, colors)
    else delete anyF.colorMap
    return colors.length
  }
  return 0
}
