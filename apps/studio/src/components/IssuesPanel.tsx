// IssuesList — the "review & fix" panel. Three layers:
//   1. the unified verdict header (same answer as the status bar);
//   2. quick fixes — deterministic problems the Studio can detect and repair
//      client-side (no Core round-trip), each with a one-click fix;
//   3. every compile issue (geometry + manufacturing), merged. Clicking a row
//      jumps to the affected feature and its face.
// Rendered inside the status-bar drawer.

import React, { useState } from 'react'
import { useCompileStore, mergeIssues, type UnifiedIssue } from '../state/CompileStore'
import { useDocumentStore, getActiveTab, findFeature, type TabState } from '../state/DocumentStore'
import type { DocumentV2, FaceId } from '../types/cardforge'
import { MIN_POCKET_FLOOR } from '../studio/document/defaults'
import { VerdictBadge, useVerdict } from './VerdictBadge'

// ── Client-side quick fixes ──────────────────────────────────────────
// Problems the Studio can see and repair without the Core — so they work
// even offline, and give the user a one-click repair instead of a hint.

interface QuickFix {
  id: string
  featureId: string
  face: FaceId
  title: string
  action: string
  apply: (doc: DocumentV2) => void
}

/** Scan a document for deterministically-fixable problems. */
export function quickFixes(doc: DocumentV2): QuickFix[] {
  const out: QuickFix[] = []
  const thickness = doc.object?.thickness ?? 0

  // 1. Back face is bed-facing — emboss is refused there and the feature
  //    produces no geometry (the classic "score 100, blank back" trap).
  for (const f of doc.faces.back?.features ?? []) {
    if (f.relief?.mode === 'emboss') {
      out.push({
        id: `back-emboss-${f.id}`, featureId: f.id, face: 'back',
        title: `"${f.name ?? f.type}" usa relieve emboss en la cara trasera — no imprime nada ahí.`,
        action: 'Cambiar a flush',
        apply: d => {
          const feat = d.faces.back?.features.find(x => x.id === f.id)
          if (feat) feat.relief = { mode: 'flush', depth: feat.relief.height ?? 0.4 }
        },
      })
    }
  }

  // 2. A pocket deeper than the body leaves it punches through (no floor).
  for (const face of ['front', 'back'] as const) {
    for (const f of doc.faces[face]?.features ?? []) {
      if (f.type !== 'pocket') continue
      const cavity = (f.depth ?? 0) + (f.depthClearance ?? 0)
      const maxDepth = thickness - MIN_POCKET_FLOOR
      if (thickness > 0 && cavity > maxDepth) {
        const safe = Math.max(0.4, Math.round((maxDepth - (f.depthClearance ?? 0)) * 10) / 10)
        out.push({
          id: `pocket-through-${f.id}`, featureId: f.id, face,
          title: `El pocket "${f.name ?? 'pocket'}" perfora la pieza (deja menos de ${MIN_POCKET_FLOOR} mm de piso).`,
          action: `Reducir a ${safe} mm`,
          apply: d => {
            const feat = d.faces[face]?.features.find(x => x.id === f.id)
            if (feat && feat.type === 'pocket') feat.depth = safe
          },
        })
      }
    }
  }

  return out
}

// ── Panel ────────────────────────────────────────────────────────────

export const IssuesList: React.FC = () => {
  const constraints = useCompileStore(s => s.constraints)
  const manufacturing = useCompileStore(s => s.manufacturing)

  const select = useDocumentStore(s => s.select)
  const setActiveFace = useDocumentStore(s => s.setActiveFace)
  const applyEdit = useDocumentStore(s => s.applyEdit)
  const tab = useDocumentStore(getActiveTab)
  const verdict = useVerdict()

  const issues = mergeIssues({ constraints, manufacturing })
  const errors = issues.filter(i => i.severity === 'error')
  const warnings = issues.filter(i => i.severity === 'warning')
  const ordered = [...errors, ...warnings] // errors first

  const fixes = tab ? quickFixes(tab.doc) : []

  const jumpTo = (featureId: string | undefined, t: TabState | null) => {
    if (!featureId || !t) return
    const found = findFeature(t.doc, featureId)
    if (found) setActiveFace(found.face)
    select(featureId)
  }

  const applyFix = (fix: QuickFix) => {
    applyEdit(d => fix.apply(d))
    setActiveFace(fix.face)
    select(fix.featureId)
  }

  return (
    <div style={{ padding: '8px 10px' }}>
      {/* Verdict header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '2px 2px 10px', borderBottom: '1px solid #2A313A', marginBottom: 8 }}>
        <VerdictBadge verdict={verdict} />
        <span style={{ fontSize: 11, color: '#5B6673' }}>
          {verdict.level === 'ok' ? 'La pieza cumple y se puede imprimir.'
            : verdict.level === 'blocked' ? 'Resolvé los bloqueos para poder imprimir.'
            : verdict.level === 'warn' ? 'Imprime, pero revisá los avisos.'
            : verdict.level === 'pending' ? 'Analizando el documento…'
            : 'Sin resultado de compilación.'}
        </span>
      </div>

      {/* Quick fixes */}
      {fixes.length > 0 && (
        <div style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: 0.6, textTransform: 'uppercase', color: '#E0A32E', margin: '2px 2px 6px' }}>
            Arreglos rápidos
          </div>
          {fixes.map(fix => (
            <div key={fix.id} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', padding: '7px 8px', background: '#231d1a', border: '1px solid #3a2c22', borderRadius: 6, marginBottom: 6 }}>
              <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#E0A32E', flexShrink: 0, marginTop: 5 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, color: '#E6E9ED', lineHeight: '16px' }}>{fix.title}</div>
              </div>
              <button
                onClick={() => applyFix(fix)}
                style={{ flexShrink: 0, background: '#C24A1C', color: '#fff', border: 'none', borderRadius: 5, padding: '4px 10px', fontSize: 11, fontWeight: 600, cursor: 'pointer' }}
              >{fix.action}</button>
            </div>
          ))}
        </div>
      )}

      {/* Compile issues */}
      {ordered.length === 0 ? (
        fixes.length === 0 && (
          <div style={{ fontSize: 12, color: '#1F9D63', padding: '4px 2px' }}>✓ Sin problemas — listo para imprimir</div>
        )
      ) : (
        ordered.map((issue, i) => (
          <IssueRow key={`${issue.source}-${issue.code}-${i}`} issue={issue} onClick={() => jumpTo(issue.featureId, tab)} />
        ))
      )}
    </div>
  )
}

const IssueRow: React.FC<{ issue: UnifiedIssue; onClick: () => void }> = ({ issue, onClick }) => {
  const [hover, setHover] = useState(false)
  const clickable = !!issue.featureId
  const dot = issue.severity === 'error' ? '#E04343' : '#E0A32E'
  return (
    <div
      onClick={() => clickable && onClick()}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      title={clickable ? 'Ir a la feature afectada' : undefined}
      style={{
        display: 'flex', gap: 7, padding: '5px 6px', borderRadius: 4, alignItems: 'flex-start',
        cursor: clickable ? 'pointer' : 'default',
        background: hover && clickable ? '#1E232A' : 'transparent',
      }}
    >
      <span style={{ width: 7, height: 7, borderRadius: '50%', background: dot, flexShrink: 0, marginTop: 5 }} />
      <div style={{ minWidth: 0, flex: 1 }}>
        <div style={{ fontSize: 12, color: '#E6E9ED', lineHeight: '16px' }}>{issue.message}</div>
        {issue.suggestion && (
          <div style={{ fontSize: 11, color: '#AEB6C0', lineHeight: '15px', marginTop: 1 }}>{issue.suggestion}</div>
        )}
      </div>
      {clickable && (
        <span style={{ flexShrink: 0, color: hover ? '#E8622C' : '#5B6673', fontSize: 12, marginTop: 2 }}>→</span>
      )}
    </div>
  )
}
