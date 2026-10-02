// EditorLayout — the IDE workspace.
// Center: 2D canvas / 3D viewer (Design|3D|Split).
// Right: single side panel like a design editor — Layers (feature tree) on
//        top, Properties (inspector) below, Materials collapsed at the bottom.
//        On narrow viewports the panel becomes an overlay drawer (☰ button).
// Bottom: status bar; issue counts toggle an Issues drawer above it.

import React, { useEffect, useState } from 'react'
import { useDocumentStore, getActiveTab } from '../state/DocumentStore'
import { useCompileStore, recompileActive } from '../state/CompileStore'
import { useEngineStore, refreshEngine } from '../state/EngineStore'
import { useUIStore } from '../state/UIStore'
import { FeatureTree } from './FeatureTree'
import { MaterialPalette } from './MaterialPalette'
import { IssuesList } from './IssuesPanel'
import { VerdictBadge, useVerdict } from './VerdictBadge'
import { InteractiveCanvas } from '../studio/canvas/InteractiveCanvas'
import { CompiledViewer } from '../studio/canvas/CompiledViewer'
import { Inspector } from '../studio/inspector/Inspector'
import { useIsNarrow } from './ui'

type ViewMode = 'design' | '3d' | 'split'

// Layers on top, properties below, materials at the bottom — the panel body
// is shared by the docked (desktop) and drawer (narrow) presentations.
const SidePanel: React.FC = () => (
  <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, height: '100%' }}>
    <div style={{ maxHeight: '40%', overflowY: 'auto', flexShrink: 0, borderBottom: '1px solid #2A313A' }}>
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
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12, color: '#5B6673' }}>
        <div style={{ fontSize: 40 }}>🃏</div>
        <div style={{ fontSize: 14 }}>No document open</div>
        <button
          onClick={openWizard}
          style={{ background: '#C24A1C', color: '#fff', border: 'none', padding: '8px 18px', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}
        >New card…</button>
      </div>
    )
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div style={{ flex: 1, display: 'flex', minHeight: 0, position: 'relative' }}>
        {/* Center */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, minHeight: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 4, padding: 4, background: '#1A1E24', borderBottom: '1px solid #2A313A', flexShrink: 0 }}>
            {(['design', '3d', 'split'] as const).map(m => (
              <button
                key={m}
                onClick={() => setViewMode(m)}
                title={m === 'design' ? '2D editing view' : m === '3d' ? 'Compiled 3D preview — exactly what the export produces' : 'Both side by side'}
                style={{
                  background: viewMode === m ? '#C24A1C' : '#1E232A',
                  color: viewMode === m ? '#fff' : '#AEB6C0',
                  border: '1px solid #2A313A', padding: '4px 14px', borderRadius: 4, cursor: 'pointer', fontSize: 12,
                }}
              >{m === 'design' ? 'Design' : m === '3d' ? '3D' : 'Split'}</button>
            ))}
          </div>
          <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
            {(viewMode === 'design' || viewMode === 'split') && (
              <div style={{ flex: 1, minWidth: 0, borderRight: viewMode === 'split' ? '1px solid #2A313A' : 'none' }}>
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
          <div style={{ width: 320, flexShrink: 0, background: '#1A1E24', borderLeft: '1px solid #2A313A', minHeight: 0 }}>
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
              width: 'min(340px, 92vw)', background: '#1A1E24', borderLeft: '1px solid #2A313A',
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
              width: 46, height: 46, borderRadius: '50%', border: '1px solid #2A313A',
              background: '#C24A1C', color: '#fff', fontSize: 19, cursor: 'pointer',
              boxShadow: '0 4px 14px rgba(0,0,0,0.5)',
            }}
          >☰</button>
        )}
      </div>

      {/* Issues drawer — toggled from the status bar */}
      {issuesOpen && (
        <div style={{ height: 200, overflowY: 'auto', background: '#1A1E24', borderTop: '1px solid #2A313A', flexShrink: 0 }}>
          <IssuesList />
        </div>
      )}

      <StatusBar />
    </div>
  )
}

// ── Status bar ───────────────────────────────────────────────────────

const StatusBar: React.FC = () => {
  const status = useCompileStore(s => s.status)
  const error = useCompileStore(s => s.error)
  const manufacturing = useCompileStore(s => s.manufacturing)
  const stats = useCompileStore(s => s.stats)
  const engineStatus = useEngineStore(s => s.status)
  const issuesOpen = useUIStore(s => s.issuesOpen)
  const toggleIssues = useUIStore(s => s.toggleIssues)

  const verdict = useVerdict()
  const errorCount = verdict.blockers.length
  const warningCount = verdict.warnings.length

  // The engine is optional: when it's off, say so calmly (design keeps working)
  // rather than surfacing a red compile error.
  const engineOffline = engineStatus === 'offline'

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12, padding: '4px 12px',
      background: '#1A1E24', borderTop: '1px solid #2A313A', fontSize: 11, color: '#AEB6C0', flexShrink: 0, minHeight: 32,
    }}>
      {/* Unified verdict — the one answer every surface shares. */}
      <VerdictBadge verdict={verdict} />

      {engineOffline ? (
        <>
          <span style={{ color: '#5B6673', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 420 }}
            title="El diseño 2D, la validación y los arreglos funcionan sin motor. La vista 3D y la exportación lo necesitan.">
            Sin motor · diseño disponible sin conexión
          </span>
          <button
            onClick={() => void refreshEngine()}
            style={{ background: '#1E232A', color: '#E6E9ED', border: '1px solid #2A313A', borderRadius: 4, padding: '2px 8px', fontSize: 10, cursor: 'pointer' }}
          >Conectar</button>
        </>
      ) : status === 'error' && error && (
        <>
          <span style={{ color: '#E04343', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 380 }} title={error}>{error}</span>
          <button
            onClick={recompileActive}
            style={{ background: '#1E232A', color: '#E6E9ED', border: '1px solid #2A313A', borderRadius: 4, padding: '2px 8px', fontSize: 10, cursor: 'pointer' }}
          >Reintentar</button>
        </>
      )}

      <button
        onClick={toggleIssues}
        title={issuesOpen ? 'Ocultar la lista de avisos' : 'Ver cada aviso y error de fabricación'}
        style={{
          background: issuesOpen ? '#1E232A' : 'transparent', color: '#AEB6C0',
          border: '1px solid #2A313A', borderRadius: 4, padding: '3px 10px', fontSize: 11, cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 6,
        }}
      >
        <span>{issuesOpen ? '▾' : '▴'} Revisar</span>
        {errorCount > 0 && <span style={{ color: '#E04343' }}>{errorCount}</span>}
        {warningCount > 0 && <span style={{ color: '#E0A32E' }}>{warningCount}</span>}
        {errorCount === 0 && warningCount === 0 && <span style={{ color: '#1F9D63' }}>✓</span>}
      </button>

      <span style={{ flex: 1 }} />

      {/* Analyzer score — secondary detail only; the verdict is the headline. */}
      {manufacturing && (
        <span style={{ color: '#5B6673' }} title="Puntaje del analizador de fabricabilidad (solo ve sus propias reglas)">
          Análisis {manufacturing.score}
        </span>
      )}
      {stats && (
        <span style={{ color: '#5B6673' }}>
          {stats.featureCount} features · {stats.compileMs} ms · {(stats.threeMfBytes / 1024).toFixed(1)} KB 3MF
        </span>
      )}
    </div>
  )
}
