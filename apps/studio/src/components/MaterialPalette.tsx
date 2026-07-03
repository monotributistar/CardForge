// MaterialPalette — editable materials list (left panel, below FeatureTree).
// Color / name / slot / role edits go through DocumentStore.applyEdit
// (undoable); color changes live-recompile via CompileStore's subscription.
// Delete is disabled while a material is referenced by any feature or is
// the last 'base' material.

import React, { useRef, useState } from 'react'
import type { Material } from '../types/cardforge'
import { useDocumentStore, getActiveTab } from '../state/DocumentStore'

const ROLES: Array<NonNullable<Material['role']>> = ['base', 'text', 'accent', 'detail', 'support']

const smallInputStyle: React.CSSProperties = {
  background: '#0d1117', color: '#c9d1d9', border: '1px solid #30363d',
  borderRadius: 4, padding: '2px 4px', fontSize: 11, minWidth: 0,
}

export const MaterialPalette: React.FC = () => {
  const tab = useDocumentStore(getActiveTab)
  const applyEdit = useDocumentStore(s => s.applyEdit)
  if (!tab) return null
  const doc = tab.doc

  const editMaterial = (id: string, fn: (m: Material) => void, snapshot = true) => {
    applyEdit(d => {
      const m = d.materials.find(x => x.id === id)
      if (m) fn(m)
    }, { snapshot })
  }

  /** Why this material cannot be deleted, or null if it can. */
  const deleteBlockReason = (m: Material): string | null => {
    for (const face of ['front', 'back'] as const) {
      for (const f of doc.faces[face]?.features ?? []) {
        const label = f.name ?? f.id
        if (f.material === m.id) return `Used by feature "${label}"`
        if (f.relief.floorMaterial === m.id) return `Used as floor material by "${label}"`
        if (f.type === 'icon' && f.colorMap && Object.values(f.colorMap).includes(m.id)) {
          return `Used in color map of "${label}"`
        }
      }
    }
    if (m.role === 'base' && doc.materials.filter(x => x.role === 'base').length === 1) {
      return 'Last base material'
    }
    return null
  }

  const addMaterial = () => {
    let n = 1
    while (doc.materials.some(m => m.id === `mat-${n}`)) n++
    const usedSlots = new Set(doc.materials.map(m => m.slot))
    let slot = 1
    while (slot < 16 && usedSlots.has(slot)) slot++
    applyEdit(d => {
      d.materials.push({ id: `mat-${n}`, name: `Material ${n}`, color: '#888888', slot, role: 'detail' })
    })
  }

  const deleteMaterial = (id: string) => {
    applyEdit(d => {
      d.materials = d.materials.filter(m => m.id !== id)
    })
  }

  return (
    <div style={{ borderTop: '1px solid #30363d', padding: '8px 10px', flexShrink: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.6, color: '#8b949e' }}>Materials</span>
        <button
          onClick={addMaterial}
          title="Add material"
          style={{ background: '#21262d', color: '#58a6ff', border: '1px solid #30363d', borderRadius: 4, width: 20, height: 20, cursor: 'pointer', fontSize: 13, lineHeight: '16px', padding: 0 }}
        >+</button>
      </div>
      {doc.materials.map(m => {
        const blockReason = deleteBlockReason(m)
        return (
          <div key={m.id} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '2px 0', fontSize: 11, color: '#c9d1d9' }}>
            <ColorSwatch
              value={m.color}
              onEdit={(color, snapshot) => editMaterial(m.id, x => { x.color = color }, snapshot)}
            />
            <NameInput value={m.name} onCommit={v => editMaterial(m.id, x => { x.name = v })} />
            <input
              type="number"
              min={1} max={16}
              value={m.slot ?? ''}
              title="Slot (1-16)"
              onChange={e => {
                const n = e.target.valueAsNumber
                if (!Number.isNaN(n)) editMaterial(m.id, x => { x.slot = Math.max(1, Math.min(16, Math.round(n))) })
              }}
              style={{ ...smallInputStyle, width: 34, flexShrink: 0 }}
            />
            <select
              value={m.role ?? ''}
              title="Role"
              onChange={e => editMaterial(m.id, x => { x.role = e.target.value as Material['role'] })}
              style={{ ...smallInputStyle, width: 58, flexShrink: 0, cursor: 'pointer' }}
            >
              {m.role == null && <option value="">—</option>}
              {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
            <button
              title={blockReason ?? 'Delete material'}
              disabled={blockReason != null}
              onClick={() => deleteMaterial(m.id)}
              style={{
                background: 'transparent', border: 'none', fontSize: 11, padding: 0, flexShrink: 0,
                cursor: blockReason ? 'not-allowed' : 'pointer', opacity: blockReason ? 0.35 : 1,
              }}
            >🗑</button>
          </div>
        )
      })}
    </div>
  )
}

// ── Row controls ─────────────────────────────────────────────────────

/**
 * Color swatch backed by <input type=color>. Browsers fire onChange
 * continuously while the picker is dragged, so snapshot only the first
 * change of a gesture (same coalescing as canvas drags); blur ends it.
 */
const ColorSwatch: React.FC<{ value: string; onEdit: (color: string, snapshot: boolean) => void }> = ({ value, onEdit }) => {
  const gestureStartedRef = useRef(false)
  return (
    <input
      type="color"
      value={value}
      title="Material color"
      onChange={e => {
        onEdit(e.target.value, !gestureStartedRef.current)
        gestureStartedRef.current = true
      }}
      onBlur={() => { gestureStartedRef.current = false }}
      style={{ width: 18, height: 18, padding: 0, border: '1px solid #30363d', borderRadius: 3, background: 'transparent', cursor: 'pointer', flexShrink: 0 }}
    />
  )
}

/** Name input that commits on blur/Enter (avoids clobbering while typing). */
const NameInput: React.FC<{ value: string; onCommit: (v: string) => void }> = ({ value, onCommit }) => {
  const [local, setLocal] = useState(value)
  React.useEffect(() => setLocal(value), [value])
  return (
    <input
      value={local}
      onChange={e => setLocal(e.target.value)}
      onBlur={() => { if (local !== value && local.trim()) onCommit(local.trim()) }}
      onKeyDown={e => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur() }}
      style={{ ...smallInputStyle, flex: 1 }}
    />
  )
}
