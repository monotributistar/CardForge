// IssuesPanel — collapsible list of every compile issue (geometry + manufacturing),
// merged via CompileStore.mergeIssues. Clicking a row with a featureId selects
// that feature (and switches to its face). Left panel, below MaterialPalette.

import React, { useState } from 'react'
import { useCompileStore, mergeIssues, type UnifiedIssue } from '../state/CompileStore'
import { useDocumentStore, getActiveTab, findFeature } from '../state/DocumentStore'

export const IssuesPanel: React.FC = () => {
  const constraints = useCompileStore(s => s.constraints)
  const manufacturing = useCompileStore(s => s.manufacturing)
  const [collapsed, setCollapsed] = useState(false)

  const select = useDocumentStore(s => s.select)
  const setActiveFace = useDocumentStore(s => s.setActiveFace)
  const tab = useDocumentStore(getActiveTab)

  const issues = mergeIssues({ constraints, manufacturing })

  const errors = issues.filter(i => i.severity === 'error')
  const warnings = issues.filter(i => i.severity === 'warning')
  // Errors first, then warnings.
  const ordered = [...errors, ...warnings]

  const onRowClick = (issue: UnifiedIssue) => {
    if (!issue.featureId || !tab) return
    const found = findFeature(tab.doc, issue.featureId)
    if (found) setActiveFace(found.face)
    select(issue.featureId)
  }

  return (
    <div style={{ borderTop: '1px solid #30363d', flexShrink: 0, maxHeight: 220, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div
        onClick={() => setCollapsed(c => !c)}
        style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px 4px',
          cursor: 'pointer', userSelect: 'none', flexShrink: 0,
        }}
      >
        <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.6, color: '#8b949e' }}>
          {collapsed ? '▸' : '▾'} Issues
        </span>
        <span style={{ flex: 1 }} />
        {errors.length > 0 && (
          <span style={{ fontSize: 10, color: '#f85149' }}>{errors.length} error{errors.length !== 1 ? 's' : ''}</span>
        )}
        {warnings.length > 0 && (
          <span style={{ fontSize: 10, color: '#d29922' }}>{warnings.length} warning{warnings.length !== 1 ? 's' : ''}</span>
        )}
      </div>

      {!collapsed && (
        <div style={{ overflowY: 'auto', padding: '2px 6px 8px', minHeight: 0 }}>
          {ordered.length === 0 ? (
            <div style={{ fontSize: 11, color: '#3fb950', padding: '2px 4px' }}>✓ No issues</div>
          ) : (
            ordered.map((issue, i) => (
              <IssueRow key={`${issue.source}-${issue.code}-${i}`} issue={issue} onClick={onRowClick} />
            ))
          )}
        </div>
      )}
    </div>
  )
}

const IssueRow: React.FC<{ issue: UnifiedIssue; onClick: (issue: UnifiedIssue) => void }> = ({ issue, onClick }) => {
  const [hover, setHover] = useState(false)
  const clickable = !!issue.featureId
  const dot = issue.severity === 'error' ? '#f85149' : '#d29922'
  return (
    <div
      onClick={() => clickable && onClick(issue)}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: 'flex', gap: 6, padding: '3px 4px', borderRadius: 4,
        cursor: clickable ? 'pointer' : 'default',
        background: hover && clickable ? '#21262d' : 'transparent',
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: dot, flexShrink: 0, marginTop: 4 }} />
      <div style={{ minWidth: 0, flex: 1 }}>
        <div style={{ fontSize: 11, color: '#c9d1d9', lineHeight: '15px' }}>{issue.message}</div>
        {issue.suggestion && (
          <div style={{ fontSize: 10, color: '#8b949e', lineHeight: '14px', marginTop: 1 }}>{issue.suggestion}</div>
        )}
      </div>
    </div>
  )
}
