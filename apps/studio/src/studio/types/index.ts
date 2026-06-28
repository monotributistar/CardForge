// Studio types — re-exported from shared types, plus Studio-specific types

export type { CardForgeDocument, DocumentObject, Face, Feature, ManufacturingReport, ManufacturingIssue } from '../../types/cardforge'

/** A unique identifier for features */
export type FeatureId = string

/** A face identifier */
export type FaceId = 'front' | 'back'

/** Workspace preferences */
export interface WorkspacePreferences {
  showGrid: boolean
  showBounds: boolean
  snapToGrid: boolean
  gridSize: number
}
