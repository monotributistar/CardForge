// VerdictBadge — the unified manufacturability verdict, shown as a single
// green/amber/red pill. Used in the status bar and the issues drawer header
// so every surface agrees on one answer: can this piece be printed?

import React from 'react'
import { useCompileStore, computeVerdict, VERDICT_COLORS, type Verdict } from '../state/CompileStore'

// Soft fill + readable text per level (text ≥ 4.5:1 on its fill).
const CHIP: Record<Verdict['level'], { bg: string; fg: string }> = {
  ok: { bg: '#15301F', fg: '#54C98C' },
  warn: { bg: '#332714', fg: '#E7B45A' },
  blocked: { bg: '#331717', fg: '#F08A8A' },
  pending: { bg: '#332714', fg: '#E7B45A' },
  none: { bg: '#1E232A', fg: '#AEB6C0' },
}

/** Read the live verdict from the compile store. */
export function useVerdict(): Verdict {
  const status = useCompileStore(s => s.status)
  const constraints = useCompileStore(s => s.constraints)
  const manufacturing = useCompileStore(s => s.manufacturing)
  const error = useCompileStore(s => s.error)
  return computeVerdict({ status, constraints, manufacturing, error })
}

export const VerdictBadge: React.FC<{ verdict: Verdict; compact?: boolean }> = ({ verdict, compact }) => {
  const chip = CHIP[verdict.level]
  const n = verdict.blockers.length || verdict.warnings.length
  const detail = verdict.blockers.length
    ? `${verdict.blockers.length} ${verdict.blockers.length === 1 ? 'bloqueo' : 'bloqueos'}`
    : verdict.warnings.length
      ? `${verdict.warnings.length} ${verdict.warnings.length === 1 ? 'aviso' : 'avisos'}`
      : ''
  return (
    <span
      title={detail ? `${verdict.label} · ${detail}` : verdict.label}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 7,
        background: chip.bg, color: chip.fg,
        borderRadius: 999, padding: compact ? '3px 10px' : '4px 12px',
        fontSize: compact ? 11 : 12, fontWeight: 600, whiteSpace: 'nowrap',
      }}
    >
      <span style={{ width: 9, height: 9, borderRadius: '50%', background: VERDICT_COLORS[verdict.level], flexShrink: 0 }} />
      {verdict.label}
      {!compact && detail ? <span style={{ fontWeight: 400, opacity: 0.85 }}>· {detail}</span> : null}
    </span>
  )
}
