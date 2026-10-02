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
      display: 'flex', alignItems: 'stretch', background: '#16191D',
      borderBottom: '1px solid #2A313A', overflowX: 'auto', flexShrink: 0, minHeight: 38,
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
              background: isActive ? '#1A1E24' : 'transparent',
              color: isActive ? '#E6E9ED' : '#AEB6C0',
              borderRight: '1px solid #1E232A',
              borderTop: isActive ? '2px solid #E8622C' : '2px solid transparent',
            }}
          >
            <span>{tab.doc.meta.name || tab.fileName || 'Untitled'}</span>
            {tab.dirty && <span style={{ color: '#E0A32E', fontSize: 10 }}>●</span>}
            <span
              title="Close"
              onClick={e => { e.stopPropagation(); handleClose(tab.id, tab.dirty, tab.doc.meta.name) }}
              style={{ color: '#5B6673', fontSize: 13, lineHeight: 1, padding: '0 2px', borderRadius: 3 }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#E04343' }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = '#5B6673' }}
            >×</span>
          </div>
        )
      })}
      <button
        onClick={() => newTab()}
        title="New document"
        style={{
          background: 'transparent', color: '#AEB6C0', border: 'none',
          padding: '0 12px', cursor: 'pointer', fontSize: 15,
        }}
      >+</button>
    </div>
  )
}
