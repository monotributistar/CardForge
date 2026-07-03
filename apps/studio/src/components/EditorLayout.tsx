// EditorLayout — the IDE workspace:
// left: FeatureTree + Materials | center: 2D canvas / 3D viewer (Design|3D|Split)
// right: Inspector | bottom: compile status bar.

import React, { useState } from 'react'
import { useDocumentStore, getActiveTab } from '../state/DocumentStore'
import { useCompileStore, recompileActive, mergeIssues } from '../state/CompileStore'
import { FeatureTree } from './FeatureTree'
import { MaterialPalette } from './MaterialPalette'
import { IssuesPanel } from './IssuesPanel'
import { InteractiveCanvas } from '../studio/canvas/InteractiveCanvas'
import { CompiledViewer } from '../studio/canvas/CompiledViewer'
import { Inspector } from '../studio/inspector/Inspector'

type ViewMode = 'design' | '3d' | 'split'

export const EditorLayout: React.FC = () => {
  const tab = useDocumentStore(getActiveTab)
  const newTab = useDocumentStore(s => s.newTab)
  const [viewMode, setViewMode] = useState<ViewMode>('split')

  if (!tab) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12, color: '#484f58' }}>
        <div style={{ fontSize: 40 }}>🃏</div>
        <div style={{ fontSize: 14 }}>No document open</div>
        <button
          onClick={() => newTab()}
          style={{ background: '#1f6feb', color: '#fff', border: 'none', padding: '6px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}
        >New document</button>
      </div>
    )
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        {/* Left panel */}
        <div style={{ width: 240, flexShrink: 0, background: '#161b22', borderRight: '1px solid #30363d', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            <FeatureTree />
          </div>
          <MaterialPalette />
          <IssuesPanel />
        </div>

        {/* Center */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, minHeight: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 4, padding: 4, background: '#161b22', borderBottom: '1px solid #30363d', flexShrink: 0 }}>
            {(['design', '3d', 'split'] as const).map(m => (
              <button
                key={m}
                onClick={() => setViewMode(m)}
                style={{
                  background: viewMode === m ? '#1f6feb' : '#21262d',
                  color: viewMode === m ? '#fff' : '#8b949e',
                  border: '1px solid #30363d', padding: '2px 12px', borderRadius: 4, cursor: 'pointer', fontSize: 11,
                }}
              >{m === 'design' ? 'Design' : m === '3d' ? '3D' : 'Split'}</button>
            ))}
          </div>
          <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
            {(viewMode === 'design' || viewMode === 'split') && (
              <div style={{ flex: 1, minWidth: 0, borderRight: viewMode === 'split' ? '1px solid #30363d' : 'none' }}>
                <InteractiveCanvas />
              </div>
            )}
            {(viewMode === '3d' || viewMode === 'split') && (
              <div style={{ flex: 1, minWidth: 0 }}>
                <CompiledViewer />
              </div>
            )}
          </div>
        </div>

        {/* Right panel */}
        <div style={{ width: 300, flexShrink: 0, background: '#161b22', borderLeft: '1px solid #30363d', minHeight: 0 }}>
          <Inspector />
        </div>
      </div>

      <StatusBar />
    </div>
  )
}

// ── Status bar ───────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  idle: '#484f58',
  compiling: '#d29922',
  ok: '#3fb950',
  error: '#f85149',
}

const StatusBar: React.FC = () => {
  const status = useCompileStore(s => s.status)
  const error = useCompileStore(s => s.error)
  const manufacturing = useCompileStore(s => s.manufacturing)
  const constraints = useCompileStore(s => s.constraints)
  const stats = useCompileStore(s => s.stats)

  const issues = mergeIssues({ constraints, manufacturing })
  const errorCount = issues.filter(i => i.severity === 'error').length
  const warningCount = issues.filter(i => i.severity === 'warning').length

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 14, padding: '4px 12px',
      background: '#161b22', borderTop: '1px solid #30363d', fontSize: 11, color: '#8b949e', flexShrink: 0, minHeight: 24,
    }}>
      <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: STATUS_COLORS[status] }} />
        {status === 'idle' ? 'Idle' : status === 'compiling' ? 'Compiling…' : status === 'ok' ? 'Compiled' : 'Error'}
      </span>
      {status === 'error' && error && (
        <>
          <span style={{ color: '#f85149', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 420 }} title={error}>{error}</span>
          <button
            onClick={recompileActive}
            style={{ background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d', borderRadius: 4, padding: '1px 8px', fontSize: 10, cursor: 'pointer' }}
          >Retry</button>
        </>
      )}
      {manufacturing && (
        <span title={manufacturing.isManufacturable ? 'Manufacturable' : 'Not manufacturable'}>
          Score: <span style={{ color: manufacturing.isManufacturable ? '#3fb950' : '#f85149' }}>
            {manufacturing.score} ({manufacturing.scoreLabel})
          </span>
        </span>
      )}
      {(errorCount > 0 || warningCount > 0) && (
        <span>
          {errorCount > 0 && <span style={{ color: '#f85149' }}>{errorCount} error{errorCount !== 1 ? 's' : ''}</span>}
          {errorCount > 0 && warningCount > 0 && ' · '}
          {warningCount > 0 && <span style={{ color: '#d29922' }}>{warningCount} warning{warningCount !== 1 ? 's' : ''}</span>}
        </span>
      )}
      <span style={{ flex: 1 }} />
      {stats && (
        <span style={{ color: '#484f58' }}>
          {stats.featureCount} features · {stats.compileMs} ms · {(stats.threeMfBytes / 1024).toFixed(1)} KB 3MF
        </span>
      )}
    </div>
  )
}
