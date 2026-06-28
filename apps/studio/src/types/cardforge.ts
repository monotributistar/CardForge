// CardForge Studio — TypeScript types for Core data formats

export interface CardForgeDocument {
  document: {
    id: string
    name: string
    version: string
    description?: string
  }
  manufacturing: {
    profile: string
    process: string
    nozzle: number
    layerHeight: number
    material: string
  }
  variables: Record<string, string>
  objects: DocumentObject[]
  exports: {
    preview: boolean
    manufacturingReport: boolean
    singleStl: boolean
    colorSeparatedStl: boolean
    threeMf: boolean
  }
}

export interface DocumentObject {
  id: string
  type: string
  width: number
  height: number
  thickness: number
  cornerRadius: number
  theme?: { baseColor?: string; textColor?: string; accentColor?: string; name?: string }
  faces: Record<string, Face>
}

export interface Face {
  features: Feature[]
}

export interface Feature {
  id: string
  type: string
  position?: { x: number; y: number; anchor?: string }
  size?: { width: number; height: number } | number
  font?: string
  fontSize?: number
  fontStyle?: string
  align?: string
  lines?: string[]
  material?: string
  relief?: { mode: string; height?: number; depth?: number }
  zIndex?: number
  visible?: boolean
  text?: string
  patternType?: string
  spacing?: number
  rotation?: number
  file?: string
  value?: string
}

export interface LegacyConfig {
  project: { name: string; type: string; version: string }
  object: { width: number; height: number; thickness: number; cornerRadius: number }
  owner: Record<string, string>
  faces: Record<string, Face>
}

export interface ManufacturingReport {
  profile: {
    process: string
    nozzle: number
    layer_height: number
    material: string
    printer_name: string
  }
  score: number
  score_label: string
  is_manufacturable: boolean
  error_count: number
  warning_count: number
  info_count: number
  fatal_count: number
  issues: ManufacturingIssue[]
  metrics: Record<string, string | number>
  suggestions: string[]
}

export interface ManufacturingIssue {
  code: string
  severity: string
  message: string
  node_id?: string
  suggestion?: string
  value?: number
  threshold?: number
}
