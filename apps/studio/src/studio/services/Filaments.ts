// Filaments — the colour helper's data and maths.
//
// Two things the wizard and the material panel both need and neither should
// invent on its own:
//   1. a library of real filament colours, so picking a colour is choosing a
//      spool you can actually buy instead of hunting in a hex wheel, and
//   2. the SAME contrast maths the Core runs (manufacturing/color.py), so the
//      Studio can warn about an unreadable pairing while you are choosing it
//      rather than after the compile.

export interface Filament {
  name: string
  color: string   // #rrggbb, lowercase
}

export interface FilamentGroup {
  label: string
  items: Filament[]
}

/** Stock filament colours, grouped the way a spool shelf is. Names are
 *  generic (no brand claims) and land straight in the material's name. */
export const FILAMENT_GROUPS: FilamentGroup[] = [
  {
    label: 'Neutrals',
    items: [
      { name: 'PLA Black', color: '#1a1a1a' },
      { name: 'PLA Charcoal', color: '#3a3a3c' },
      { name: 'PLA Grey', color: '#8b8b8d' },
      { name: 'PLA Light Grey', color: '#c4c4c6' },
      { name: 'PLA White', color: '#ffffff' },
      { name: 'PLA Ivory', color: '#f2ead3' },
    ],
  },
  {
    label: 'Metallics',
    items: [
      { name: 'PLA Gold', color: '#d4af37' },
      { name: 'PLA Bronze', color: '#a97142' },
      { name: 'PLA Copper', color: '#b87333' },
      { name: 'PLA Silver', color: '#b7bcc2' },
      { name: 'PLA Gunmetal', color: '#5a5f66' },
    ],
  },
  {
    label: 'Colours',
    items: [
      { name: 'PLA Red', color: '#c0392b' },
      { name: 'PLA Orange', color: '#e67e22' },
      { name: 'PLA Yellow', color: '#f1c40f' },
      { name: 'PLA Green', color: '#27ae60' },
      { name: 'PLA Teal', color: '#12908f' },
      { name: 'PLA Blue', color: '#1f6feb' },
      { name: 'PLA Navy', color: '#152a4e' },
      { name: 'PLA Purple', color: '#7d3cb5' },
      { name: 'PLA Pink', color: '#e84393' },
    ],
  },
  {
    label: 'Naturals',
    items: [
      { name: 'PLA Wood', color: '#9c6b3f' },
      { name: 'PLA Sand', color: '#d8c9a3' },
      { name: 'PLA Terracotta', color: '#9c4a2f' },
      { name: 'PLA Marble', color: '#e8e6e1' },
    ],
  },
]

export const ALL_FILAMENTS: Filament[] = FILAMENT_GROUPS.flatMap(g => g.items)

/** Library name for an exact colour match, else null. Lets a hand-typed hex
 *  that happens to be a stock colour still show its proper name. */
export function filamentName(color: string): string | null {
  const c = color.toLowerCase()
  return ALL_FILAMENTS.find(f => f.color === c)?.name ?? null
}

/** True when a material still carries a name the library gave it — i.e. it
 *  can follow the spool when the colour changes, without overwriting a name
 *  the user chose themselves. */
export function isLibraryName(name: string): boolean {
  return ALL_FILAMENTS.some(f => f.name === name)
}

// ── Contrast (WCAG, mirroring cardforge/manufacturing/color.py) ────────

function parseHex(color: string): [number, number, number] {
  let c = color.trim().replace('#', '')
  if (c.length === 3) c = c.split('').map(ch => ch + ch).join('')
  if (c.length !== 6) return [128, 128, 128]
  return [
    parseInt(c.slice(0, 2), 16),
    parseInt(c.slice(2, 4), 16),
    parseInt(c.slice(4, 6), 16),
  ]
}

/** WCAG relative luminance, 0 (black) … 1 (white). */
export function relativeLuminance(color: string): number {
  const lin = (v: number) => {
    const s = v / 255
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4)
  }
  const [r, g, b] = parseHex(color)
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
}

/** WCAG contrast ratio between two hex colours, 1.0 … 21.0. */
export function contrastRatio(a: string, b: string): number {
  const la = relativeLuminance(a)
  const lb = relativeLuminance(b)
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)
}

/** The Core calls a QR unreadable under this ratio (analyzer.py) — below it,
 *  a flush colour is invisible and only relief saves the feature. */
export const MIN_READABLE_CONTRAST = 2.5
/** Comfortably legible at small text sizes. */
export const GOOD_CONTRAST = 4.5

export interface ContrastVerdict {
  ratio: number
  level: 'good' | 'weak' | 'bad'
  text: string
}

/** How a colour reads against the body it sits on. */
export function judgeContrast(color: string, base: string): ContrastVerdict {
  const ratio = contrastRatio(color, base)
  if (ratio >= GOOD_CONTRAST) {
    return { ratio, level: 'good', text: `${ratio.toFixed(1)}:1 — reads clearly` }
  }
  if (ratio >= MIN_READABLE_CONTRAST) {
    return { ratio, level: 'weak', text: `${ratio.toFixed(1)}:1 — faint at small sizes` }
  }
  return { ratio, level: 'bad', text: `${ratio.toFixed(1)}:1 — too close to the body colour` }
}

/** Whichever of black/white stands out most on `base` — the safe default
 *  when the user picks a body colour and needs a legible partner. */
export function bestTextColor(base: string): Filament {
  const white = ALL_FILAMENTS.find(f => f.name === 'PLA White')!
  const black = ALL_FILAMENTS.find(f => f.name === 'PLA Black')!
  return contrastRatio(white.color, base) >= contrastRatio(black.color, base) ? white : black
}

// ── Curated palettes ──────────────────────────────────────────────────

export interface PaletteEntry {
  name: string
  color: string
  role: 'base' | 'text' | 'accent'
}

export interface Palette {
  key: string
  label: string
  entries: PaletteEntry[]
}

/** Ready-made combinations. Every one clears MIN_READABLE_CONTRAST between
 *  its body colour and the rest — picking one can't paint you into an
 *  invisible card. The first entry is always the body (role 'base'). */
export const PALETTES: Palette[] = [
  {
    key: 'classic', label: 'Classic',
    entries: [
      { name: 'PLA Black', color: '#1a1a1a', role: 'base' },
      { name: 'PLA White', color: '#ffffff', role: 'text' },
    ],
  },
  {
    key: 'blackgold', label: 'Black & Gold',
    entries: [
      { name: 'PLA Black', color: '#1a1a1a', role: 'base' },
      { name: 'PLA White', color: '#ffffff', role: 'text' },
      { name: 'PLA Gold', color: '#d4af37', role: 'accent' },
    ],
  },
  {
    key: 'paper', label: 'Paper',
    entries: [
      { name: 'PLA White', color: '#ffffff', role: 'base' },
      { name: 'PLA Black', color: '#1a1a1a', role: 'text' },
      { name: 'PLA Red', color: '#c0392b', role: 'accent' },
    ],
  },
  {
    key: 'navy', label: 'Navy & Ivory',
    entries: [
      { name: 'PLA Navy', color: '#152a4e', role: 'base' },
      { name: 'PLA Ivory', color: '#f2ead3', role: 'text' },
      { name: 'PLA Copper', color: '#b87333', role: 'accent' },
    ],
  },
  {
    key: 'slate', label: 'Slate & Orange',
    entries: [
      { name: 'PLA Charcoal', color: '#3a3a3c', role: 'base' },
      { name: 'PLA Light Grey', color: '#c4c4c6', role: 'text' },
      { name: 'PLA Orange', color: '#e67e22', role: 'accent' },
    ],
  },
  {
    key: 'wood', label: 'Wood & Black',
    entries: [
      { name: 'PLA Wood', color: '#9c6b3f', role: 'base' },
      { name: 'PLA Black', color: '#1a1a1a', role: 'text' },
      { name: 'PLA Ivory', color: '#f2ead3', role: 'accent' },
    ],
  },
  {
    key: 'mono', label: 'Silver & Black',
    entries: [
      { name: 'PLA Silver', color: '#b7bcc2', role: 'base' },
      { name: 'PLA Black', color: '#1a1a1a', role: 'text' },
    ],
  },
  {
    key: 'teal', label: 'Teal & Sand',
    entries: [
      { name: 'PLA Teal', color: '#12908f', role: 'base' },
      { name: 'PLA Sand', color: '#d8c9a3', role: 'text' },
      { name: 'PLA Charcoal', color: '#3a3a3c', role: 'accent' },
    ],
  },
]
