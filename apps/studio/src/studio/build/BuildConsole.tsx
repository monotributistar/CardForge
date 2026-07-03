// Build Console — shows build progress, steps, and logs

import React from 'react'

interface BuildConsoleProps {
  isBuilding: boolean
  messages: string[]
  progress: number
  steps: Array<{ name: string; status: string }>
}

export const BuildConsole: React.FC<BuildConsoleProps> = ({ isBuilding, messages, progress, steps }) => {
  if (!isBuilding && messages.length === 0 && steps.length === 0) {
    return (
      <div style={{ fontSize: 11, color: '#484f58', fontStyle: 'italic', padding: '4px 0' }}>
        Build console — logs appear here during manufacture
      </div>
    )
  }

  return (
    <div style={{ width: '100%' }}>
      {/* Progress bar */}
      {(isBuilding || progress > 0) && (
        <div style={{ marginBottom: 4 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 2 }}>
            <span style={{ color: '#8b949e' }}>
              {progress < 100 ? 'Manufacturing...' : 'Manufacture complete'}
            </span>
            <span style={{ color: '#58a6ff' }}>{Math.round(progress)}%</span>
          </div>
          <div style={{ height: 3, background: '#21262d', borderRadius: 2, overflow: 'hidden' }}>
            <div style={{
              height: '100%', background: progress >= 100 ? '#3fb950' : '#58a6ff',
              width: `${progress}%`, transition: 'width 0.3s',
            }} />
          </div>
        </div>
      )}

      {/* Steps */}
      {steps.length > 0 && (
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 4 }}>
          {steps.map((s, i) => (
            <span key={i} style={{ fontSize: 11, color: s.status === 'done' ? '#3fb950' : s.status === 'running' ? '#58a6ff' : s.status === 'failed' ? '#f85149' : '#484f58' }}>
              {s.status === 'done' ? '✓' : s.status === 'failed' ? '✗' : s.status === 'running' ? '●' : '○'} {s.name}
            </span>
          ))}
        </div>
      )}

      {/* Logs */}
      {messages.length > 0 && (
        <div style={{ maxHeight: 40, overflow: 'auto', fontFamily: 'monospace', fontSize: 10, color: '#8b949e' }}>
          {messages.slice(-3).map((m, i) => (
            <div key={i}>{m}</div>
          ))}
        </div>
      )}
    </div>
  )
}
