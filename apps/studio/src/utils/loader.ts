// CardForge Studio — File loading utilities

import type { CardForgeDocument, ManufacturingReport } from '../types/cardforge'

export function parseDocumentFile(content: string): CardForgeDocument {
  const data = JSON.parse(content)
  if (!data.document && !data.objects) {
    // Try legacy config format
    if (data.project && data.faces) {
      return convertLegacyToDocument(data)
    }
    throw new Error('Not a valid CardForge document or config file')
  }
  if (data.objects) {
    return data as CardForgeDocument
  }
  throw new Error('Document has no objects array')
}

function convertLegacyToDocument(config: any): CardForgeDocument {
  return {
    document: {
      id: config.project?.name?.toLowerCase().replace(/\s+/g, '-') ?? 'legacy',
      name: config.project?.name ?? 'Legacy Config',
      version: config.project?.version ?? '0.1.0',
    },
    manufacturing: {
      profile: 'fdm-standard',
      process: config.manufacturing?.process ?? 'fdm',
      nozzle: config.manufacturing?.nozzle ?? 0.4,
      layerHeight: config.manufacturing?.layerHeight ?? 0.2,
      material: config.manufacturing?.material ?? 'PLA',
    },
    variables: config.owner ?? {},
    objects: [{
      id: 'main-card',
      type: config.project?.type ?? 'business-card',
      width: config.object?.width ?? 85,
      height: config.object?.height ?? 54,
      thickness: config.object?.thickness ?? 1.8,
      cornerRadius: config.object?.cornerRadius ?? 4,
      theme: config.theme,
      faces: config.faces ?? {},
    }],
    exports: {
      preview: true,
      manufacturingReport: true,
      singleStl: config.exports?.singleStl ?? true,
      colorSeparatedStl: config.exports?.colorSeparatedStl ?? false,
      threeMf: false,
    },
  }
}

export function parseReportFile(content: string): ManufacturingReport {
  return JSON.parse(content) as ManufacturingReport
}

export function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = () => reject(new Error(`Failed to read ${file.name}`))
    reader.readAsText(file)
  })
}

export function detectFileType(name: string): 'document' | 'config' | 'svg' | 'report' | 'unknown' {
  const lower = name.toLowerCase()
  if (lower.endsWith('.cardforge.json') || lower.includes('resolved')) return 'document'
  if (lower.endsWith('.json') && (lower.includes('manufacturing') || lower.includes('report'))) return 'report'
  if (lower.endsWith('.json')) return 'config'
  if (lower.endsWith('.svg')) return 'svg'
  return 'unknown'
}
