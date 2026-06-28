// CompileService — live SVG preview + manufacturing report in TypeScript
//
// Takes a CardForgeDocument and generates:
//   1. SVG preview (front/back)
//   2. Manufacturing report
//
// This is a TypeScript reimplementation of the Core pipeline for live Studio use.
// It does NOT replace the Core compiler — just enables live preview.

import type { CardForgeDocument, ManufacturingReport, Feature } from '../../types/cardforge'
import { renderQRSVG } from './QRGenerator'

// ── SVG Generation ──────────────────────────────────────────────────────

function resolveText(template: string, vars: Record<string, string>): string {
  return template.replace(/\{\{(\w+)\}\}/g, (_, key) => vars[key] ?? `{{${key}}}`)
}

const PX_PER_MM = 4

function svgHeader(w: number, h: number): string {
  const pw = w * PX_PER_MM
  const ph = h * PX_PER_MM
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${pw}" height="${ph}" viewBox="0 0 ${pw} ${ph}">`
}

function svgFooter(): string { return '</svg>' }

function compileFaceSVG(doc: CardForgeDocument, faceId: string): string {
  const obj = doc.objects[0]
  if (!obj) return ''
  const face = obj.faces[faceId]
  if (!face) return ''

  const w = obj.width * PX_PER_MM
  const h = obj.height * PX_PER_MM
  const r = (obj.cornerRadius ?? 4) * PX_PER_MM
  const baseColor = obj.theme?.baseColor ?? '#1a1a1a'
  const textColor = obj.theme?.textColor ?? '#ffffff'
  const accentColor = obj.theme?.accentColor ?? '#ffd700'
  const vars = doc.variables ?? {}

  const parts: string[] = []
  parts.push(svgHeader(w, h))
  parts.push(`<rect x="0" y="0" width="${w}" height="${h}" rx="${r}" fill="${baseColor}"/>`)

  for (const feat of face.features) {
    const x = (feat.position?.x ?? 0) * PX_PER_MM
    const y = (feat.position?.y ?? 0) * PX_PER_MM
    const color = feat.material === 'accent' ? accentColor : textColor

    if (feat.type === 'text-block' && feat.lines) {
      const fs = (feat.fontSize ?? 3.0) * PX_PER_MM
      const lh = 1.4
      for (let i = 0; i < feat.lines.length; i++) {
        const text = resolveText(feat.lines[i], vars)
        const ly = y + (i + 1) * fs * lh
        const anchor = feat.align === 'center' ? 'middle' : feat.align === 'right' ? 'end' : 'start'
        const ax = feat.align === 'center' ? x + (((feat as any).size?.width ?? obj.width) * PX_PER_MM) / 2 : x
        parts.push(`<text x="${ax}" y="${ly}" font-family="${feat.font ?? 'sans-serif'}" font-size="${fs}" font-weight="${feat.fontStyle ?? 'normal'}" fill="${color}" text-anchor="${anchor}">${text}</text>`)
      }
    } else if (feat.type === 'qr') {
      const qrValue = resolveText(feat.value ?? '', vars)
      const qrSizeMM = typeof feat.size === 'number' ? feat.size : (feat.size as any)?.width ?? 24
      const qrSvg = renderQRSVG(qrValue || 'cardforge', qrSizeMM, 2, PX_PER_MM)
      parts.push(`<g transform="translate(${x},${y})">${qrSvg}</g>`)
    } else if (feat.type === 'pattern') {
      parts.push(`<rect x="0" y="0" width="${w}" height="${h}" fill="none" stroke="${textColor}" stroke-width="${0.5 * PX_PER_MM}" opacity="0.15"/>`)
      parts.push(`<text x="${w/2}" y="${h/2}" font-size="${24 * PX_PER_MM}" fill="${textColor}" opacity="0.1" text-anchor="middle" transform="rotate(-25,${w/2},${h/2})">${feat.text ?? ''}</text>`)
    }
  }
  parts.push(svgFooter())
  return parts.join('\n')
}

// ── Manufacturing Analysis ──────────────────────────────────────────────

interface LiveIssue {
  code: string; severity: string; message: string; suggestion?: string
}

function analyzeDocument(doc: CardForgeDocument): { score: number; label: string; manufacturable: boolean; issues: LiveIssue[]; suggestions: string[] } {
  const issues: LiveIssue[] = []
  const profile = { minTextSize: 3.0, minQrSize: 22, minEmboss: 0.3, minDeboss: 0.2 }
  const vars = doc.variables ?? {}

  for (const obj of doc.objects) {
    for (const [_fid, face] of Object.entries(obj.faces)) {
      for (const feat of face.features) {
        if (feat.type === 'text-block' && feat.fontSize && feat.fontSize < profile.minTextSize) {
          issues.push({ code: 'text-too-small', severity: 'warning', message: `Text size ${feat.fontSize}mm below minimum ${profile.minTextSize}mm`, suggestion: `Increase font to at least ${profile.minTextSize}mm` })
        }
        if (feat.type === 'qr') {
          const qrSize = typeof feat.size === 'number' ? feat.size : (feat.size as any)?.width ?? 24
          if (qrSize < profile.minQrSize) {
            issues.push({ code: 'qr-too-small', severity: 'error', message: `QR size ${qrSize}mm below minimum ${profile.minQrSize}mm`, suggestion: `Increase QR to at least ${profile.minQrSize}mm` })
          }
        }
        if (feat.relief?.mode === 'emboss' && feat.relief.height != null && feat.relief.height < profile.minEmboss) {
          issues.push({ code: 'min-emboss', severity: 'warning', message: `Emboss height ${feat.relief.height}mm below minimum ${profile.minEmboss}mm`, suggestion: `Increase emboss to at least ${profile.minEmboss}mm` })
        }
      }
    }
  }

  const errors = issues.filter(i => i.severity === 'error').length
  const warnings = issues.filter(i => i.severity === 'warning').length
  const score = Math.max(0, 100 - errors * 15 - warnings * 5)
  const label = score >= 95 ? 'Excellent — ready to print' : score >= 80 ? 'Good — printable with minor warnings' : score >= 60 ? 'Fair — review warnings' : 'Poor — significant issues'

  return {
    score, label,
    manufacturable: errors === 0,
    issues,
    suggestions: issues.filter(i => i.suggestion).map(i => i.suggestion!),
  }
}

// ── Compile Service ─────────────────────────────────────────────────────

export interface CompileResult {
  frontSvg: string
  backSvg: string
  report: ManufacturingReport
}

export function compileLive(doc: CardForgeDocument): CompileResult {
  const frontSvg = compileFaceSVG(doc, 'front')
  const backSvg = compileFaceSVG(doc, 'back')

  const analysis = analyzeDocument(doc)

  const report: ManufacturingReport = {
    profile: {
      process: doc.manufacturing.process,
      nozzle: doc.manufacturing.nozzle,
      layer_height: doc.manufacturing.layerHeight,
      material: doc.manufacturing.material,
      printer_name: 'Generic FDM 0.4mm',
    },
    score: analysis.score,
    score_label: analysis.label,
    is_manufacturable: analysis.manufacturable,
    error_count: analysis.issues.filter(i => i.severity === 'error').length,
    warning_count: analysis.issues.filter(i => i.severity === 'warning').length,
    info_count: 0,
    fatal_count: 0,
    issues: analysis.issues.map(i => ({ ...i, node_id: undefined, value: undefined, threshold: undefined })),
    metrics: {},
    suggestions: analysis.suggestions,
  }

  return { frontSvg, backSvg, report }
}
