// CoreClient — unified API for Studio to consume Core results
//
// The Studio never calls CoreBridge directly.
// It calls CoreClient, which:
//   1. Tries the Core Bridge (CLI/HTTP/WS — depending on environment)
//   2. Falls back to CompileService if Bridge is unavailable
//
// When the Bridge is fully available, CompileService will be removed.

import type { CardForgeDocument } from '../../types/cardforge'
import type { CorePreviewResponse, CoreCompileResponse, CorePublishResponse } from './CoreProtocol'
import { CoreBridge } from './CoreBridge'

export interface CoreClientResult {
  /** SVG previews */
  frontSvg: string
  backSvg: string
  /** Manufacturing report */
  score: number
  scoreLabel: string
  isManufacturable: boolean
  warnings: Array<{ code: string; message: string; suggestion?: string }>
  errors: Array<{ code: string; message: string }>
  suggestions: string[]
  /** Source of the result */
  source: 'core' | 'fallback'
}

/**
 * Request a live preview from the Core.
 * Falls back to CompileService if Core is unavailable.
 */
export async function corePreview(document: CardForgeDocument): Promise<CoreClientResult> {
  try {
    // Try Core Bridge first (will throw in browser env)
    const response = await CoreBridge.preview(document.document.id)
    return {
      frontSvg: response.preview.frontSvg,
      backSvg: response.preview.backSvg,
      score: response.manufacturing.score,
      scoreLabel: response.manufacturing.scoreLabel,
      isManufacturable: response.manufacturing.isManufacturable,
      warnings: response.manufacturing.warnings,
      errors: response.manufacturing.errors,
      suggestions: response.manufacturing.suggestions,
      source: 'core',
    }
  } catch {
    // Fallback to CompileService
    const { compileLive } = await import('../services/CompileService')
    const result = compileLive(document)
    return {
      frontSvg: result.frontSvg,
      backSvg: result.backSvg,
      score: result.report.score,
      scoreLabel: result.report.score_label,
      isManufacturable: result.report.is_manufacturable,
      warnings: result.report.issues.filter(i => i.severity === 'warning').map(i => ({ code: i.code, message: i.message, suggestion: i.suggestion })),
      errors: result.report.issues.filter(i => i.severity === 'error').map(i => ({ code: i.code, message: i.message })),
      suggestions: result.report.suggestions,
      source: 'fallback',
    }
  }
}

/**
 * Request a publish manifest from the Core.
 */
export async function corePublish(document: CardForgeDocument): Promise<CorePublishResponse> {
  return CoreBridge.publish(document.document.id)
}
