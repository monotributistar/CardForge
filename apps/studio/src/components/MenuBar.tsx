// MenuBar — file operations, undo/redo, document name + dirty indicator.

import React, { useState, useRef, useEffect } from 'react'
import {
  useDocumentStore, getActiveTab,
  listStoredDocuments, openStoredDocument, deleteStoredDocument, type StoredDocInfo,
} from '../state/DocumentStore'
import { openDocumentViaDialog, saveActiveTab, saveActiveTabAs, exportActiveTab } from '../state/fileio'
import { useUIStore } from '../state/UIStore'

export const MenuBar: React.FC = () => {
  const tab = useDocumentStore(getActiveTab)
  const undo = useDocumentStore(s => s.undo)
  const redo = useDocumentStore(s => s.redo)
  const openSplash = useUIStore(s => s.openSplash)
  const openWizard = useUIStore(s => s.openWizard)

  const hasDoc = tab != null
  const canUndo = (tab?.undo.length ?? 0) > 0
  const canRedo = (tab?.redo.length ?? 0) > 0

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 4, padding: '6px 10px',
      background: '#161b22', borderBottom: '1px solid #30363d', flexShrink: 0,
      overflowX: 'auto',
    }}>
      <button
        onClick={openSplash}
        title="Welcome screen — recents, wizard, support"
        style={{ fontWeight: 700, fontSize: 13, color: '#58a6ff', marginRight: 10, background: 'transparent', border: 'none', cursor: 'pointer', padding: '4px 2px', whiteSpace: 'nowrap' }}
      >CardForge Studio</button>

      <MenuBtn onClick={openWizard} title="New card — guided setup">New</MenuBtn>
      <MenuBtn onClick={() => void openDocumentViaDialog()}>Open</MenuBtn>
      <RecentMenu />
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

// Documents autosaved to localStorage — open or delete them.
const RecentMenu: React.FC = () => {
  const [open, setOpen] = useState(false)
  const [docs, setDocs] = useState<StoredDocInfo[]>([])
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    setDocs(listStoredDocuments())
    const onDocClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [open])

  const openStored = (id: string) => {
    setOpen(false)
    openStoredDocument(id)
  }

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <MenuBtn onClick={() => setOpen(o => !o)}>Recent ▾</MenuBtn>
      {open && (
        <div style={{
          position: 'absolute', top: 26, left: 0, zIndex: 50, minWidth: 240,
          background: '#161b22', border: '1px solid #30363d', borderRadius: 6,
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)', padding: 4,
        }}>
          {docs.length === 0 && (
            <div style={{ padding: '6px 8px', fontSize: 11, color: '#484f58' }}>No stored documents</div>
          )}
          {docs.map(d => (
            <div key={d.id}
              onClick={() => openStored(d.id)}
              style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 8px', cursor: 'pointer', borderRadius: 4, color: '#c9d1d9', fontSize: 12 }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = '#21262d' }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent' }}>
              <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.name}</span>
              <span style={{ fontSize: 10, color: '#484f58' }}>{d.savedAt.slice(0, 16).replace('T', ' ')}</span>
              <button title="Delete from browser storage"
                onClick={e => { e.stopPropagation(); deleteStoredDocument(d.id); setDocs(listStoredDocuments()) }}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: 11, padding: 0 }}>🗑</button>
            </div>
          ))}
        </div>
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
      padding: '6px 12px', borderRadius: 5,
      cursor: disabled ? 'default' : 'pointer',
      fontSize: 13,
      opacity: disabled && accent ? 0.5 : 1,
    }}
  >{children}</button>
)
