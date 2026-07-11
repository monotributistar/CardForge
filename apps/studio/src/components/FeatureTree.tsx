// FeatureTree — faces → features, with add / select / visibility / delete.

import React, { useState } from 'react'
import type { Feature, FaceId } from '../types/cardforge'
import { useDocumentStore, getActiveTab } from '../state/DocumentStore'
import { defaultFeature } from '../studio/document/defaults'

const TYPE_ICONS: Record<string, string> = {
  'text-block': 'T',
  'text-pattern': '⧉',
  'pattern': '▦',
  'qr': '▣',
  'icon': '🖼',
  'shape': '◇',
  'hole': '◎',
}

const ADDABLE: Array<{ type: Feature['type']; label: string }> = [
  { type: 'text-block', label: 'Text block' },
  { type: 'text-pattern', label: 'Text pattern' },
  { type: 'pattern', label: 'Pattern' },
  { type: 'qr', label: 'QR code' },
  { type: 'icon', label: 'Icon' },
  { type: 'shape', label: 'Shape' },
  { type: 'hole', label: 'Hole (keyring / lanyard)' },
]

export const FeatureTree: React.FC = () => {
  const tab = useDocumentStore(getActiveTab)
  const applyEdit = useDocumentStore(s => s.applyEdit)
  const select = useDocumentStore(s => s.select)
  const selectObject = useDocumentStore(s => s.selectObject)
  const toggleSelect = useDocumentStore(s => s.toggleSelect)
  const setActiveFace = useDocumentStore(s => s.setActiveFace)
  const [addMenuOpen, setAddMenuOpen] = useState(false)

  if (!tab) {
    return <div style={{ padding: 12, color: '#484f58', fontSize: 12 }}>No document open</div>
  }
  const doc = tab.doc

  const materialColor = (id: string) => doc.materials.find(m => m.id === id)?.color ?? '#8b949e'

  const addFeature = (type: Feature['type']) => {
    setAddMenuOpen(false)
    const face = tab.activeFace
    // Prefer a non-base material that exists in this document
    const material = doc.materials.find(m => m.role === 'text')?.id
      ?? doc.materials.find(m => m.role !== 'base')?.id
      ?? doc.materials[0]?.id
      ?? 'text'
    const feature = defaultFeature(type, face, material)
    applyEdit(d => {
      if (!d.faces[face]) d.faces[face] = { features: [] }
      d.faces[face]!.features.push(feature)
    })
    select(feature.id)
  }

  const deleteFeature = (face: FaceId, id: string) => {
    applyEdit(d => {
      const f = d.faces[face]
      if (f) f.features = f.features.filter(x => x.id !== id)
    })
    if (tab.selectedFeatureIds.includes(id)) toggleSelect(id)
  }

  const toggleVisible = (face: FaceId, id: string) => {
    applyEdit(d => {
      const f = d.faces[face]?.features.find(x => x.id === id)
      if (f) f.visible = f.visible === false
    })
  }

  // The kernel applies a face's features sorted by zOrder (list order breaks
  // ties); on overlap the LAST-applied feature keeps the shared volume.
  const applicationOrder = (features: Feature[]): Feature[] =>
    features
      .map((f, i) => [f, i] as const)
      .sort((a, b) => ((a[0].zOrder ?? 0) - (b[0].zOrder ?? 0)) || (a[1] - b[1]))
      .map(([f]) => f)

  /** Move a feature one step in the application order (dir +1 = applied
   * later = wins overlaps). Rewrites zOrder = position so the order you see
   * is exactly the order the kernel uses. */
  const moveFeature = (face: FaceId, id: string, dir: 1 | -1) => {
    applyEdit(d => {
      const fc = d.faces[face]
      if (!fc) return
      const ordered = applicationOrder(fc.features)
      const i = ordered.findIndex(f => f.id === id)
      const j = i + dir
      if (i < 0 || j < 0 || j >= ordered.length) return
      ;[ordered[i], ordered[j]] = [ordered[j], ordered[i]]
      ordered.forEach((f, idx) => { f.zOrder = idx })
      fc.features = ordered
    })
  }

  return (
    <div style={{ fontSize: 12, position: 'relative' }}>
      {/* Header with add menu */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 10px 4px' }}>
        <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.6, color: '#8b949e' }}>Features</span>
        <button
          onClick={() => setAddMenuOpen(o => !o)}
          title="Add feature to active face"
          style={{ background: '#21262d', color: '#58a6ff', border: '1px solid #30363d', borderRadius: 4, width: 24, height: 24, cursor: 'pointer', fontSize: 14, lineHeight: '18px', padding: 0 }}
        >+</button>
      </div>
      {addMenuOpen && (
        <div style={{
          position: 'absolute', right: 8, top: 30, zIndex: 20,
          background: '#161b22', border: '1px solid #30363d', borderRadius: 6,
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)', padding: 4, minWidth: 140,
        }}>
          {ADDABLE.map(a => (
            <div
              key={a.type}
              onClick={() => addFeature(a.type)}
              style={{ padding: '8px 10px', cursor: 'pointer', borderRadius: 4, display: 'flex', gap: 8, alignItems: 'center', color: '#c9d1d9', fontSize: 13 }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = '#21262d' }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent' }}
            >
              <span style={{ width: 16, textAlign: 'center', color: '#8b949e' }}>{TYPE_ICONS[a.type]}</span>
              {a.label}
              <span style={{ marginLeft: 'auto', fontSize: 10, color: '#484f58' }}>{tab.activeFace}</span>
            </div>
          ))}
        </div>
      )}

      {/* Base object node */}
      <div
        onClick={() => selectObject()}
        title="Edit the base card (outline, thickness, fill)"
        style={{
          display: 'flex', alignItems: 'center', gap: 6, padding: '7px 10px', minHeight: 30,
          cursor: 'pointer',
          background: tab.objectSelected ? 'rgba(88,166,255,0.15)' : 'transparent',
          borderLeft: tab.objectSelected ? '2px solid #58a6ff' : '2px solid transparent',
          color: tab.objectSelected ? '#58a6ff' : '#c9d1d9',
          fontWeight: tab.objectSelected ? 600 : 400,
        }}
      >
        <span style={{ width: 14, textAlign: 'center', flexShrink: 0 }}>◼</span>
        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>Object</span>
        <span style={{ fontSize: 10, color: '#484f58' }}>{doc.object.outline.type}</span>
      </div>

      {/* Faces */}
      {(['front', 'back'] as const).map(face => {
        const features = doc.faces[face]?.features ?? []
        const isActive = tab.activeFace === face
        return (
          <div key={face}>
            <div
              onClick={() => setActiveFace(face)}
              style={{
                padding: '7px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, minHeight: 30,
                color: isActive ? '#58a6ff' : '#8b949e', fontWeight: isActive ? 600 : 400,
                background: isActive ? 'rgba(88,166,255,0.06)' : 'transparent',
              }}
            >
              <span style={{ fontSize: 9 }}>{isActive ? '▼' : '▶'}</span>
              {face === 'front' ? 'Front' : 'Back'}
              <span style={{ fontSize: 10, color: '#484f58' }}>({features.length})</span>
            </div>
            {applicationOrder(features).slice().reverse().map((f, rowIdx) => {
              // Top row = applied last = wins overlaps (layer-panel order)
              const step = features.length - rowIdx
              const isSel = tab.selectedFeatureIds.includes(f.id)
              const hidden = f.visible === false
              return (
                <div
                  key={f.id}
                  title={`Capa ${step}/${features.length} — se aplica en ese orden; la de arriba gana los solapamientos`}
                  onClick={e => {
                    setActiveFace(face)
                    // Shift+click toggles membership; plain click replaces.
                    if (e.shiftKey) toggleSelect(f.id)
                    else select(f.id)
                  }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6, padding: '6px 8px 6px 14px', minHeight: 28,
                    cursor: 'pointer',
                    background: isSel ? 'rgba(88,166,255,0.15)' : 'transparent',
                    borderLeft: isSel ? '2px solid #58a6ff' : '2px solid transparent',
                    color: hidden ? '#484f58' : '#c9d1d9',
                  }}
                >
                  <span style={{ width: 12, textAlign: 'right', fontSize: 9, color: '#484f58', flexShrink: 0 }}>{step}</span>
                  <span style={{ width: 14, textAlign: 'center', color: '#8b949e', flexShrink: 0 }}>{TYPE_ICONS[f.type] ?? '?'}</span>
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {f.name ?? f.id}
                  </span>
                  <span style={{
                    width: 8, height: 8, borderRadius: 2, flexShrink: 0,
                    background: materialColor(f.material), border: '1px solid #30363d',
                  }} />
                  <button
                    title="Subir capa (se aplica después — gana solapamientos)"
                    disabled={rowIdx === 0}
                    onClick={e => { e.stopPropagation(); moveFeature(face, f.id, +1) }}
                    style={{ background: 'transparent', border: 'none', cursor: rowIdx === 0 ? 'default' : 'pointer', fontSize: 9, padding: 0, color: rowIdx === 0 ? '#30363d' : '#8b949e', flexShrink: 0 }}
                  >▲</button>
                  <button
                    title="Bajar capa (se aplica antes)"
                    disabled={rowIdx === features.length - 1}
                    onClick={e => { e.stopPropagation(); moveFeature(face, f.id, -1) }}
                    style={{ background: 'transparent', border: 'none', cursor: rowIdx === features.length - 1 ? 'default' : 'pointer', fontSize: 9, padding: 0, color: rowIdx === features.length - 1 ? '#30363d' : '#8b949e', flexShrink: 0 }}
                  >▼</button>
                  <button
                    title={hidden ? 'Show' : 'Hide'}
                    onClick={e => { e.stopPropagation(); toggleVisible(face, f.id) }}
                    style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: 11, padding: 0, opacity: hidden ? 0.4 : 1, flexShrink: 0 }}
                  >👁</button>
                  <button
                    title="Delete"
                    onClick={e => { e.stopPropagation(); deleteFeature(face, f.id) }}
                    style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: 11, padding: 0, flexShrink: 0 }}
                  >🗑</button>
                </div>
              )
            })}
            {features.length === 0 && (
              <div style={{ padding: '2px 22px', color: '#484f58', fontSize: 11 }}>empty</div>
            )}
          </div>
        )
      })}
    </div>
  )
}
