// MenuBar — file operations, undo/redo, document name + dirty indicator.

import React from 'react'
import { useDocumentStore, getActiveTab } from '../state/DocumentStore'
import { openDocumentViaDialog, saveActiveTab, saveActiveTabAs, exportActiveTab } from '../state/fileio'

export const MenuBar: React.FC = () => {
  const tab = useDocumentStore(getActiveTab)
  const newTab = useDocumentStore(s => s.newTab)
  const undo = useDocumentStore(s => s.undo)
  const redo = useDocumentStore(s => s.redo)

  const hasDoc = tab != null
  const canUndo = (tab?.undo.length ?? 0) > 0
  const canRedo = (tab?.redo.length ?? 0) > 0

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 4, padding: '6px 10px',
      background: '#161b22', borderBottom: '1px solid #30363d', flexShrink: 0,
    }}>
      <span style={{ fontWeight: 700, fontSize: 13, color: '#58a6ff', marginRight: 10 }}>CardForge Studio</span>

      <MenuBtn onClick={() => newTab()}>New</MenuBtn>
      <MenuBtn onClick={() => void openDocumentViaDialog()}>Open</MenuBtn>
      <MenuBtn disabled={!hasDoc} onClick={() => void saveActiveTab()}>Save</MenuBtn>
      <MenuBtn disabled={!hasDoc} onClick={() => void saveActiveTabAs()}>Save As</MenuBtn>
      <MenuBtn disabled={!hasDoc} onClick={() => void exportActiveTab()} accent>Export</MenuBtn>

      <span style={{ width: 1, height: 16, background: '#30363d', margin: '0 6px' }} />

      <MenuBtn disabled={!canUndo} onClick={undo} title="Cmd/Ctrl+Z">Undo</MenuBtn>
      <MenuBtn disabled={!canRedo} onClick={redo} title="Shift+Cmd/Ctrl+Z">Redo</MenuBtn>

      <span style={{ flex: 1 }} />

      {tab && (
        <span style={{ fontSize: 12, color: '#8b949e', display: 'flex', alignItems: 'center', gap: 6 }}>
          {tab.doc.meta.name}
          {tab.fileName && <span style={{ color: '#484f58' }}>({tab.fileName})</span>}
          {tab.dirty && <span title="Unsaved changes" style={{ color: '#d29922', fontSize: 14, lineHeight: 1 }}>●</span>}
        </span>
      )}
    </div>
  )
}

const MenuBtn: React.FC<{
  onClick: () => void
  disabled?: boolean
  accent?: boolean
  title?: string
  children: React.ReactNode
}> = ({ onClick, disabled, accent, title, children }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    title={title}
    style={{
      background: accent ? '#1f6feb' : '#21262d',
      color: disabled ? '#484f58' : accent ? '#fff' : '#c9d1d9',
      border: '1px solid #30363d',
      padding: '3px 10px', borderRadius: 4,
      cursor: disabled ? 'default' : 'pointer',
      fontSize: 12,
      opacity: disabled && accent ? 0.5 : 1,
    }}
  >{children}</button>
)
