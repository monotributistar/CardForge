// PublishDialog — shows publish summary before confirming

import React from 'react'
import type { PublishResult } from './PublishService'

interface PublishDialogProps {
  result: PublishResult | null
  onClose: () => void
  onConfirm: () => void
}

const S = {
  overlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 } as React.CSSProperties,
  dialog: { background: '#161b22', border: '1px solid #30363d', borderRadius: 12, padding: 24, maxWidth: 480, width: '90%', maxHeight: '80vh', overflow: 'auto', color: '#c9d1d9' } as React.CSSProperties,
  title: { fontSize: 18, fontWeight: 700, color: '#58a6ff', marginBottom: 16 } as React.CSSProperties,
  section: { marginBottom: 14 } as React.CSSProperties,
  st: { fontSize: 11, fontWeight: 600, color: '#8b949e', textTransform: 'uppercase' as const, marginBottom: 6 },
  row: { display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '2px 0' },
  label: { color: '#8b949e' },
  value: { color: '#c9d1d9' },
  file: { fontSize: 11, color: '#8b949e', padding: '1px 0' },
  btnRow: { display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 },
  btn: { background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d', padding: '6px 14px', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
  btnPrimary: { background: '#238636', color: '#fff', border: '1px solid #2ea043', padding: '6px 14px', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 600 },
  btnDanger: { background: '#da3633', color: '#fff', border: '1px solid #f85149', padding: '6px 14px', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
}

export const PublishDialog: React.FC<PublishDialogProps> = ({ result, onClose, onConfirm }) => {
  if (!result) return null
  const m = result.manifest

  return (
    <div style={S.overlay} onClick={onClose}>
      <div style={S.dialog} onClick={e => e.stopPropagation()}>
        <div style={S.title}>Publish Manufacturing Package</div>

        <div style={S.section}>
          <div style={S.st}>Document</div>
          <div style={S.row}><span style={S.label}>Name</span><span style={S.value}>{m.document}</span></div>
          <div style={S.row}><span style={S.label}>Version</span><span style={S.value}>{m.version}</span></div>
        </div>

        <div style={S.section}>
          <div style={S.st}>Manufacturing</div>
          <div style={S.row}>
            <span style={S.label}>Score</span>
            <span style={{ ...S.value, color: m.score >= 80 ? '#3fb950' : '#f85149', fontWeight: 700 }}>{m.score}/100 — {m.scoreLabel}</span>
          </div>
          <div style={S.row}><span style={S.label}>Profile</span><span style={S.value}>{m.profile} — {m.nozzle}mm</span></div>
          <div style={S.row}><span style={S.label}>Material</span><span style={S.value}>{m.material}</span></div>
          <div style={S.row}><span style={S.label}>Colors</span><span style={S.value}>{m.colorCount}</span></div>
        </div>

        <div style={S.section}>
          <div style={S.st}>Ready to Print?</div>
          <div style={{ fontSize: 12 }}>✅ Preview generated</div>
          <div style={{ fontSize: 12 }}>{result.errors.length === 0 ? '✅' : '❌'} Manufacturing check passed</div>
          <div style={{ fontSize: 12 }}>✅ {m.files.length} files in package</div>
        </div>

        {result.errors.length > 0 && (
          <div style={S.section}>
            <div style={{ ...S.st, color: '#f85149' }}>Errors</div>
            {result.errors.map((e, i) => <div key={i} style={{ fontSize: 11, color: '#f85149' }}>• {e}</div>)}
          </div>
        )}
        {result.warnings.length > 0 && (
          <div style={S.section}>
            <div style={{ ...S.st, color: '#d29922' }}>Warnings</div>
            {result.warnings.map((w, i) => <div key={i} style={{ fontSize: 11, color: '#d29922' }}>• {w}</div>)}
          </div>
        )}

        <div style={S.btnRow}>
          <button style={S.btn} onClick={onClose}>Cancel</button>
          {result.errors.length === 0 && (
            <button style={S.btnPrimary} onClick={onConfirm}>Publish Package</button>
          )}
          {result.errors.length > 0 && (
            <button style={S.btnDanger} onClick={onConfirm}>Publish Anyway</button>
          )}
        </div>
      </div>
    </div>
  )
}
