// PublishService — orchestrates the publish pipeline
//
// Compile → Build → Publish → Manufacturing Package
//
// Compile = preview + analysis (in-browser, via CompileService)
// Build = generate STL files (via Core CLI, placeholder)
// Publish = organize everything into a consistent package

import type { CardForgeDocument, ManufacturingReport } from '../../types/cardforge'
import type { PublishManifest, PublishFileEntry } from './PublishManifest'
import { createManifest, standardFileEntries } from './PublishManifest'

export interface PublishResult {
  success: boolean
  manifest: PublishManifest
  documentId: string
  errors: string[]
  warnings: string[]
}

export interface PublishOptions {
  includeSingleStl: boolean
  includePartsStl: boolean
  includeScad: boolean
}

const DEFAULT_OPTIONS: PublishOptions = {
  includeSingleStl: true,
  includePartsStl: true,
  includeScad: true,
}

/** Run the full publish pipeline */
export function publishDocument(
  doc: CardForgeDocument,
  report: ManufacturingReport,
  options: PublishOptions = DEFAULT_OPTIONS,
): PublishResult {
  const errors: string[] = []
  const warnings: string[] = []

  if (!report.is_manufacturable) {
    errors.push(`Document is not manufacturable (score: ${report.score}/100)`)
  }
  if (report.warning_count > 0) {
    warnings.push(`${report.warning_count} manufacturing warning(s) found`)
  }

  // Build file list
  const files: PublishFileEntry[] = standardFileEntries(doc.document.id)
    .filter(f => {
      if (f.type === 'stl' && !options.includeSingleStl) return false
      if (f.type === 'stl_part' && !options.includePartsStl) return false
      if (f.type === 'scad' && !options.includeScad) return false
      return true
    })

  const materials = ['PLA']
  if (doc.objects[0]?.theme?.accentColor) materials.push('Accent PLA')

  const manifest = createManifest(
    doc.document.name,
    doc.document.version,
    doc.manufacturing.profile,
    doc.manufacturing.process,
    doc.manufacturing.nozzle,
    doc.manufacturing.layerHeight,
    doc.manufacturing.material,
    report.score,
    report.score_label,
    report.is_manufacturable,
    files,
    materials,
  )

  return {
    success: errors.length === 0,
    manifest,
    documentId: doc.document.id,
    errors,
    warnings,
  }
}

/** Simulate a publish for preview (no actual file writing) */
export function previewPublish(
  doc: CardForgeDocument,
  report: ManufacturingReport,
): PublishResult {
  return publishDocument(doc, report)
}
