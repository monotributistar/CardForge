// SVG import — file → inline SVG, fill-color detection, and color→material
// mapping. Mirrors the kernel's parsing rules (svg.py): shapes without an
// explicit fill (or fill="none") are skipped, and colors are normalized to
// lowercase #rrggbb so the colorMap keys match svgelements' hexrgb output.

import type { DocumentV2, Feature, Material } from '../../types/cardforge'

const SHAPE_SELECTOR = 'path, rect, circle, ellipse, polygon, polyline, line'

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

function paintOf(el: Element, prop: 'fill' | 'stroke'): string | null {
  const style = el.getAttribute('style')
  const styleVal = style?.match(new RegExp(`${prop}\\s*:\\s*([^;]+)`))?.[1]?.trim()
  const val = styleVal
    ?? el.getAttribute(prop)
    ?? el.closest(`[${prop}]`)?.getAttribute(prop)
    ?? null
  // SVG spec default: fill is black when unspecified, stroke is none.
  if (val === null) return prop === 'fill' ? '#000000' : null
  if (val === 'none') return null
  // currentColor resolves to black in the kernel (no CSS cascade there)
  if (val === 'currentColor') return '#000000'
  return normalizeColor(val)
}

/** Distinct colors of an SVG in document order (#rrggbb, lowercase).
 * Mirrors the kernel (svg.py): missing fill defaults to black, `none` is
 * skipped, and stroked shapes contribute their stroke color too. */
export function extractSvgFillColors(svgText: string): string[] {
  const dom = new DOMParser().parseFromString(svgText, 'image/svg+xml')
  if (dom.querySelector('parsererror')) return []
  const out: string[] = []
  const seen = new Set<string>()
  const add = (hex: string | null) => {
    if (hex && !seen.has(hex)) { seen.add(hex); out.push(hex) }
  }
  dom.querySelectorAll(SHAPE_SELECTOR).forEach(el => {
    add(paintOf(el, 'fill'))
    add(paintOf(el, 'stroke'))
  })
  return out
}

/** Natural width/height of an SVG: viewBox, else width/height attributes,
 * else the rendered bounding box (hidden off-screen measurement). */
export function svgNaturalSize(svgText: string): { width: number; height: number } | null {
  const dom = new DOMParser().parseFromString(svgText, 'image/svg+xml')
  const root = dom.querySelector('svg')
  if (!root || dom.querySelector('parsererror')) return null
  const vb = root.getAttribute('viewBox')?.trim().split(/[\s,]+/).map(Number)
  if (vb?.length === 4 && vb[2] > 0 && vb[3] > 0) return { width: vb[2], height: vb[3] }
  const w = parseFloat(root.getAttribute('width') ?? '')
  const h = parseFloat(root.getAttribute('height') ?? '')
  if (w > 0 && h > 0) return { width: w, height: h }
  // Last resort: mount off-screen and measure the artwork's bbox
  const holder = document.createElement('div')
  holder.style.cssText = 'position:absolute;left:-9999px;top:-9999px;visibility:hidden'
  holder.innerHTML = svgText
  document.body.appendChild(holder)
  try {
    const box = (holder.querySelector('svg') as SVGSVGElement | null)?.getBBox()
    if (box && box.width > 0 && box.height > 0) return { width: box.width, height: box.height }
  } catch { /* detached/foreign SVG — fall through */ } finally {
    holder.remove()
  }
  return null
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

/** Default depth of the multicolor layer on a freshly imported SVG shape:
 * three 0.2mm layers — enough for the color to read, cheap in filament, and
 * it leaves the rest of the body (and the other face) in base material. */
export const DEFAULT_COLOR_DEPTH = 0.6

/** The color layer has to stay inside the body — the Core rejects a depth at
 * or past the thickness (that IS the through-column case). Returns undefined
 * for "through", which is how the absence of colorDepth reads. */
export function clampColorDepth(depth: number | undefined, thickness: number): number | undefined {
  if (!depth || depth <= 0) return undefined
  return round2(Math.min(depth, thickness / 2))
}

export interface ColorLayerOptions {
  /** Depth of the color layer in mm; 0/undefined = colors run through. */
  colorDepth?: number
  colorFace?: 'front' | 'back' | 'both'
}

/** Use an SVG file as the card's outline (main shape): stores the full
 * markup (the kernel resolves transforms and every shape element), keeps the
 * artwork's aspect ratio, and maps every color to a material so the base
 * extrudes multicolor. By default the colors are a DEFAULT_COLOR_DEPTH layer
 * on the front, so the back stays a clean base-material canvas; re-importing
 * over an existing SVG shape keeps whatever layer settings it had.
 * Mutates `doc` — use inside applyEdit or on a freshly built document.
 * Returns the number of colors found (0 = parse failure). */
export function applySvgOutline(doc: DocumentV2, svgText: string, targetWidth?: number,
                                opts: ColorLayerOptions = {}): number {
  const colors = extractSvgFillColors(svgText)
  if (!colors.length) return 0
  const prev = doc.object.outline
  const width = targetWidth
    ?? (prev.type === 'circle' ? prev.diameter : prev.width)
    ?? 85
  const nat = svgNaturalSize(svgText)
  const height = nat ? width * (nat.height / nat.width)
    : (prev.type === 'circle' ? prev.diameter : prev.height) ?? 54
  const keep = prev.type === 'path' && prev.svgInline
  const depth = opts.colorDepth ?? (keep ? prev.colorDepth : DEFAULT_COLOR_DEPTH)
  const colorDepth = clampColorDepth(depth, doc.object.thickness)
  const colorFace = opts.colorFace ?? (keep ? prev.colorFace : undefined) ?? 'front'
  doc.object.outline = {
    type: 'path',
    svgPath: extractSvgPathD(svgText), // 2D-canvas fallback only
    svgInline: svgText,
    colorMap: ensureMaterialsForColors(doc, colors),
    ...(colorDepth ? { colorDepth, ...(colorFace !== 'front' ? { colorFace } : {}) } : {}),
    width: round2(width),
    height: round2(height),
  }
  return colors.length
}

const round2 = (n: number) => Math.round(n * 100) / 100

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
