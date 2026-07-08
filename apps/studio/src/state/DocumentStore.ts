// DocumentStore — the heart of the multi-document IDE.
//
// One TabState per open document. Every edit goes through applyEdit(),
// which snapshots the document JSON for undo (cap 100) and marks dirty.

import { create } from 'zustand'
import type { DocumentV2, FaceId, Feature } from '../types/cardforge'
import { createNewDocument } from '../studio/document/defaults'
import { migrateDocument } from '../studio/core/CoreClient'

const UNDO_CAP = 100

export interface TabState {
  id: string
  doc: DocumentV2
  fileHandle: FileSystemFileHandle | null
  fileName: string | null
  dirty: boolean
  undo: string[]
  redo: string[]
  /** Multi-selection; the last entry is the primary. */
  selectedFeatureIds: string[]
  /** Primary selection (= last selected). Kept in sync with selectedFeatureIds. */
  selectedFeatureId: string | null
  /** True when the base object (not a feature) is the current selection. */
  objectSelected: boolean
  activeFace: FaceId
}

export interface DocumentStoreState {
  tabs: TabState[]
  activeTabId: string | null
  newTab: (doc?: DocumentV2) => string
  closeTab: (id: string) => void
  setActive: (id: string) => void
  /**
   * Mutate the active document. Pushes a JSON snapshot to the undo stack
   * (unless options.snapshot === false, used to coalesce drag moves),
   * clears redo, marks the tab dirty.
   */
  applyEdit: (mutator: (doc: DocumentV2) => void, options?: { snapshot?: boolean }) => void
  undo: () => void
  redo: () => void
  /** Replace the selection with a single feature (or clear it). */
  select: (featureId: string | null) => void
  /** Select the base object; clears any feature selection. */
  selectObject: () => void
  /** Toggle a feature's membership in the multi-selection. */
  toggleSelect: (featureId: string) => void
  setActiveFace: (face: FaceId) => void
  markSaved: (fileHandle?: FileSystemFileHandle | null, fileName?: string | null) => void
  /** Open parsed JSON data. Non-v2 documents are migrated via the Core API. */
  openFromData: (data: unknown, fileName?: string, fileHandle?: FileSystemFileHandle | null) => Promise<void>
}

let tabCounter = 0
const nextTabId = () => `tab-${++tabCounter}`

function makeTab(doc: DocumentV2, fileName: string | null = null, fileHandle: FileSystemFileHandle | null = null): TabState {
  return {
    id: nextTabId(),
    doc,
    fileHandle,
    fileName,
    dirty: false,
    undo: [],
    redo: [],
    selectedFeatureIds: [],
    selectedFeatureId: null,
    objectSelected: true,
    activeFace: 'front',
  }
}

export const useDocumentStore = create<DocumentStoreState>((set, get) => {
  const updateActiveTab = (fn: (tab: TabState) => TabState) => {
    set(state => {
      const tab = state.tabs.find(t => t.id === state.activeTabId)
      if (!tab) return state
      return { tabs: state.tabs.map(t => (t.id === tab.id ? fn(t) : t)) }
    })
  }

  return {
    tabs: [],
    activeTabId: null,

    newTab: (doc) => {
      const tab = makeTab(doc ?? createNewDocument())
      set(state => ({ tabs: [...state.tabs, tab], activeTabId: tab.id }))
      return tab.id
    },

    closeTab: (id) => {
      set(state => {
        const idx = state.tabs.findIndex(t => t.id === id)
        if (idx === -1) return state
        const tabs = state.tabs.filter(t => t.id !== id)
        let activeTabId = state.activeTabId
        if (activeTabId === id) {
          const neighbor = tabs[Math.min(idx, tabs.length - 1)]
          activeTabId = neighbor ? neighbor.id : null
        }
        return { tabs, activeTabId }
      })
    },

    setActive: (id) => {
      if (get().tabs.some(t => t.id === id)) set({ activeTabId: id })
    },

    applyEdit: (mutator, options) => {
      updateActiveTab(tab => {
        const next = structuredClone(tab.doc)
        mutator(next)
        const snapshot = options?.snapshot !== false
        const undo = snapshot ? [...tab.undo, JSON.stringify(tab.doc)].slice(-UNDO_CAP) : tab.undo
        const redo = snapshot ? [] : tab.redo
        return { ...tab, doc: next, undo, redo, dirty: true }
      })
    },

    undo: () => {
      updateActiveTab(tab => {
        if (tab.undo.length === 0) return tab
        const doc = JSON.parse(tab.undo[tab.undo.length - 1]) as DocumentV2
        return {
          ...tab,
          doc,
          undo: tab.undo.slice(0, -1),
          redo: [...tab.redo, JSON.stringify(tab.doc)],
          dirty: true,
        }
      })
    },

    redo: () => {
      updateActiveTab(tab => {
        if (tab.redo.length === 0) return tab
        const doc = JSON.parse(tab.redo[tab.redo.length - 1]) as DocumentV2
        return {
          ...tab,
          doc,
          redo: tab.redo.slice(0, -1),
          undo: [...tab.undo, JSON.stringify(tab.doc)].slice(-UNDO_CAP),
          dirty: true,
        }
      })
    },

    select: (featureId) => {
      updateActiveTab(tab => ({
        ...tab,
        selectedFeatureIds: featureId ? [featureId] : [],
        selectedFeatureId: featureId || null,
        objectSelected: false,
      }))
    },

    selectObject: () => {
      updateActiveTab(tab => ({
        ...tab,
        selectedFeatureIds: [],
        selectedFeatureId: null,
        objectSelected: true,
      }))
    },

    toggleSelect: (featureId) => {
      updateActiveTab(tab => {
        const ids = tab.selectedFeatureIds.includes(featureId)
          ? tab.selectedFeatureIds.filter(id => id !== featureId)
          : [...tab.selectedFeatureIds, featureId]
        return { ...tab, selectedFeatureIds: ids, selectedFeatureId: ids[ids.length - 1] ?? null, objectSelected: false }
      })
    },

    setActiveFace: (face) => {
      updateActiveTab(tab => ({ ...tab, activeFace: face }))
    },

    markSaved: (fileHandle, fileName) => {
      updateActiveTab(tab => ({
        ...tab,
        dirty: false,
        fileHandle: fileHandle !== undefined ? fileHandle : tab.fileHandle,
        fileName: fileName !== undefined ? fileName : tab.fileName,
      }))
    },

    openFromData: async (data, fileName, fileHandle) => {
      let doc: DocumentV2
      if (data && typeof data === 'object' && (data as { cardforge?: unknown }).cardforge === '2.0') {
        doc = data as DocumentV2
      } else {
        const res = await migrateDocument(data)
        doc = res.document
      }
      const tab = makeTab(doc, fileName ?? null, fileHandle ?? null)
      set(state => ({ tabs: [...state.tabs, tab], activeTabId: tab.id }))
    },
  }
})

// ── Selectors / helpers ──────────────────────────────────────────────

export function getActiveTab(state: DocumentStoreState): TabState | null {
  return state.tabs.find(t => t.id === state.activeTabId) ?? null
}

/** Remove features by id from both faces. Use inside applyEdit. */
export function removeFeatures(doc: DocumentV2, ids: string[]): void {
  for (const face of ['front', 'back'] as const) {
    const f = doc.faces[face]
    if (f) f.features = f.features.filter(x => !ids.includes(x.id))
  }
}

/** Find a feature by id in either face. Returns the feature and its face. */
export function findFeature(doc: DocumentV2, featureId: string): { feature: Feature; face: FaceId } | null {
  for (const face of ['front', 'back'] as const) {
    const feature = doc.faces[face]?.features.find(f => f.id === featureId)
    if (feature) return { feature, face }
  }
  return null
}

// ── localStorage persistence ─────────────────────────────────────────
// Every open document autosaves (debounced) under cardforge.doc.<id>, and
// the open-tab list under cardforge.session — a reload restores the session
// and the MenuBar "Recent" list offers every stored document.

const DOC_KEY_PREFIX = 'cardforge.doc.'
const SESSION_KEY = 'cardforge.session'

export interface StoredDocInfo { id: string; name: string; savedAt: string }

export function listStoredDocuments(): StoredDocInfo[] {
  const out: StoredDocInfo[] = []
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (!key?.startsWith(DOC_KEY_PREFIX)) continue
      const entry = JSON.parse(localStorage.getItem(key) ?? 'null')
      if (entry?.data) out.push({ id: key.slice(DOC_KEY_PREFIX.length), name: entry.name ?? '?', savedAt: entry.savedAt ?? '' })
    }
  } catch { /* storage unavailable */ }
  return out.sort((a, b) => b.savedAt.localeCompare(a.savedAt))
}

export function loadStoredDocument(id: string): DocumentV2 | null {
  try {
    const entry = JSON.parse(localStorage.getItem(DOC_KEY_PREFIX + id) ?? 'null')
    return entry?.data ?? null
  } catch { return null }
}

export function deleteStoredDocument(id: string): void {
  try { localStorage.removeItem(DOC_KEY_PREFIX + id) } catch { /* ignore */ }
}

let persistTimer: ReturnType<typeof setTimeout> | null = null

useDocumentStore.subscribe(state => {
  if (persistTimer) clearTimeout(persistTimer)
  persistTimer = setTimeout(() => {
    try {
      for (const tab of state.tabs) {
        localStorage.setItem(DOC_KEY_PREFIX + tab.doc.meta.id, JSON.stringify({
          name: tab.doc.meta.name,
          savedAt: new Date().toISOString(),
          data: tab.doc,
        }))
      }
      const active = state.tabs.find(t => t.id === state.activeTabId)
      localStorage.setItem(SESSION_KEY, JSON.stringify({
        open: state.tabs.map(t => t.doc.meta.id),
        active: active?.doc.meta.id ?? null,
      }))
    } catch { /* quota exceeded / storage unavailable — autosave is best-effort */ }
  }, 800)
})

/** Reopen the previous session's tabs from localStorage. Returns true if at
 * least one document was restored (App then skips the default blank tab). */
export function restoreSession(): boolean {
  try {
    const session = JSON.parse(localStorage.getItem(SESSION_KEY) ?? 'null')
    if (!session?.open?.length) return false
    const store = useDocumentStore.getState()
    let restoredActive: string | null = null
    let restored = false
    for (const id of session.open as string[]) {
      const doc = loadStoredDocument(id)
      if (!doc) continue
      const tabId = store.newTab(doc)
      restored = true
      if (id === session.active) restoredActive = tabId
    }
    if (restoredActive) store.setActive(restoredActive)
    return restored
  } catch { return false }
}
