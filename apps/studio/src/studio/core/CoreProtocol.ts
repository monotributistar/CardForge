// CoreProtocol — stable JSON contract between Studio and Core
//
// This is the single source of truth for Studio↔Core communication.
// Both sides implement against this contract.
// The TypeScript types mirror the Python CLI JSON output exactly.

export interface CorePreviewResponse {
  success: boolean
  error?: string
  preview: {
    frontSvg: string
    backSvg: string
  }
  manufacturing: {
    score: number
    scoreLabel: string
    isManufacturable: boolean
    errorCount: number
    warningCount: number
    infoCount: number
    warnings: CoreWarning[]
    errors: CoreError[]
    suggestions: string[]
  }
}

export interface CoreCompileResponse extends CorePreviewResponse {
  geometry: {
    status: string
  }
}

export interface CorePublishResponse {
  success: boolean
  error?: string
  manifest: CorePublishManifest
  manufacturing: CorePreviewResponse['manufacturing']
}

export interface CoreWarning {
  code: string
  message: string
  suggestion?: string
}

export interface CoreError {
  code: string
  message: string
}

export interface CorePublishManifest {
  document: string
  version: string
  timestamp: string
  profile: string
  process: string
  nozzle: number
  layerHeight: number
  material: string
  score: number
  scoreLabel: string
  manufacturable: boolean
  files: CoreFileEntry[]
  materials: string[]
  colorCount: number
}

export interface CoreFileEntry {
  path: string
  type: string
}
