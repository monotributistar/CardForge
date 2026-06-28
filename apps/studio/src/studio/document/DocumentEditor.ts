// DocumentState — mutable document model for Studio editing
//
// This is the single source of truth for the open document.
// All edits go through commands, which mutate this state.
// The CompileService reads this state to generate previews.

import type { CardForgeDocument, DocumentObject, Feature } from '../../types/cardforge'

export interface EditableFeature {
  id: string
  type: string
  lines: string[]
  font: string
  fontSize: number
  fontStyle: string
  material: string
  reliefMode: string
  reliefHeight: number
  reliefDepth: number
  value: string  // for QR
  size: number   // for QR
  position: { x: number; y: number }
  zIndex: number
}

export interface DocumentState {
  document: CardForgeDocument | null
  variables: Record<string, string>
  features: EditableFeature[]
}

const DEFAULT_VARIABLES = {
  name: 'Your Name',
  title: 'Your Title',
  email: 'you@example.com',
  website: 'https://example.com',
  phone: '+54 351 123 4567',
}

/** Create a new blank business card document */
export function createNewDocument(): CardForgeDocument {
  return {
    document: { id: 'new-card', name: 'New Business Card', version: '0.1.0' },
    manufacturing: { profile: 'fdm-standard', process: 'fdm', nozzle: 0.4, layerHeight: 0.2, material: 'PLA' },
    variables: { ...DEFAULT_VARIABLES },
    objects: [{
      id: 'main-card', type: 'business-card',
      width: 85, height: 54, thickness: 1.8, cornerRadius: 4,
      theme: { name: 'dark-luxury', baseColor: 'black', textColor: 'white', accentColor: 'gold' },
      faces: {
        front: { features: [
          { id: 'front-name', type: 'text-block', position: { x: 42.5, y: 20 },
            font: 'Montserrat', fontSize: 4.0, fontStyle: 'bold', align: 'center',
            lines: ['{{name}}'], material: 'text', relief: { mode: 'emboss', height: 0.4 }, zIndex: 1, size: { width: 70, height: 10 } },
          { id: 'front-title', type: 'text-block', position: { x: 42.5, y: 28 },
            font: 'Montserrat', fontSize: 3.0, fontStyle: 'regular', align: 'center',
            lines: ['{{title}}'], material: 'text', relief: { mode: 'emboss', height: 0.4 }, zIndex: 1, size: { width: 70, height: 10 } },
        ] },
        back: { features: [
          { id: 'contact', type: 'text-block', position: { x: 8, y: 12 },
            font: 'Montserrat', fontSize: 3.2, fontStyle: 'semibold', align: 'left',
            lines: ['{{name}}', '{{title}}', '{{email}}', '{{website}}'],
            material: 'text', relief: { mode: 'emboss', height: 0.4 }, zIndex: 1, size: { width: 40, height: 20 } },
          { id: 'qr', type: 'qr', position: { x: 56, y: 15 },
            value: '{{website}}', size: 24,
            material: 'text', relief: { mode: 'emboss', height: 0.4 }, zIndex: 2 },
        ] },
      },
    }],
    exports: { preview: true, manufacturingReport: true, singleStl: true, colorSeparatedStl: true, threeMf: false },
  }
}

/** Extract editable features from a document */
export function extractFeatures(doc: CardForgeDocument | null): EditableFeature[] {
  if (!doc) return []
  const result: EditableFeature[] = []
  for (const obj of doc.objects) {
    for (const [_faceId, face] of Object.entries(obj.faces)) {
      for (const feat of face.features) {
        result.push({
          id: feat.id,
          type: feat.type,
          lines: feat.lines ?? [],
          font: feat.font ?? 'Montserrat',
          fontSize: feat.fontSize ?? 3.0,
          fontStyle: feat.fontStyle ?? 'regular',
          material: feat.material ?? 'base',
          reliefMode: feat.relief?.mode ?? 'emboss',
          reliefHeight: feat.relief?.height ?? 0.4,
          reliefDepth: feat.relief?.depth ?? 0.2,
          value: feat.value ?? '',
          size: typeof feat.size === 'number' ? feat.size : (feat.size as any)?.width ?? 24,
          position: feat.position ?? { x: 0, y: 0 },
          zIndex: feat.zIndex ?? 0,
        })
      }
    }
  }
  return result
}

/** Find a feature in the document by ID */
export function findFeature(doc: CardForgeDocument, featureId: string): Feature | null {
  for (const obj of doc.objects) {
    for (const face of Object.values(obj.faces)) {
      for (const feat of face.features) {
        if (feat.id === featureId) return feat
      }
    }
  }
  return null
}

/** Update a feature's field in the document */
export function updateFeatureField(doc: CardForgeDocument, featureId: string, field: string, value: any): boolean {
  for (const obj of doc.objects) {
    for (const face of Object.values(obj.faces)) {
      for (const feat of face.features) {
        if (feat.id !== featureId) continue
        if (field === 'lines') (feat as any).lines = value
        else if (field === 'fontSize') (feat as any).fontSize = value
        else if (field === 'reliefHeight' && feat.relief) feat.relief.height = value
        else if (field === 'material') (feat as any).material = value
        else if (field === 'value') (feat as any).value = value
        else if (field === 'size') {
          if (typeof feat.size === 'number') (feat as any).size = value
          else if (feat.size) (feat.size as any).width = value
          else (feat as any).size = value
        }
        return true
      }
    }
  }
  return false
}

/** Update a document variable */
export function updateDocumentVariable(doc: CardForgeDocument, key: string, value: string): void {
  doc.variables[key] = value
}
