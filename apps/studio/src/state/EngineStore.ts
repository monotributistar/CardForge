// EngineStore — the connection to the compile engine (the Core API).
//
// The engine is OPTIONAL. The 2D editor, validation and client-side quick
// fixes all run in the browser with no engine at all; only compiling the 3D
// geometry and exporting need it. So a missing engine is a calm "feature off"
// state, never a red error — this store holds that connection state and lets
// the user point the Studio at any engine (or none) at runtime.

import { create } from 'zustand'
import {
  getCoreBaseUrl,
  setCoreBaseUrl,
  DEFAULT_CORE_URL,
  checkHealth,
} from '../studio/core/CoreClient'
import { recompileActive } from './CompileStore'

export type EngineStatus = 'unknown' | 'checking' | 'online' | 'offline'

interface EngineState {
  /** Endpoint currently in effect. */
  url: string
  /** Build-time default (shown as a hint / reset target). */
  defaultUrl: string
  status: EngineStatus
  /** Epoch ms of the last health probe, or null. */
  checkedAt: number | null
}

export const useEngineStore = create<EngineState>(() => ({
  url: getCoreBaseUrl(),
  defaultUrl: DEFAULT_CORE_URL,
  status: 'unknown',
  checkedAt: null,
}))

// Only the latest probe wins (URL can change mid-flight).
let probeSeq = 0

/** Probe the current engine for health; updates the store. Returns reachable?. */
export async function refreshEngine(): Promise<boolean> {
  const seq = ++probeSeq
  useEngineStore.setState({ status: 'checking' })
  const ok = await checkHealth()
  if (seq !== probeSeq) return ok // superseded by a newer probe
  useEngineStore.setState({ status: ok ? 'online' : 'offline', checkedAt: Date.now() })
  return ok
}

/**
 * Point the Studio at a different engine (empty resets to the default),
 * persist it, re-probe, and recompile if it came up.
 */
export function setEngineUrl(raw: string): void {
  const url = setCoreBaseUrl(raw)
  useEngineStore.setState({ url, status: 'unknown', checkedAt: null })
  void refreshEngine().then(ok => { if (ok) recompileActive() })
}

/** The compile pipeline calls this when a request finds the engine unreachable. */
export function markEngineOffline(): void {
  if (useEngineStore.getState().status !== 'offline') {
    useEngineStore.setState({ status: 'offline', checkedAt: Date.now() })
  }
}

/** The compile pipeline calls this when a request succeeds. */
export function markEngineOnline(): void {
  if (useEngineStore.getState().status !== 'online') {
    useEngineStore.setState({ status: 'online', checkedAt: Date.now() })
  }
}

// Probe once at startup so the UI shows the real state without a user action.
void refreshEngine()
