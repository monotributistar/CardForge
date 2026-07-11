// IssuesList — every compile issue (geometry + manufacturing), merged via
// CompileStore.mergeIssues. Clicking a row with a featureId selects that
// feature (and switches to its face). Rendered inside the status-bar drawer.

import React, { useState } from 'react'
import { useCompileStore, mergeIssues, type UnifiedIssue } from '../state/CompileStore'
import { useDocumentStore, getActiveTab, findFeature } from '../state/DocumentStore'

export const IssuesList: React.FC = () => {
  const constraints = useCompileStore(s => s.constraints)
  const manufacturing = useCompileStore(s => s.manufacturing)

  const select = useDocumentStore(s => s.select)
  const setActiveFace = useDocumentStore(s => s.setActiveFace)
  const tab = useDocumentStore(getActiveTab)

  const issues = mergeIssues({ constraints, manufacturing })
  const errors = issues.filter(i => i.severity === 'error')
  const warnings = issues.filter(i => i.severity === 'warning')
  const ordered = [...errors, ...warnings] // errors first

  const onRowClick = (issue: UnifiedIssue) => {
    if (!issue.featureId || !tab) return
    const found = findFeature(tab.doc, issue.featureId)
    if (found) setActiveFace(found.face)
    select(issue.featureId)
  }

  return (
    <div style={{ padding: '6px 10px' }}>
      {ordered.length === 0 ? (
        <div style={{ fontSize: 12, color: '#3fb950', padding: '4px 2px' }}>✓ No issues — ready to print</div>
      ) : (
        ordered.map((issue, i) => (
          <IssueRow key={`${issue.source}-${issue.code}-${i}`} issue={issue} onClick={onRowClick} />
        ))
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
      title={clickable ? 'Click to select the affected feature' : undefined}
      style={{
        display: 'flex', gap: 7, padding: '5px 6px', borderRadius: 4,
        cursor: clickable ? 'pointer' : 'default',
        background: hover && clickable ? '#21262d' : 'transparent',
      }}
    >
      <span style={{ width: 7, height: 7, borderRadius: '50%', background: dot, flexShrink: 0, marginTop: 5 }} />
      <div style={{ minWidth: 0, flex: 1 }}>
        <div style={{ fontSize: 12, color: '#c9d1d9', lineHeight: '16px' }}>{issue.message}</div>
        {issue.suggestion && (
          <div style={{ fontSize: 11, color: '#8b949e', lineHeight: '15px', marginTop: 1 }}>{issue.suggestion}</div>
        )}
      </div>
    </div>
  )
}
