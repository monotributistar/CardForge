// CoreClient — typed fetch wrapper for the CardForge Core API.
//
// The Core (Python, FastAPI) compiles v2 documents to per-material 3MF.
// Fidelity guarantee: the Studio 3D preview renders the exact 3MF bytes
// the Core returns — no geometry is reimplemented in TypeScript.

import type { DocumentV2 } from '../../types/cardforge'

// Core (compile engine) endpoint.
//
// The URL resolves in two layers so the Studio is usable without touching a
// build config: a runtime override the user can set in-app (persisted in
// localStorage) wins; otherwise the build-time default (VITE_CORE_URL, baked
// in for the hosted build) applies. The 2D editor, validation and quick fixes
// never need the engine — only compiling the 3D geometry and exporting do —
// so a missing engine is an *optional* feature being off, not a broken app.

const CORE_URL_KEY = 'cardforge.core.url'

/** Build-time default endpoint (hosted build bakes in VITE_CORE_URL). */
export const DEFAULT_CORE_URL: string =
  import.meta.env.VITE_CORE_URL ?? 'http://localhost:9000'

function normalizeUrl(raw: string | null | undefined): string {
  const v = (raw ?? '').trim().replace(/\/+$/, '')
  return v || DEFAULT_CORE_URL
}

function readStoredUrl(): string {
  try {
    return normalizeUrl(localStorage.getItem(CORE_URL_KEY))
  } catch {
    return DEFAULT_CORE_URL
  }
}

let _baseUrl = readStoredUrl()

/** The engine endpoint currently in effect (runtime override or default). */
export function getCoreBaseUrl(): string {
  return _baseUrl
}

/**
 * Set and persist the engine endpoint. An empty value resets to the default.
 * Returns the effective URL after normalization.
 */
export function setCoreBaseUrl(raw: string): string {
  _baseUrl = normalizeUrl(raw)
  try {
    if (_baseUrl === DEFAULT_CORE_URL) localStorage.removeItem(CORE_URL_KEY)
    else localStorage.setItem(CORE_URL_KEY, _baseUrl)
  } catch {
    /* storage unavailable — override stays in memory for the session */
  }
  // A different engine can advertise different fonts — drop the cache.
  _fontsCache = null
  _fontsPromise = null
  return _baseUrl
}

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

export interface PartReport {
  id: string
  /** Exact 3MF object name — matches the mesh names the viewer sees. */
  label: string
  /** Feature this part came from (null for the base body). */
  featureId: string | null
  material: string
  slot?: number | null
  /** [width, depth, height] in mm. */
  sizeMm: [number, number, number]
  /** [zMin, zMax] in mm, bed at 0. */
  zMm: [number, number]
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
  parts: PartReport[]
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

/** Thrown when the engine cannot be reached at all (server not running). */
export class CoreUnreachableError extends Error {
  constructor() {
    super(`No se pudo conectar con el motor en ${getCoreBaseUrl()}`)
    this.name = 'CoreUnreachableError'
  }
}

// ── Internals ────────────────────────────────────────────────────────

async function postJson(path: string, body: unknown): Promise<Response> {
  try {
    return await fetch(`${getCoreBaseUrl()}${path}`, {
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
    const res = await fetch(`${getCoreBaseUrl()}/api/health`)
    if (!res.ok) return false
    const data = await res.json()
    return data?.ok === true
  } catch {
    return false
  }
}

export interface FontInfo { family: string; variable: boolean; weights?: number[] }

let _fontsCache: FontInfo[] | null = null
let _fontsPromise: Promise<FontInfo[]> | null = null

/** GET /api/fonts — families the Core can render (cached for the session). */
export async function listFonts(): Promise<FontInfo[]> {
  if (_fontsCache) return _fontsCache
  if (!_fontsPromise) {
    _fontsPromise = (async () => {
      try {
        const res = await fetch(`${getCoreBaseUrl()}/api/fonts`)
        if (!res.ok) return []
        const data = await res.json()
        _fontsCache = (data?.fonts ?? []) as FontInfo[]
        return _fontsCache
      } catch {
        return []
      }
    })()
  }
  return _fontsPromise
}
