// App — thin shell: MenuBar / TabBar / EditorLayout + keyboard shortcuts.

import React, { useEffect } from 'react'
import { MenuBar } from './components/MenuBar'
import { TabBar } from './components/TabBar'
import { EditorLayout } from './components/EditorLayout'
import { useDocumentStore } from './state/DocumentStore'
import { saveActiveTab } from './state/fileio'

const App: React.FC = () => {
  // Open a fresh document on first launch
  useEffect(() => {
    const store = useDocumentStore.getState()
    if (store.tabs.length === 0) store.newTab()
  }, [])

  // Keyboard shortcuts: Cmd/Ctrl+Z undo, Shift+Cmd/Ctrl+Z redo, Cmd/Ctrl+S save
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey
      if (!mod) return
      if (e.key.toLowerCase() === 's') {
        e.preventDefault()
        void saveActiveTab()
        return
      }
      if (e.key.toLowerCase() === 'z') {
        // Let native undo work inside text inputs
        const t = e.target as HTMLElement | null
        if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
        e.preventDefault()
        if (e.shiftKey) useDocumentStore.getState().redo()
        else useDocumentStore.getState().undo()
      }
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
