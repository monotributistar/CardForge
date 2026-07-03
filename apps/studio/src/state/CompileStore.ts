// CompileStore — live compile results from the Core API.
//
// Subscribes to the DocumentStore active document; debounces 400ms; posts
// /api/compile; keeps only the latest response (stale responses dropped
// via a request counter). The 3D viewer renders model3mfB64 verbatim —
// the exact bytes the Core produced.

import { create } from 'zustand'
import type { DocumentV2 } from '../types/cardforge'
import {
  compileDocument,
  type ConstraintIssue,
  type ManufacturingSummary,
  type CompileStats,
  type MaterialReport,
} from '../studio/core/CoreClient'
import { useDocumentStore, type DocumentStoreState } from './DocumentStore'

export type CompileStatus = 'idle' | 'compiling' | 'ok' | 'error'

export interface CompileStoreState {
  status: CompileStatus
  model3mfB64: string | null
  constraints: ConstraintIssue[]
  manufacturing: ManufacturingSummary | null
  stats: CompileStats | null
  materials: MaterialReport[]
  error: string | null
}

const EMPTY: CompileStoreState = {
  status: 'idle',
  model3mfB64: null,
  constraints: [],
  manufacturing: null,
  stats: null,
  materials: [],
  error: null,
}

export const useCompileStore = create<CompileStoreState>(() => ({ ...EMPTY }))

// ── Unified issue list ───────────────────────────────────────────────
// Merges kernel geometric `constraints` with `manufacturing.issues` into a
// single normalized list so panels/badges/status can read one stream.

export interface UnifiedIssue {
  severity: 'error' | 'warning'
  code: string
  message: string
  featureId?: string
  suggestion?: string
  source: 'geometry' | 'manufacturing'
}

/** Merge the two alert streams of a compile state into one normalized list. */
export function mergeIssues(state: Pick<CompileStoreState, 'constraints' | 'manufacturing'>): UnifiedIssue[] {
  const out: UnifiedIssue[] = []
  for (const c of state.constraints) {
    out.push({
      severity: c.severity, code: c.code, message: c.message,
      featureId: c.featureId, suggestion: c.suggestion, source: 'geometry',
    })
  }
  for (const m of state.manufacturing?.issues ?? []) {
    out.push({
      severity: m.severity, code: m.code, message: m.message,
      featureId: m.featureId, suggestion: m.suggestion, source: 'manufacturing',
    })
  }
  return out
}

/** Snapshot helper — the merged issue list for the current compile state. */
export function allIssues(): UnifiedIssue[] {
  return mergeIssues(useCompileStore.getState())
}

// ── Compile pipeline ─────────────────────────────────────────────────

const DEBOUNCE_MS = 400
let debounceTimer: ReturnType<typeof setTimeout> | null = null
let requestCounter = 0

function activeDoc(state: DocumentStoreState): DocumentV2 | null {
  const tab = state.tabs.find(t => t.id === state.activeTabId)
  return tab?.doc ?? null
}

async function runCompile(doc: DocumentV2): Promise<void> {
  const requestId = ++requestCounter
  useCompileStore.setState({ status: 'compiling', error: null })
  try {
    const res = await compileDocument(doc)
    if (requestId !== requestCounter) return // stale response — drop
    if (res.model3mfBase64) {
      useCompileStore.setState({
        status: 'ok',
        model3mfB64: res.model3mfBase64,
        constraints: res.constraints ?? [],
        manufacturing: res.manufacturing ?? null,
        stats: res.stats ?? null,
        materials: res.materials ?? [],
        error: null,
      })
    } else {
      const firstError = (res.constraints ?? []).find(c => c.severity === 'error')
      useCompileStore.setState({
        status: 'error',
        constraints: res.constraints ?? [],
        manufacturing: res.manufacturing ?? null,
        stats: res.stats ?? null,
        materials: res.materials ?? [],
        error: firstError?.message ?? 'Compile failed',
      })
    }
  } catch (e) {
    if (requestId !== requestCounter) return
    useCompileStore.setState({
      status: 'error',
      error: e instanceof Error ? e.message : String(e),
    })
  }
}

function schedule(doc: DocumentV2 | null, immediate = false): void {
  if (debounceTimer) {
    clearTimeout(debounceTimer)
    debounceTimer = null
  }
  if (!doc) {
    requestCounter++ // invalidate any in-flight compile
    useCompileStore.setState({ ...EMPTY })
    return
  }
  if (immediate) {
    void runCompile(doc)
  } else {
    debounceTimer = setTimeout(() => void runCompile(doc), DEBOUNCE_MS)
  }
}

/** Force a compile of the current active document right now (e.g. Retry). */
export function recompileActive(): void {
  schedule(activeDoc(useDocumentStore.getState()), true)
}

useDocumentStore.subscribe((state, prevState) => {
  const doc = activeDoc(state)
  const prevDoc = activeDoc(prevState)
  if (doc !== prevDoc) schedule(doc)
})
