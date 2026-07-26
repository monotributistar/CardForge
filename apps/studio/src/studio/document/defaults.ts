// Document defaults — factory for new documents and features.

import type { DocumentV2, Feature, FaceId, Outline, Material, HoleFeature, IconFeature, PocketFeature, TextBlockFeature } from '../../types/cardforge'
import { DEFAULT_POCKET_CLEARANCE, DEFAULT_POCKET_DEPTH_CLEARANCE } from '../../types/cardforge'

function uid(prefix: string): string {
  const rand = typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID().slice(0, 8)
    : Math.random().toString(36).slice(2, 10)
  return `${prefix}-${rand}`
}

/** A fresh 85×54×1.8 business card with three materials and starter features. */
export function createNewDocument(): DocumentV2 {
  const now = new Date().toISOString()
  return {
    cardforge: '2.0',
    meta: {
      id: uid('doc'),
      name: 'Untitled Card',
      created: now,
      modified: now,
    },
    object: {
      outline: { type: 'rounded-rect', width: 85, height: 54, radius: 4 },
      thickness: 1.8,
    },
    manufacturing: { process: 'fdm', nozzle: 0.4, layerHeight: 0.2 },
    materials: [
      { id: 'base', name: 'PLA Negro', color: '#1a1a1a', slot: 1, role: 'base' },
      { id: 'text', name: 'PLA Blanco', color: '#ffffff', slot: 2, role: 'text' },
      { id: 'accent', name: 'PLA Dorado', color: '#d4af37', slot: 3, role: 'accent' },
    ],
    faces: {
      front: {
        features: [
          {
            id: uid('text-block'),
            type: 'text-block',
            name: 'Name',
            transform: { x: 8, y: 10 },
            material: 'text',
            relief: { mode: 'emboss', height: 0.4 },
            lines: ['Tu Nombre'],
            font: { family: 'Helvetica Neue', size: 6, weight: 700 },
            align: 'left',
          },
        ],
      },
      // Back is the bed-facing face — it must stay flat, so its features are
      // flush inlays (colour imprinted level with the surface), never emboss.
      back: {
        features: [
          {
            id: uid('qr'),
            type: 'qr',
            name: 'QR',
            transform: { x: 30.5, y: 10 },
            material: 'text',
            relief: { mode: 'flush', depth: 0.4 },
            qrType: 'url',
            fields: { url: 'https://example.com' },
            size: 24,
            errorCorrection: 'M',
          },
          {
            id: uid('text-block'),
            type: 'text-block',
            name: 'Caption',
            transform: { x: 30.5, y: 40 },
            material: 'text',
            relief: { mode: 'flush', depth: 0.4 },
            lines: ['example.com'],
            font: { family: 'Helvetica Neue', size: 6 },
            align: 'left',
          },
        ],
      },
    },
  }
}

/** Sensible default feature of a given type, placed at x:10, y:10.
 *  Back (bed-facing) features default to a flush inlay — the back must stay
 *  flat, so emboss is not offered there. Front features emboss (raised). */
export function defaultFeature(type: Feature['type'], face: FaceId, materialId = 'text'): Feature {
  const relief = face === 'back'
    ? { mode: 'flush' as const, depth: 0.4 }
    : { mode: 'emboss' as const, height: 0.4 }
  const base = {
    id: uid(type),
    transform: { x: 10, y: 10 },
    material: materialId,
    relief,
  }
  switch (type) {
    case 'text-block':
      return {
        ...base, type,
        lines: ['New text'],
        font: { family: 'Helvetica Neue', size: 6 },
        align: 'left',
      }
    case 'text-pattern':
      return {
        ...base, type,
        text: 'PATTERN',
        font: { family: 'Helvetica Neue', size: 3 },
        spacing: 6,
        angle: 0,
      }
    case 'pattern':
      return {
        ...base, type,
        patternType: 'dots',
        spacing: 4,
        elementSize: 1,
        region: 'bounds',
        width: 20,
        height: 20,
      }
    case 'qr':
      return {
        ...base, type,
        qrType: 'url',
        fields: { url: 'https://example.com' },
        size: 20,
        errorCorrection: 'M',
      }
    case 'icon':
      return {
        ...base, type,
        width: 12,
        height: 12,
        svgInline: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#ffffff"/></svg>',
      }
    case 'shape':
      return {
        ...base, type,
        shapeType: 'rect',
        width: 20,
        height: 10,
      }
    case 'hole':
      // A hole is always a through-cut; relief mode is fixed.
      return {
        ...base, type,
        relief: { mode: 'cut' },
        holeType: 'circle',
        diameter: 5,
      }
    case 'pocket':
      // A pocket owns its own z geometry (depth + ceiling), so relief is
      // fixed and hidden — same contract as a hole. Defaults to the most
      // common insert: a Ø6×2 neodymium disc magnet, open at the surface.
      return {
        ...base, type,
        relief: { mode: 'cut' },
        pocketType: 'circle',
        insert: 'magnet',
        diameter: 6,
        depth: 2,
        clearance: DEFAULT_POCKET_CLEARANCE,
        depthClearance: DEFAULT_POCKET_DEPTH_CLEARANCE,
      }
  }
}

/** Two-color stand-in until the real artwork is uploaded — it shows what a
 *  logo feature is for: one material per fill color. */
const LOGO_PLACEHOLDER =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">'
  + '<circle cx="24" cy="24" r="22" fill="#1f6feb"/>'
  + '<path d="M14 31 L24 12 L34 31 Z" fill="#ffffff"/></svg>'

/** Multicolor logo artwork placed ON a face — as opposed to an SVG used as
 *  the object's own outline. Flush by default on both faces: the colors sit
 *  level with the surface (raised pads would make the front bumpy, and the
 *  bed-facing back cannot carry them at all). Height is left off so the
 *  artwork keeps its aspect ratio. */
export function defaultLogoFeature(materialId = 'text'): IconFeature {
  return {
    id: uid('logo'),
    type: 'icon',
    name: 'Logo',
    transform: { x: 10, y: 10 },
    material: materialId,
    relief: { mode: 'flush', depth: 0.6 },
    width: 30,
    svgInline: LOGO_PLACEHOLDER,
  }
}

// ── New-card wizard ────────────────────────────────────────────────────

/** Insert pockets the wizard can drop in, with the sizes people actually
 *  buy. `minThickness` is what the body needs to carry one: the cavity plus
 *  the fit slack plus a floor thick enough not to crack (see the pocket
 *  constraints in the Core). */
export interface WizardPocket {
  key: string
  label: string
  insert: PocketFeature['insert']
  diameter: number
  depth: number
}

export const WIZARD_POCKETS: WizardPocket[] = [
  { key: 'magnet6', label: 'Magnet Ø6 × 2 mm', insert: 'magnet', diameter: 6, depth: 2 },
  { key: 'magnet8', label: 'Magnet Ø8 × 3 mm', insert: 'magnet', diameter: 8, depth: 3 },
  { key: 'magnet10', label: 'Magnet Ø10 × 2 mm', insert: 'magnet', diameter: 10, depth: 2 },
  { key: 'rfid25', label: 'RFID / NFC tag Ø25 × 0.9 mm', insert: 'rfid', diameter: 25, depth: 0.9 },
]

/** Thinnest body that can hold this insert: cavity + a floor that survives. */
export const MIN_POCKET_FLOOR = 0.8
export function minThicknessForPocket(p: WizardPocket): number {
  return Math.round((p.depth + DEFAULT_POCKET_DEPTH_CLEARANCE + MIN_POCKET_FLOOR) * 10) / 10
}

export interface WizardOptions {
  name: string
  outline: Outline
  thickness: number
  nozzle: number
  /** Full palette, in slot order. Exactly one carries role 'base' (the card
   *  body); features are assigned the first non-base material. */
  materials: Material[]
  hole: 'none' | 'keyring' | 'lanyard'
  /** Material lug around the hole (lets it sit on/past the edge). */
  holeTab: boolean
  /** Insert pocket (magnet / RFID tag), or none. */
  pocket?: WizardPocket | null
  /** Add a starter 6mm name text-block on the front. */
  sampleText: boolean
  /** Starter content on the back (bed-facing) face — flush inlays, the only
   *  thing that face can carry besides carving. Used when the front is taken
   *  by an SVG logo and the back is the writable side. */
  backStarter?: 'none' | 'text-qr'
}

/** Where a wizard pocket sits: clear of the left-aligned starter text on a
 *  rectangular card, dead centre on a disc. */
function pocketAnchor(o: WizardOptions, bore: number): { x: number; y: number } {
  const W = o.outline.type === 'circle' ? o.outline.diameter : o.outline.width
  const H = o.outline.type === 'circle' ? o.outline.diameter : o.outline.height
  const cx = o.outline.type === 'circle' || bore > W * 0.5 ? W / 2 : W * 0.72
  return {
    x: Math.round((cx - bore / 2) * 10) / 10,
    y: Math.round((H / 2 - bore / 2) * 10) / 10,
  }
}

/** Build a full v2 document from the wizard's selections. */
export function buildWizardDocument(o: WizardOptions): DocumentV2 {
  const now = new Date().toISOString()
  const W = o.outline.type === 'circle' ? o.outline.diameter : o.outline.width
  const H = o.outline.type === 'circle' ? o.outline.diameter : o.outline.height

  const materials: Material[] = o.materials.map((m, i) => ({ ...m, slot: m.slot ?? i + 1 }))
  const baseId = (materials.find(m => m.role === 'base') ?? materials[0]).id
  // What starter content prints in: the first colour that isn't the body.
  const inkId = (materials.find(m => m.role === 'text')
    ?? materials.find(m => m.id !== baseId)
    ?? materials[0]).id

  const front: Feature[] = []

  if (o.hole === 'keyring') {
    // Circle Ø5 centered on the left edge — with the tab it reads as a
    // classic keyring ear; without it the constraint layer warns (open notch).
    const hole: HoleFeature = {
      id: uid('hole'), type: 'hole', name: 'Keyring hole',
      transform: { x: o.holeTab ? -2.5 : 2.5, y: H / 2 - 2.5 },
      material: baseId, relief: { mode: 'cut' },
      holeType: 'circle', diameter: 5,
      ...(o.holeTab ? { tab: true, tabMargin: 3 } : {}),
    }
    front.push(hole)
  } else if (o.hole === 'lanyard') {
    // Slot 14×5 top-center, fully inside — the credential/badge classic.
    const hole: HoleFeature = {
      id: uid('hole'), type: 'hole', name: 'Lanyard slot',
      transform: { x: W / 2 - 7, y: 3 },
      material: baseId, relief: { mode: 'cut' },
      holeType: 'slot', width: 14, height: 5,
      ...(o.holeTab ? { tab: true, tabMargin: 3 } : {}),
    }
    front.push(hole)
  }

  if (o.pocket) {
    // Open at the front surface (ceiling 0): nothing to bridge, and the
    // insert drops in after the print instead of needing a pause.
    const p = o.pocket
    const bore = p.diameter + DEFAULT_POCKET_CLEARANCE
    const pocket: PocketFeature = {
      id: uid('pocket'), type: 'pocket',
      name: p.insert === 'rfid' ? 'RFID pocket' : 'Magnet pocket',
      transform: pocketAnchor(o, bore),
      material: baseId, relief: { mode: 'cut' },
      pocketType: 'circle', insert: p.insert,
      diameter: p.diameter, depth: p.depth,
      clearance: DEFAULT_POCKET_CLEARANCE,
      depthClearance: DEFAULT_POCKET_DEPTH_CLEARANCE,
    }
    front.push(pocket)
  }

  if (o.sampleText) {
    const text: TextBlockFeature = {
      id: uid('text-block'), type: 'text-block', name: 'Name',
      transform: { x: Math.max(6, W * 0.1), y: Math.max(4, H / 2 - 4) },
      material: inkId, relief: { mode: 'emboss', height: 0.4 },
      lines: ['Your Name'],
      font: { family: 'Helvetica Neue', size: 6, weight: 700 },
      align: 'left',
    }
    front.push(text)
  }

  // Back = bed-facing: flush inlays only, and its content is authored in
  // back-face space (the kernel mirrors it into place).
  const back: Feature[] = []
  if (o.backStarter === 'text-qr') {
    // Anchored to the bottom: caption on the last line, QR above it. On a
    // logo silhouette the shape is usually widest low down, so this clips
    // less than a top-aligned block would (and the Core flags what it does
    // clip). The gap clears the QR's quiet zone — anything inside it blocks
    // scanning.
    const quietZone = 2
    const captionSize = 4
    const qrSize = Math.min(24, Math.max(14, Math.min(W, H) * 0.45))
    const captionY = Math.max(3, H - 4 - captionSize)
    const qrY = Math.max(3, captionY - qrSize - 2 * quietZone - 2)
    back.push({
      id: uid('qr'), type: 'qr', name: 'QR',
      transform: { x: (W - qrSize) / 2, y: qrY },
      material: inkId, relief: { mode: 'flush', depth: 0.4 },
      qrType: 'url', fields: { url: 'https://example.com' },
      size: qrSize, errorCorrection: 'M', quietZone,
    })
    back.push({
      id: uid('text-block'), type: 'text-block', name: 'Caption',
      transform: { x: Math.max(4, W * 0.1), y: captionY },
      material: inkId, relief: { mode: 'flush', depth: 0.4 },
      lines: ['example.com'],
      font: { family: 'Helvetica Neue', size: captionSize, weight: 700 },
      align: 'left',
    })
  }

  return {
    cardforge: '2.0',
    meta: { id: uid('doc'), name: o.name || 'Untitled Card', created: now, modified: now },
    object: { outline: o.outline, thickness: o.thickness },
    manufacturing: { process: 'fdm', nozzle: o.nozzle, layerHeight: 0.2 },
    materials,
    faces: { front: { features: front }, back: { features: back } },
  }
}
