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
      background: '#1A1E24', borderBottom: '1px solid #2A313A', flexShrink: 0,
      overflowX: 'auto',
    }}>
      <button
        onClick={openSplash}
        title="Welcome screen — recents, wizard, support"
        style={{ display: 'flex', alignItems: 'center', gap: 7, fontFamily: 'var(--cf-font-display)', fontWeight: 700, fontSize: 14, letterSpacing: '-0.01em', color: '#F2F4F7', marginRight: 10, background: 'transparent', border: 'none', cursor: 'pointer', padding: '2px 2px', whiteSpace: 'nowrap' }}
      >
        <svg width="20" height="20" viewBox="0 0 112 112" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect x="30" y="22" width="60" height="40" rx="8" fill="#2A313A" />
          <rect x="21" y="34" width="60" height="40" rx="8" fill="#3A434F" />
          <rect x="12" y="46" width="60" height="40" rx="8" fill="#1B1F25" stroke="#E8622C" strokeWidth="4" />
          <circle cx="88" cy="30" r="9" fill="#E8622C" />
        </svg>
        <span>Card<span style={{ color: '#E8622C' }}>Forge</span></span>
      </button>

      <MenuBtn onClick={openWizard} title="New card — guided setup">New</MenuBtn>
      <MenuBtn onClick={() => void openDocumentViaDialog()}>Open</MenuBtn>
      <RecentMenu />
      <MenuBtn disabled={!hasDoc} onClick={() => void saveActiveTab()}>Save</MenuBtn>
      <MenuBtn disabled={!hasDoc} onClick={() => void saveActiveTabAs()}>Save As</MenuBtn>
      <MenuBtn disabled={!hasDoc} onClick={() => void exportActiveTab()} accent>Export</MenuBtn>

      <span style={{ width: 1, height: 16, background: '#2A313A', margin: '0 6px' }} />

      <MenuBtn disabled={!canUndo} onClick={undo} title="Cmd/Ctrl+Z">Undo</MenuBtn>
      <MenuBtn disabled={!canRedo} onClick={redo} title="Shift+Cmd/Ctrl+Z">Redo</MenuBtn>

      <span style={{ flex: 1 }} />

      {tab && (
        <span style={{ fontSize: 12, color: '#AEB6C0', display: 'flex', alignItems: 'center', gap: 6 }}>
          {tab.doc.meta.name}
          {tab.fileName && <span style={{ color: '#5B6673' }}>({tab.fileName})</span>}
          {tab.dirty && <span title="Unsaved changes" style={{ color: '#E0A32E', fontSize: 14, lineHeight: 1 }}>●</span>}
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
          background: '#1A1E24', border: '1px solid #2A313A', borderRadius: 6,
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)', padding: 4,
        }}>
          {docs.length === 0 && (
            <div style={{ padding: '6px 8px', fontSize: 11, color: '#5B6673' }}>No stored documents</div>
          )}
          {docs.map(d => (
            <div key={d.id}
              onClick={() => openStored(d.id)}
              style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 8px', cursor: 'pointer', borderRadius: 4, color: '#E6E9ED', fontSize: 12 }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = '#1E232A' }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent' }}>
              <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.name}</span>
              <span style={{ fontSize: 10, color: '#5B6673' }}>{d.savedAt.slice(0, 16).replace('T', ' ')}</span>
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
      background: accent ? '#C24A1C' : '#1E232A',
      color: disabled ? '#5B6673' : accent ? '#fff' : '#E6E9ED',
      border: '1px solid #2A313A',
      padding: '6px 12px', borderRadius: 5,
      cursor: disabled ? 'default' : 'pointer',
      fontSize: 13,
      opacity: disabled && accent ? 0.5 : 1,
    }}
  >{children}</button>
)
