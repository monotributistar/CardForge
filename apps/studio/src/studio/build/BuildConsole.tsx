// Build Console — shows build logs and progress
//
// Placeholder for future build output, warnings, errors.
// Will consume a BuildService in future phases.

import React from 'react'

interface BuildConsoleProps {
  isBuilding: boolean
  messages: string[]
}

export const BuildConsole: React.FC<BuildConsoleProps> = ({ isBuilding, messages }) => {
  if (messages.length === 0 && !isBuilding) {
    return (
      <div style={{ fontSize: 12, color: '#484f58', fontStyle: 'italic', padding: 8 }}>
        Build console — logs will appear here
      </div>
    )
  }

  return (
    <div style={{ padding: 8, maxHeight: 120, overflow: 'auto', fontFamily: 'monospace', fontSize: 11 }}>
      {messages.map((msg, i) => (
        <div key={i} style={{ color: '#8b949e', padding: '1px 0' }}>{msg}</div>
      ))}
      {isBuilding && <div style={{ color: '#58a6ff' }}>Building...</div>}
    </div>
  )
}
