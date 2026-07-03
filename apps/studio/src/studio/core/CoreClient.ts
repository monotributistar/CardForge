// CoreClient — typed fetch wrapper for the CardForge Core API.
//
// The Core (Python, FastAPI) compiles v2 documents to per-material 3MF.
// Fidelity guarantee: the Studio 3D preview renders the exact 3MF bytes
// the Core returns — no geometry is reimplemented in TypeScript.

import type { DocumentV2 } from '../../types/cardforge'

export const CORE_BASE_URL = 'http://localhost:9000'

// ── Response types ───────────────────────────────────────────────────

export interface ConstraintIssue {
  severity: 'error' | 'warning'
  code: string
  message: string
  featureId?: string
  faceId?: string
  /** Present on manufacturing-rule issues: a human hint on how to fix it. */
  suggestion?: string
}

export interface ManufacturingSummary {
  score: number
  scoreLabel: string
  isManufacturable: boolean
  errorCount: number
  warningCount: number
  issues: ConstraintIssue[]
}

export interface CompileStats {
  compileMs: number
  featureCount: number
  threeMfBytes: number
}

export interface MaterialReport {
  id: string
  name: string
  color: string
  slot?: number
  role?: string
  present: boolean
  volumeMm3: number
}

export interface CompileResponse {
  ok: boolean
  model3mfBase64: string
  constraints: ConstraintIssue[]
  warnings: string[]
  skippedFeatures: string[]
  manufacturing: ManufacturingSummary
  stats: CompileStats
  materials: MaterialReport[]
}

export interface MigrateResponse {
  ok: boolean
  document: DocumentV2
  migrated: boolean
}

// ── Errors ───────────────────────────────────────────────────────────

export class CoreApiError extends Error {
  constructor(message: string, public status?: number, public details?: unknown) {
    super(message)
    this.name = 'CoreApiError'
  }
}

/** Thrown when the API cannot be reached at all (server not running). */
export class CoreUnreachableError extends Error {
  constructor() {
    super(`Core API unreachable at ${CORE_BASE_URL} — run \`pnpm core:api\``)
    this.name = 'CoreUnreachableError'
  }
}

// ── Internals ────────────────────────────────────────────────────────

async function postJson(path: string, body: unknown): Promise<Response> {
  try {
    return await fetch(`${CORE_BASE_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch {
    throw new CoreUnreachableError()
  }
}

async function readErrorMessage(res: Response): Promise<CoreApiError> {
  let message = `Core API error (HTTP ${res.status})`
  let details: unknown
  try {
    const data = await res.json()
    if (data && typeof data.error === 'string') message = data.error
    details = data?.details
  } catch { /* non-JSON error body */ }
  return new CoreApiError(message, res.status, details)
}

// ── Endpoints ────────────────────────────────────────────────────────

/** POST /api/compile — compile a document to per-material 3MF. */
export async function compileDocument(document: DocumentV2): Promise<CompileResponse> {
  const res = await postJson('/api/compile', { document })
  if (!res.ok) throw await readErrorMessage(res)
  return res.json() as Promise<CompileResponse>
}

/** POST /api/migrate — normalize a v1 (or unknown) document to v2. */
export async function migrateDocument(document: unknown): Promise<MigrateResponse> {
  const res = await postJson('/api/migrate', { document })
  if (!res.ok) throw await readErrorMessage(res)
  return res.json() as Promise<MigrateResponse>
}

/** POST /api/export — returns a binary ZIP, or throws on 409 (blocking errors). */
export async function exportDocument(
  document: DocumentV2,
  formats?: Array<'3mf' | 'stl'>,
  ignoreErrors?: boolean,
): Promise<Blob> {
  const res = await postJson('/api/export', { document, formats, ignoreErrors })
  if (!res.ok) throw await readErrorMessage(res)
  return res.blob()
}

/** GET /api/health — true when the Core API is up. */
export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${CORE_BASE_URL}/api/health`)
    if (!res.ok) return false
    const data = await res.json()
    return data?.ok === true
  } catch {
    return false
  }
}
