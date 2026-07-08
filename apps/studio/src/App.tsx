// App — thin shell: MenuBar / TabBar / EditorLayout + keyboard shortcuts.

import React, { useEffect } from 'react'
import { MenuBar } from './components/MenuBar'
import { TabBar } from './components/TabBar'
import { EditorLayout } from './components/EditorLayout'
import { useDocumentStore, getActiveTab, removeFeatures, restoreSession } from './state/DocumentStore'
import { saveActiveTab } from './state/fileio'

const App: React.FC = () => {
  // Restore the previous session from localStorage, else open a fresh doc
  useEffect(() => {
    const store = useDocumentStore.getState()
    if (store.tabs.length === 0 && !restoreSession()) store.newTab()
  }, [])

  // Keyboard shortcuts:
  //   Cmd/Ctrl+Z undo · Shift+Cmd/Ctrl+Z redo · Cmd/Ctrl+S save
  //   Arrows nudge selection 0.5mm (Shift: 2mm) · Delete/Backspace delete · Esc clear
  useEffect(() => {
    const NUDGE_DIRS: Record<string, [number, number]> = {
      ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1],
    }
    const onKeyDown = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null
      const inInput = !!t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)
      const mod = e.metaKey || e.ctrlKey
      const store = useDocumentStore.getState()

      if (mod) {
        if (e.key.toLowerCase() === 's') {
          e.preventDefault()
          void saveActiveTab()
          return
        }
        if (e.key.toLowerCase() === 'z') {
          // Let native undo work inside text inputs
          if (inInput) return
          e.preventDefault()
          if (e.shiftKey) store.redo()
          else store.undo()
        }
        return
      }

      if (inInput) return
      const tab = getActiveTab(store)
      if (!tab) return

      if (e.key === 'Escape') {
        store.select(null)
        return
      }

      const ids = tab.selectedFeatureIds
      if (ids.length === 0) return

      if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault()
        store.applyEdit(d => removeFeatures(d, ids))
        store.select(null)
        return
      }

      const dir = NUDGE_DIRS[e.key]
      if (!dir) return
      e.preventDefault()
      const step = e.shiftKey ? 2 : 0.5
      store.applyEdit(d => {
        for (const face of ['front', 'back'] as const) {
          for (const f of d.faces[face]?.features ?? []) {
            if (ids.includes(f.id)) {
              f.transform.x = Math.round((f.transform.x + dir[0] * step) * 10) / 10
              f.transform.y = Math.round((f.transform.y + dir[1] * step) * 10) / 10
            }
          }
        }
      })
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: '#0d1117', color: '#c9d1d9' }}>
      <MenuBar />
      <TabBar />
      <EditorLayout />
    </div>
  )
}

export default App
