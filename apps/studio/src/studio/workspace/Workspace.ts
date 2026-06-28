// Workspace — the top-level project container
//
// Responsibility: maintain the open project, its document,
// manufacturing profile, preferences, and assets.
// Prepared for multi-document in the future.

import type { CardForgeDocument, ManufacturingReport } from '../types'
import type { WorkspacePreferences } from '../types'

export interface WorkspaceState {
  /** Currently open document (null if none) */
  document: CardForgeDocument | null

  /** Manufacturing report for the current build */
  manufacturingReport: ManufacturingReport | null

  /** User preferences */
  preferences: WorkspacePreferences

  /** Errors from loading or building */
  errors: string[]

  /** Whether a build is in progress */
  isBuilding: boolean
}

export const DEFAULT_PREFERENCES: WorkspacePreferences = {
  showGrid: false,
  showBounds: false,
  snapToGrid: false,
  gridSize: 1.0,
}

export function createEmptyWorkspace(): WorkspaceState {
  return {
    document: null,
    manufacturingReport: null,
    preferences: { ...DEFAULT_PREFERENCES },
    errors: [],
    isBuilding: false,
  }
}

/** Actions that modify workspace state */
export interface WorkspaceActions {
  openDocument: (doc: CardForgeDocument) => void
  setReport: (report: ManufacturingReport) => void
  addError: (error: string) => void
  clearErrors: () => void
  updatePreferences: (patch: Partial<WorkspacePreferences>) => void
}

export class Workspace {
  state: WorkspaceState
  actions: WorkspaceActions

  constructor() {
    this.state = createEmptyWorkspace()
    this.actions = {
      openDocument: (doc) => { this.state = { ...this.state, document: doc, errors: [] } },
      setReport: (report) => { this.state = { ...this.state, manufacturingReport: report } },
      addError: (error) => { this.state = { ...this.state, errors: [...this.state.errors, error] } },
      clearErrors: () => { this.state = { ...this.state, errors: [] } },
      updatePreferences: (patch) => {
        this.state = { ...this.state, preferences: { ...this.state.preferences, ...patch } }
      },
    }
  }

  get document() { return this.state.document }
  get report() { return this.state.manufacturingReport }
  get object() { return this.state.document?.objects?.[0] ?? null }
}
