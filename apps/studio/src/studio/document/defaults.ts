// Document defaults — factory for new documents and features.

import type { DocumentV2, Feature, FaceId, Outline, Material, HoleFeature, TextBlockFeature } from '../../types/cardforge'

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
  }
}

// ── New-card wizard ────────────────────────────────────────────────────

export interface WizardOptions {
  name: string
  outline: Outline
  thickness: number
  nozzle: number
  baseColor: string
  baseName: string
  textColor: string
  textName: string
  /** Accent material is optional (multicolor palettes only). */
  accentColor?: string
  accentName?: string
  hole: 'none' | 'keyring' | 'lanyard'
  /** Material lug around the hole (lets it sit on/past the edge). */
  holeTab: boolean
  /** Add a starter 6mm name text-block on the front. */
  sampleText: boolean
}

/** Build a full v2 document from the wizard's selections. */
export function buildWizardDocument(o: WizardOptions): DocumentV2 {
  const now = new Date().toISOString()
  const W = o.outline.type === 'circle' ? o.outline.diameter : o.outline.width
  const H = o.outline.type === 'circle' ? o.outline.diameter : o.outline.height

  const materials: Material[] = [
    { id: 'base', name: o.baseName, color: o.baseColor, slot: 1, role: 'base' },
    { id: 'text', name: o.textName, color: o.textColor, slot: 2, role: 'text' },
  ]
  if (o.accentColor) {
    materials.push({ id: 'accent', name: o.accentName || 'Accent', color: o.accentColor, slot: 3, role: 'accent' })
  }

  const front: Feature[] = []

  if (o.hole === 'keyring') {
    // Circle Ø5 centered on the left edge — with the tab it reads as a
    // classic keyring ear; without it the constraint layer warns (open notch).
    const hole: HoleFeature = {
      id: uid('hole'), type: 'hole', name: 'Keyring hole',
      transform: { x: o.holeTab ? -2.5 : 2.5, y: H / 2 - 2.5 },
      material: 'base', relief: { mode: 'cut' },
      holeType: 'circle', diameter: 5,
      ...(o.holeTab ? { tab: true, tabMargin: 3 } : {}),
    }
    front.push(hole)
  } else if (o.hole === 'lanyard') {
    // Slot 14×5 top-center, fully inside — the credential/badge classic.
    const hole: HoleFeature = {
      id: uid('hole'), type: 'hole', name: 'Lanyard slot',
      transform: { x: W / 2 - 7, y: 3 },
      material: 'base', relief: { mode: 'cut' },
      holeType: 'slot', width: 14, height: 5,
      ...(o.holeTab ? { tab: true, tabMargin: 3 } : {}),
    }
    front.push(hole)
  }

  if (o.sampleText) {
    const text: TextBlockFeature = {
      id: uid('text-block'), type: 'text-block', name: 'Name',
      transform: { x: Math.max(6, W * 0.1), y: Math.max(4, H / 2 - 4) },
      material: 'text', relief: { mode: 'emboss', height: 0.4 },
      lines: ['Your Name'],
      font: { family: 'Helvetica Neue', size: 6, weight: 700 },
      align: 'left',
    }
    front.push(text)
  }

  return {
    cardforge: '2.0',
    meta: { id: uid('doc'), name: o.name || 'Untitled Card', created: now, modified: now },
    object: { outline: o.outline, thickness: o.thickness },
    manufacturing: { process: 'fdm', nozzle: o.nozzle, layerHeight: 0.2 },
    materials,
    faces: { front: { features: front }, back: { features: [] } },
  }
}
