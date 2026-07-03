// Manufacturing Pipeline types for Studio

import type { CardForgeDocument } from '../../types/cardforge'

export type ManufacturingProcess = 'fdm' | 'sla' | 'laser' | 'cnc'

export interface ManufacturingConfig {
  process: ManufacturingProcess
  profile: string
  presentationFace: 'front' | 'back'
  preferredPrintFace: 'front' | 'back'
  outputs: {
    preview: boolean
    scad: boolean
    stl: boolean
    separatedStl: boolean
    report: boolean
  }
}

export const PROCESSES: { id: ManufacturingProcess; label: string; profiles: string[] }[] = [
  { id: 'fdm', label: 'FDM (3D Print)', profiles: ['Standard 0.4mm', 'Fine 0.25mm', 'Draft 0.6mm'] },
  { id: 'sla', label: 'SLA (Resin)', profiles: ['Standard 0.05mm', 'Fine 0.025mm'] },
  { id: 'laser', label: 'Laser Cut/Engrave', profiles: ['Standard', 'Fine Detail'] },
  { id: 'cnc', label: 'CNC Mill', profiles: ['Standard', 'Fine'] },
]

export const DEFAULT_CONFIG: ManufacturingConfig = {
  process: 'fdm',
  profile: 'Standard 0.4mm',
  presentationFace: 'front',
  preferredPrintFace: 'back',
  outputs: {
    preview: true, scad: true, stl: true, separatedStl: true, report: true,
  },
}

/** Update document's manufacturing section from config */
export function applyManufacturingConfig(doc: CardForgeDocument, config: ManufacturingConfig): void {
  doc.manufacturing.process = config.process
  doc.manufacturing.profile = config.profile
  Object.assign(doc.manufacturing, {
    presentationFace: config.presentationFace,
    preferredPrintFace: config.preferredPrintFace,
  })
}
