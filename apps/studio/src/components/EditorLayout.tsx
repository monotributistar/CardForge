// EditorLayout — the IDE workspace.
// Center: 2D canvas / 3D viewer (Design|3D|Split).
// Right: single side panel like a design editor — Layers (feature tree) on
//        top, Properties (inspector) below, Materials collapsed at the bottom.
//        On narrow viewports the panel becomes an overlay drawer (☰ button).
// Bottom: status bar; issue counts toggle an Issues drawer above it.

import React, { useEffect, useState } from 'react'
import { useDocumentStore, getActiveTab } from '../state/DocumentStore'
import { useCompileStore, recompileActive, mergeIssues } from '../state/CompileStore'
import { useUIStore } from '../state/UIStore'
import { FeatureTree } from './FeatureTree'
import { MaterialPalette } from './MaterialPalette'
import { IssuesList } from './IssuesPanel'
import { InteractiveCanvas } from '../studio/canvas/InteractiveCanvas'
import { CompiledViewer } from '../studio/canvas/CompiledViewer'
import { Inspector } from '../studio/inspector/Inspector'
import { useIsNarrow } from './ui'

type ViewMode = 'design' | '3d' | 'split'

// Layers on top, properties below, materials at the bottom — the panel body
// is shared by the docked (desktop) and drawer (narrow) presentations.
const SidePanel: React.FC = () => (
  <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, height: '100%' }}>
    <div style={{ maxHeight: '40%', overflowY: 'auto', flexShrink: 0, borderBottom: '1px solid #30363d' }}>
      <FeatureTree />
    </div>
    <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
      <Inspector />
    </div>
    <MaterialPalette />
  </div>
)

export const EditorLayout: React.FC = () => {
  const tab = useDocumentStore(getActiveTab)
  const openWizard = useUIStore(s => s.openWizard)
  const issuesOpen = useUIStore(s => s.issuesOpen)
  const panelOpen = useUIStore(s => s.panelOpen)
  const setPanelOpen = useUIStore(s => s.setPanelOpen)
  const narrow = useIsNarrow()
  const [viewMode, setViewMode] = useState<ViewMode>('split')

  // Narrow viewports can't afford Split — fall back to Design once.
  useEffect(() => {
    if (narrow) setViewMode(m => (m === 'split' ? 'design' : m))
  }, [narrow])

  if (!tab) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12, color: '#484f58' }}>
        <div style={{ fontSize: 40 }}>🃏</div>
        <div style={{ fontSize: 14 }}>No document open</div>
        <button
          onClick={openWizard}
          style={{ background: '#1f6feb', color: '#fff', border: 'none', padding: '8px 18px', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}
        >New card…</button>
      </div>
    )
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div style={{ flex: 1, display: 'flex', minHeight: 0, position: 'relative' }}>
        {/* Center */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, minHeight: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 4, padding: 4, background: '#161b22', borderBottom: '1px solid #30363d', flexShrink: 0 }}>
            {(['design', '3d', 'split'] as const).map(m => (
              <button
                key={m}
                onClick={() => setViewMode(m)}
                title={m === 'design' ? '2D editing view' : m === '3d' ? 'Compiled 3D preview — exactly what the export produces' : 'Both side by side'}
                style={{
                  background: viewMode === m ? '#1f6feb' : '#21262d',
                  color: viewMode === m ? '#fff' : '#8b949e',
                  border: '1px solid #30363d', padding: '4px 14px', borderRadius: 4, cursor: 'pointer', fontSize: 12,
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

        {/* Right panel — docked on desktop, overlay drawer when narrow */}
        {!narrow && (
          <div style={{ width: 320, flexShrink: 0, background: '#161b22', borderLeft: '1px solid #30363d', minHeight: 0 }}>
            <SidePanel />
          </div>
        )}
        {narrow && panelOpen && (
          <>
            <div
              onClick={() => setPanelOpen(false)}
              style={{ position: 'absolute', inset: 0, background: 'rgba(1,4,9,0.5)', zIndex: 90 }}
            />
            <div style={{
              position: 'absolute', top: 0, right: 0, bottom: 0, zIndex: 91,
              width: 'min(340px, 92vw)', background: '#161b22', borderLeft: '1px solid #30363d',
              boxShadow: '-8px 0 24px rgba(0,0,0,0.5)',
            }}>
              <SidePanel />
            </div>
          </>
        )}
        {narrow && !panelOpen && (
          <button
            onClick={() => setPanelOpen(true)}
            title="Layers & properties"
            style={{
              position: 'absolute', right: 14, bottom: 14, zIndex: 80,
              width: 46, height: 46, borderRadius: '50%', border: '1px solid #30363d',
              background: '#1f6feb', color: '#fff', fontSize: 19, cursor: 'pointer',
              boxShadow: '0 4px 14px rgba(0,0,0,0.5)',
            }}
          >☰</button>
        )}
      </div>

      {/* Issues drawer — toggled from the status bar */}
      {issuesOpen && (
        <div style={{ height: 200, overflowY: 'auto', background: '#161b22', borderTop: '1px solid #30363d', flexShrink: 0 }}>
          <IssuesList />
        </div>
      )}

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
  const issuesOpen = useUIStore(s => s.issuesOpen)
  const toggleIssues = useUIStore(s => s.toggleIssues)

  const issues = mergeIssues({ constraints, manufacturing })
  const errorCount = issues.filter(i => i.severity === 'error').length
  const warningCount = issues.filter(i => i.severity === 'warning').length

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 14, padding: '4px 12px',
      background: '#161b22', borderTop: '1px solid #30363d', fontSize: 11, color: '#8b949e', flexShrink: 0, minHeight: 28,
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
            style={{ background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d', borderRadius: 4, padding: '2px 8px', fontSize: 10, cursor: 'pointer' }}
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
      <button
        onClick={toggleIssues}
        title={issuesOpen ? 'Hide the issues list' : 'Show every compile warning and error'}
        style={{
          background: issuesOpen ? '#21262d' : 'transparent', color: '#8b949e',
          border: '1px solid #30363d', borderRadius: 4, padding: '3px 10px', fontSize: 11, cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 6,
        }}
      >
        <span>{issuesOpen ? '▾' : '▴'} Issues</span>
        {errorCount > 0 && <span style={{ color: '#f85149' }}>{errorCount}</span>}
        {warningCount > 0 && <span style={{ color: '#d29922' }}>{warningCount}</span>}
        {errorCount === 0 && warningCount === 0 && <span style={{ color: '#3fb950' }}>✓</span>}
      </button>
      <span style={{ flex: 1 }} />
      {stats && (
        <span style={{ color: '#484f58' }}>
          {stats.featureCount} features · {stats.compileMs} ms · {(stats.threeMfBytes / 1024).toFixed(1)} KB 3MF
        </span>
      )}
    </div>
  )
}
