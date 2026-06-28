// Publish Manifiesto — metadata for a Manufacturing Package

export interface PublishManifest {
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
  files: PublishFileEntry[]
  materials: string[]
  colorCount: number
}

export interface PublishFileEntry {
  path: string
  type: string  // 'document' | 'preview' | 'report' | 'scad' | 'stl' | 'stl_part' | 'print_readme'
  size?: number
  description?: string
}

/** Generate a manifest from document + compile result */
export function createManifest(
  documentName: string,
  documentVersion: string,
  profile: string,
  process: string,
  nozzle: number,
  layerHeight: number,
  material: string,
  score: number,
  scoreLabel: string,
  manufacturable: boolean,
  files: PublishFileEntry[],
  materials: string[],
): PublishManifest {
  return {
    document: documentName,
    version: documentVersion,
    timestamp: new Date().toISOString(),
    profile,
    process,
    nozzle,
    layerHeight,
    material,
    score,
    scoreLabel,
    manufacturable,
    files,
    materials,
    colorCount: materials.length,
  }
}

/** Generate a standard set of file entries for a published package */
export function standardFileEntries(docId: string): PublishFileEntry[] {
  return [
    { path: 'document/resolved.cardforge.json', type: 'document', description: 'Resolved document' },
    { path: 'preview/front.svg', type: 'preview', description: 'Front face preview' },
    { path: 'preview/back.svg', type: 'preview', description: 'Back face preview' },
    { path: 'reports/manufacturing_report.json', type: 'report', description: 'Manufacturing report (JSON)' },
    { path: 'reports/manufacturing_report.md', type: 'report', description: 'Manufacturing report (Markdown)' },
    { path: 'scad/generated.scad', type: 'scad', description: 'OpenSCAD geometry' },
    { path: 'stl/card_single.stl', type: 'stl', description: 'Single STL file' },
    { path: 'stl/parts/01_base_pla.stl', type: 'stl_part', description: 'Base material STL' },
    { path: 'stl/parts/02_text_pla.stl', type: 'stl_part', description: 'Text material STL' },
    { path: 'stl/parts/03_accent_pla.stl', type: 'stl_part', description: 'Accent material STL' },
    { path: 'print/README_PRINT.md', type: 'print_readme', description: 'Print instructions' },
    { path: 'manifest.json', type: 'document', description: 'Package manifest' },
  ]
}
