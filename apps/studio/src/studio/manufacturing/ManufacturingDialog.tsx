// ManufacturingDialog — process, profile, faces selection → API or CLI

import React, { useState } from 'react'
import { PROCESSES, type ManufacturingConfig, DEFAULT_CONFIG } from './ManufacturingPipeline'
import type { ManufacturingSession } from './ManufacturingSession'

interface Props {
  documentId: string
  documentJson: string | null
  session: ManufacturingSession | null
  onClose: () => void
  onManufacture: (config: ManufacturingConfig) => void
}

const S = {
  overlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 } as React.CSSProperties,
  dialog: { background: '#161b22', border: '1px solid #30363d', borderRadius: 12, padding: 24, maxWidth: 420, width: '90%', maxHeight: '85vh', overflow: 'auto', color: '#c9d1d9' } as React.CSSProperties,
  title: { fontSize: 18, fontWeight: 700, color: '#58a6ff', marginBottom: 16 } as React.CSSProperties,
  section: { marginBottom: 14 } as React.CSSProperties,
  st: { fontSize: 11, fontWeight: 600, color: '#8b949e', textTransform: 'uppercase' as const, marginBottom: 6 },
  radioGroup: { display: 'flex', flexWrap: 'wrap' as const, gap: 4 },
  radio: (active: boolean): React.CSSProperties => ({
    background: active ? '#1f6feb' : '#21262d', color: active ? '#fff' : '#8b949e',
    border: `1px solid ${active ? '#58a6ff' : '#30363d'}`, padding: '4px 10px', borderRadius: 6,
    cursor: 'pointer', fontSize: 12,
  }),
  btnRow: { display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 },
  btn: { background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d', padding: '6px 14px', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
  btnPrimary: { background: '#238636', color: '#fff', border: '1px solid #2ea043', padding: '6px 14px', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 600 },
  progress: { marginTop: 8 } as React.CSSProperties,
  progressBar: { height: 4, background: '#21262d', borderRadius: 2, overflow: 'hidden', marginBottom: 6 },
  progressFill: (pct: number): React.CSSProperties => ({ height: '100%', background: pct >= 100 ? '#3fb950' : '#58a6ff', width: `${pct}%`, transition: 'width 0.4s' }),
  stepItem: (status: string): React.CSSProperties => ({
    fontSize: 11, padding: '2px 0',
    color: status === 'done' ? '#3fb950' : status === 'running' ? '#58a6ff' : status === 'failed' ? '#f85149' : '#484f58',
  }),
  cmdBox: { background: '#0d1117', border: '1px solid #30363d', borderRadius: 6, padding: 10, fontFamily: 'monospace', fontSize: 11, color: '#7ee787', marginTop: 4, wordBreak: 'break-all' as const },
}

export const ManufacturingDialog: React.FC<Props> = ({ documentId, documentJson, session, onClose, onManufacture }) => {
  const [config, setConfig] = useState<ManufacturingConfig>(DEFAULT_CONFIG)
  const update = (patch: Partial<ManufacturingConfig>) => setConfig(c => ({ ...c, ...patch }))
  const process = PROCESSES.find(p => p.id === config.process)!

  const isRunning = session && session.status !== 'idle' && session.status !== 'done' && session.status !== 'failed'

  // If API is running (session active), show progress
  if (isRunning) {
    return (
      <div style={S.overlay} onClick={onClose}>
        <div style={S.dialog} onClick={e => e.stopPropagation()}>
          <div style={S.title}>Manufacturing...</div>
          <div style={S.progress}>
            <div style={S.progressBar}>
              <div style={S.progressFill(session.progress)} />
            </div>
            <div style={{ fontSize: 11, color: '#8b949e', marginBottom: 8 }}>
              {session.progress}%
            </div>
            {session.steps.map((s, i) => (
              <div key={i} style={S.stepItem(s.status)}>
                {s.status === 'done' ? '✓' : s.status === 'running' ? '●' : s.status === 'failed' ? '✗' : '○'} {s.name}
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // If done, show success briefly then auto-close
  if (session?.status === 'done') {
    return null // Auto-closed, results in Compiled Viewer
  }

  // If failed, show error
  if (session?.status === 'failed') {
    return (
      <div style={S.overlay} onClick={onClose}>
        <div style={S.dialog} onClick={e => e.stopPropagation()}>
          <div style={S.title}>Manufacture Failed</div>
          <div style={{ fontSize: 12, color: '#f85149', marginBottom: 12 }}>
            {session.error || 'Unknown error'}
          </div>
          <div style={S.btnRow}>
            <button style={S.btn} onClick={onClose}>Close</button>
          </div>
        </div>
      </div>
    )
  }

  // Config step: process, profile, faces, outputs
  return (
    <div style={S.overlay} onClick={onClose}>
      <div style={S.dialog} onClick={e => e.stopPropagation()}>
        <div style={S.title}>Manufacture</div>

        <Section t="Process">
          <div style={S.radioGroup}>
            {PROCESSES.map(p => (
              <button key={p.id} style={S.radio(config.process === p.id)}
                onClick={() => update({ process: p.id, profile: p.profiles[0] })}>
                {config.process === p.id ? '●' : '○'} {p.label}
              </button>
            ))}
          </div>
        </Section>

        <Section t="Profile">
          <div style={S.radioGroup}>
            {process.profiles.map(pf => (
              <button key={pf} style={S.radio(config.profile === pf)}
                onClick={() => update({ profile: pf })}>
                {config.profile === pf ? '●' : '○'} {pf}
              </button>
            ))}
          </div>
        </Section>

        <Section t="Presentation Face">
          <div style={{ fontSize: 10, color: '#484f58', marginBottom: 4 }}>Face shown to the end user</div>
          <div style={S.radioGroup}>
            {(['front', 'back'] as const).map(f => (
              <button key={f} style={S.radio(config.presentationFace === f)}
                onClick={() => update({ presentationFace: f })}>
                {config.presentationFace === f ? '●' : '○'} {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </Section>

        <Section t="Print Face (FDM)">
          <div style={{ fontSize: 10, color: '#484f58', marginBottom: 4 }}>Face on build plate</div>
          <div style={S.radioGroup}>
            {(['front', 'back'] as const).map(f => (
              <button key={f} style={S.radio(config.preferredPrintFace === f)}
                onClick={() => update({ preferredPrintFace: f })}>
                {config.preferredPrintFace === f ? '●' : '○'} {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </Section>

        <div style={S.btnRow}>
          <button style={S.btn} onClick={onClose}>Cancel</button>
          <button style={S.btnPrimary} onClick={() => onManufacture(config)}>
            Manufacture
          </button>
        </div>
      </div>
    </div>
  )
}

const Section: React.FC<{ t: string; children: React.ReactNode }> = ({ t, children }) => (
  <div style={S.section}><div style={S.st}>{t}</div>{children}</div>
)
