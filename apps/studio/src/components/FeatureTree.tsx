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
}

const ADDABLE: Array<{ type: Feature['type']; label: string }> = [
  { type: 'text-block', label: 'Text block' },
  { type: 'text-pattern', label: 'Text pattern' },
  { type: 'pattern', label: 'Pattern' },
  { type: 'qr', label: 'QR code' },
  { type: 'icon', label: 'Icon' },
  { type: 'shape', label: 'Shape' },
]

export const FeatureTree: React.FC = () => {
  const tab = useDocumentStore(getActiveTab)
  const applyEdit = useDocumentStore(s => s.applyEdit)
  const select = useDocumentStore(s => s.select)
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
    if (tab.selectedFeatureId === id) select(null)
  }

  const toggleVisible = (face: FaceId, id: string) => {
    applyEdit(d => {
      const f = d.faces[face]?.features.find(x => x.id === id)
      if (f) f.visible = f.visible === false
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
          style={{ background: '#21262d', color: '#58a6ff', border: '1px solid #30363d', borderRadius: 4, width: 20, height: 20, cursor: 'pointer', fontSize: 13, lineHeight: '16px', padding: 0 }}
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
              style={{ padding: '5px 8px', cursor: 'pointer', borderRadius: 4, display: 'flex', gap: 8, alignItems: 'center', color: '#c9d1d9' }}
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

      {/* Faces */}
      {(['front', 'back'] as const).map(face => {
        const features = doc.faces[face]?.features ?? []
        const isActive = tab.activeFace === face
        return (
          <div key={face}>
            <div
              onClick={() => setActiveFace(face)}
              style={{
                padding: '5px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
                color: isActive ? '#58a6ff' : '#8b949e', fontWeight: isActive ? 600 : 400,
                background: isActive ? 'rgba(88,166,255,0.06)' : 'transparent',
              }}
            >
              <span style={{ fontSize: 9 }}>{isActive ? '▼' : '▶'}</span>
              {face === 'front' ? 'Front' : 'Back'}
              <span style={{ fontSize: 10, color: '#484f58' }}>({features.length})</span>
            </div>
            {features.map(f => {
              const isSel = f.id === tab.selectedFeatureId
              const hidden = f.visible === false
              return (
                <div
                  key={f.id}
                  onClick={() => { setActiveFace(face); select(f.id) }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6, padding: '3px 8px 3px 22px',
                    cursor: 'pointer',
                    background: isSel ? 'rgba(88,166,255,0.15)' : 'transparent',
                    borderLeft: isSel ? '2px solid #58a6ff' : '2px solid transparent',
                    color: hidden ? '#484f58' : '#c9d1d9',
                  }}
                >
                  <span style={{ width: 14, textAlign: 'center', color: '#8b949e', flexShrink: 0 }}>{TYPE_ICONS[f.type] ?? '?'}</span>
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {f.name ?? f.id}
                  </span>
                  <span style={{
                    width: 8, height: 8, borderRadius: 2, flexShrink: 0,
                    background: materialColor(f.material), border: '1px solid #30363d',
                  }} />
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
