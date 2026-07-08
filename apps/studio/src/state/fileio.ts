// File I/O — File System Access API with graceful fallback.
//
// Chromium: window.showOpenFilePicker / showSaveFilePicker keep a
// FileSystemFileHandle so plain Save writes in place.
// Fallback (Firefox/Safari): <input type=file> for Open, blob download for Save.

import type { DocumentV2 } from '../types/cardforge'
import { useDocumentStore, getActiveTab } from './DocumentStore'
import { exportDocument } from '../studio/core/CoreClient'

// ── File System Access API ambient types (not yet in lib.dom) ────────

interface FilePickerAcceptType {
  description?: string
  accept: Record<string, string[]>
}
interface OpenFilePickerOptions {
  types?: FilePickerAcceptType[]
  multiple?: boolean
  excludeAcceptAllOption?: boolean
}
interface SaveFilePickerOptions {
  types?: FilePickerAcceptType[]
  suggestedName?: string
  excludeAcceptAllOption?: boolean
}

declare global {
  interface Window {
    showOpenFilePicker?: (options?: OpenFilePickerOptions) => Promise<FileSystemFileHandle[]>
    showSaveFilePicker?: (options?: SaveFilePickerOptions) => Promise<FileSystemFileHandle>
  }
}

const CARDFORGE_TYPES: FilePickerAcceptType[] = [
  { description: 'CardForge document', accept: { 'application/json': ['.json'] } },
]

function isAbort(e: unknown): boolean {
  return e instanceof DOMException && e.name === 'AbortError'
}

// ── Primitives ───────────────────────────────────────────────────────

export function downloadBlob(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 5000)
}

async function writeToHandle(handle: FileSystemFileHandle, contents: string): Promise<void> {
  const writable = await handle.createWritable()
  await writable.write(contents)
  await writable.close()
}

function pickFileFallback(): Promise<File | null> {
  return new Promise(resolve => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json,application/json'
    input.onchange = () => resolve(input.files?.[0] ?? null)
    // If the dialog is cancelled we simply never resolve with a file;
    // resolve(null) on window focus back is unreliable, so use 'cancel' when available.
    input.addEventListener('cancel', () => resolve(null))
    input.click()
  })
}

function serializeDocument(doc: DocumentV2): string {
  const stamped: DocumentV2 = { ...doc, meta: { ...doc.meta, modified: new Date().toISOString() } }
  return JSON.stringify(stamped, null, 2)
}

function suggestedFileName(doc: DocumentV2, current: string | null): string {
  if (current) return current
  const slug = (doc.meta.name || 'card').trim().replace(/[^\w-]+/g, '-').toLowerCase() || 'card'
  return `${slug}.cardforge.json`
}

// ── High-level actions (used by MenuBar and keyboard shortcuts) ──────

/** Open a document via file dialog. Migrates non-v2 files through the Core. */
export async function openDocumentViaDialog(): Promise<void> {
  try {
    let text: string
    let fileName: string
    let fileHandle: FileSystemFileHandle | null = null

    if (window.showOpenFilePicker) {
      const [handle] = await window.showOpenFilePicker({ types: CARDFORGE_TYPES })
      const file = await handle.getFile()
      text = await file.text()
      fileName = file.name
      fileHandle = handle
    } else {
      const file = await pickFileFallback()
      if (!file) return
      text = await file.text()
      fileName = file.name
    }

    let data: unknown
    try {
      data = JSON.parse(text)
    } catch {
      window.alert(`"${fileName}" is not valid JSON.`)
      return
    }
    await useDocumentStore.getState().openFromData(data, fileName, fileHandle)
  } catch (e) {
    if (isAbort(e)) return
    window.alert(`Open failed: ${e instanceof Error ? e.message : String(e)}`)
  }
}

/** Save the active tab: write in place if we have a handle, else Save As. */
export async function saveActiveTab(): Promise<void> {
  const state = useDocumentStore.getState()
  const tab = getActiveTab(state)
  if (!tab) return
  if (tab.fileHandle) {
    try {
      await writeToHandle(tab.fileHandle, serializeDocument(tab.doc))
      state.markSaved()
    } catch (e) {
      if (isAbort(e)) return
      window.alert(`Save failed: ${e instanceof Error ? e.message : String(e)}`)
    }
  } else {
    await saveActiveTabAs()
  }
}

/** Save As: picker with handle when supported, blob download otherwise. */
export async function saveActiveTabAs(): Promise<void> {
  const state = useDocumentStore.getState()
  const tab = getActiveTab(state)
  if (!tab) return
  const json = serializeDocument(tab.doc)
  const name = suggestedFileName(tab.doc, tab.fileName)

  if (window.showSaveFilePicker) {
    try {
      const handle = await window.showSaveFilePicker({ types: CARDFORGE_TYPES, suggestedName: name })
      await writeToHandle(handle, json)
      state.markSaved(handle, handle.name)
    } catch (e) {
      if (isAbort(e)) return
      window.alert(`Save failed: ${e instanceof Error ? e.message : String(e)}`)
    }
  } else {
    downloadBlob(new Blob([json], { type: 'application/json' }), name)
    state.markSaved(null, name)
  }
}

/** Export the active tab as a single .3mf named "<card name>_<stamp>.3mf". */
export async function exportActiveTab(): Promise<void> {
  const state = useDocumentStore.getState()
  const tab = getActiveTab(state)
  if (!tab) return
  try {
    const blob = await exportDocument(tab.doc, ['3mf'])
    const name = (tab.doc.meta?.name ?? '').replace(/[\\/:*?"<>|]/g, '').trim() || 'card'
    downloadBlob(blob, `${name}_${exportTimestamp()}.3mf`)
  } catch (e) {
    window.alert(`Export failed: ${e instanceof Error ? e.message : String(e)}`)
  }
}

/** Local-time compact stamp for export filenames: YYYYMMDD-HHMMSS. */
function exportTimestamp(d = new Date()): string {
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}` +
    `-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`
}
