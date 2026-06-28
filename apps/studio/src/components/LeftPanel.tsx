import React from 'react'
import { useStudio } from '../state/studioStore'
import type { Feature } from '../types/cardforge'

const PANEL_STYLE: Record<string, React.CSSProperties> = {
  section: { marginBottom: 12 },
  title: { fontSize: 11, fontWeight: 600, color: '#8b949e', textTransform: 'uppercase', marginBottom: 4 },
  item: { fontSize: 12, padding: '3px 8px', borderRadius: 4, cursor: 'pointer', color: '#c9d1d9' },
  itemActive: { fontSize: 12, padding: '3px 8px', borderRadius: 4, cursor: 'pointer', background: '#1f6feb33', color: '#58a6ff' },
  empty: { fontSize: 12, color: '#484f58', fontStyle: 'italic' },
}

export default function LeftPanel() {
  const { state, actions } = useStudio()
  const { document, legacyConfig, selectedFeatureId } = state

  // Try document format first, then legacy config
  const objects = document?.objects ?? []
  const faces = legacyConfig?.faces ?? {}

  if (objects.length === 0 && Object.keys(faces).length === 0) {
    return (
      <div style={{ padding: 8 }}>
        <div style={PANEL_STYLE.empty}>Load a document to see features</div>
      </div>
    )
  }

  return (
    <div>
      {objects.map(obj => (
        <div key={obj.id} style={PANEL_STYLE.section}>
          <div style={PANEL_STYLE.title}>{obj.type}</div>
          <div style={PANEL_STYLE.item}>{obj.id}</div>
          {Object.entries(obj.faces).map(([faceId, face]) => (
            <div key={faceId} style={{ marginLeft: 8 }}>
              <div style={{ fontSize: 11, color: '#8b949e', marginTop: 4 }}>{faceId}</div>
              {face.features.map((feat: Feature) => (
                <div
                  key={feat.id}
                  style={selectedFeatureId === feat.id ? PANEL_STYLE.itemActive : PANEL_STYLE.item}
                  onClick={() => actions.selectFeature(feat.id)}
                >
                  {feat.type} — {feat.id}
                </div>
              ))}
            </div>
          ))}
        </div>
      ))}

      {/* Legacy config format */}
      {objects.length === 0 && Object.entries(faces).map(([faceId, face]) => (
        <div key={faceId} style={PANEL_STYLE.section}>
          <div style={PANEL_STYLE.title}>{faceId}</div>
          {(face as any).features?.map((feat: Feature) => (
            <div
              key={feat.id}
              style={selectedFeatureId === feat.id ? PANEL_STYLE.itemActive : PANEL_STYLE.item}
              onClick={() => actions.selectFeature(feat.id)}
            >
              {feat.type} — {feat.id}
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
