// TabBar — one tab per open document, dirty dot, close, + for new doc.

import React from 'react'
import { useDocumentStore } from '../state/DocumentStore'

export const TabBar: React.FC = () => {
  const tabs = useDocumentStore(s => s.tabs)
  const activeTabId = useDocumentStore(s => s.activeTabId)
  const setActive = useDocumentStore(s => s.setActive)
  const closeTab = useDocumentStore(s => s.closeTab)
  const newTab = useDocumentStore(s => s.newTab)

  const handleClose = (id: string, dirty: boolean, name: string) => {
    if (dirty && !window.confirm(`"${name}" has unsaved changes. Close anyway?`)) return
    closeTab(id)
  }

  return (
    <div style={{
      display: 'flex', alignItems: 'stretch', background: '#0d1117',
      borderBottom: '1px solid #30363d', overflowX: 'auto', flexShrink: 0, minHeight: 38,
    }}>
      {tabs.map(tab => {
        const isActive = tab.id === activeTabId
        return (
          <div
            key={tab.id}
            onClick={() => setActive(tab.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '0 12px',
              cursor: 'pointer', fontSize: 13, whiteSpace: 'nowrap',
              background: isActive ? '#161b22' : 'transparent',
              color: isActive ? '#c9d1d9' : '#8b949e',
              borderRight: '1px solid #21262d',
              borderTop: isActive ? '2px solid #58a6ff' : '2px solid transparent',
            }}
          >
            <span>{tab.doc.meta.name || tab.fileName || 'Untitled'}</span>
            {tab.dirty && <span style={{ color: '#d29922', fontSize: 10 }}>●</span>}
            <span
              title="Close"
              onClick={e => { e.stopPropagation(); handleClose(tab.id, tab.dirty, tab.doc.meta.name) }}
              style={{ color: '#484f58', fontSize: 13, lineHeight: 1, padding: '0 2px', borderRadius: 3 }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#f85149' }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = '#484f58' }}
            >×</span>
          </div>
        )
      })}
      <button
        onClick={() => newTab()}
        title="New document"
        style={{
          background: 'transparent', color: '#8b949e', border: 'none',
          padding: '0 12px', cursor: 'pointer', fontSize: 15,
        }}
      >+</button>
    </div>
  )
}
