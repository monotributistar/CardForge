import React from 'react'
import { useStudio } from '../state/studioStore'
import type { Feature } from '../types/cardforge'

const PANEL_STYLE: Record<string, React.CSSProperties> = {
  section: { marginBottom: 16 },
  title: { fontSize: 11, fontWeight: 600, color: '#8b949e', textTransform: 'uppercase', marginBottom: 6 },
  row: { display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '2px 0' },
  label: { color: '#8b949e' },
  value: { color: '#c9d1d9' },
  empty: { fontSize: 12, color: '#484f58', fontStyle: 'italic' },
}

function formatSize(size: any): string {
  if (typeof size === 'number') return `${size} mm`
  if (size?.width !== undefined) return `${size.width} × ${size.height} mm`
  return '—'
}

export default function RightPanel() {
  const { state, actions } = useStudio()
  const feature = actions.getSelectedFeature()
  const doc = state.document

  if (feature) {
    return (
      <div>
        <div style={PANEL_STYLE.section}>
          <div style={PANEL_STYLE.title}>Feature</div>
          <div style={PANEL_STYLE.row}>
            <span style={PANEL_STYLE.label}>ID</span>
            <span style={PANEL_STYLE.value}>{feature.id}</span>
          </div>
          <div style={PANEL_STYLE.row}>
            <span style={PANEL_STYLE.label}>Type</span>
            <span style={PANEL_STYLE.value}>{feature.type}</span>
          </div>
          {feature.material && (
            <div style={PANEL_STYLE.row}>
              <span style={PANEL_STYLE.label}>Material</span>
              <span style={PANEL_STYLE.value}>{feature.material}</span>
            </div>
          )}
        </div>

        {feature.position && (
          <div style={PANEL_STYLE.section}>
            <div style={PANEL_STYLE.title}>Position</div>
            <div style={PANEL_STYLE.row}>
              <span style={PANEL_STYLE.label}>X</span>
              <span style={PANEL_STYLE.value}>{feature.position.x} mm</span>
            </div>
            <div style={PANEL_STYLE.row}>
              <span style={PANEL_STYLE.label}>Y</span>
              <span style={PANEL_STYLE.value}>{feature.position.y} mm</span>
            </div>
          </div>
        )}

        {feature.size && (
          <div style={PANEL_STYLE.section}>
            <div style={PANEL_STYLE.title}>Size</div>
            <div style={PANEL_STYLE.row}>
              <span style={PANEL_STYLE.label}>Dimensions</span>
              <span style={PANEL_STYLE.value}>{formatSize(feature.size)}</span>
            </div>
          </div>
        )}

        {feature.relief && (
          <div style={PANEL_STYLE.section}>
            <div style={PANEL_STYLE.title}>Relief</div>
            <div style={PANEL_STYLE.row}>
              <span style={PANEL_STYLE.label}>Mode</span>
              <span style={PANEL_STYLE.value}>{feature.relief.mode}</span>
            </div>
            {feature.relief.height != null && (
              <div style={PANEL_STYLE.row}>
                <span style={PANEL_STYLE.label}>Height</span>
                <span style={PANEL_STYLE.value}>{feature.relief.height} mm</span>
              </div>
            )}
            {feature.relief.depth != null && (
              <div style={PANEL_STYLE.row}>
                <span style={PANEL_STYLE.label}>Depth</span>
                <span style={PANEL_STYLE.value}>{feature.relief.depth} mm</span>
              </div>
            )}
          </div>
        )}

        {feature.fontSize && (
          <div style={PANEL_STYLE.section}>
            <div style={PANEL_STYLE.title}>Text</div>
            <div style={PANEL_STYLE.row}>
              <span style={PANEL_STYLE.label}>Font Size</span>
              <span style={PANEL_STYLE.value}>{feature.fontSize} mm</span>
            </div>
            <div style={PANEL_STYLE.row}>
              <span style={PANEL_STYLE.label}>Style</span>
              <span style={PANEL_STYLE.value}>{feature.fontStyle ?? 'regular'}</span>
            </div>
          </div>
        )}

        {feature.zIndex != null && (
          <div style={PANEL_STYLE.row}>
            <span style={PANEL_STYLE.label}>zIndex</span>
            <span style={PANEL_STYLE.value}>{feature.zIndex}</span>
          </div>
        )}
      </div>
    )
  }

  // No feature selected — show document info
  return (
    <div>
      {doc ? (
        <>
          <div style={PANEL_STYLE.section}>
            <div style={PANEL_STYLE.title}>Document</div>
            <div style={PANEL_STYLE.row}>
              <span style={PANEL_STYLE.label}>Name</span>
              <span style={PANEL_STYLE.value}>{doc.document.name}</span>
            </div>
            <div style={PANEL_STYLE.row}>
              <span style={PANEL_STYLE.label}>ID</span>
              <span style={PANEL_STYLE.value}>{doc.document.id}</span>
            </div>
          </div>
          {doc.objects.map(obj => (
            <div key={obj.id} style={PANEL_STYLE.section}>
              <div style={PANEL_STYLE.title}>Object: {obj.type}</div>
              <div style={PANEL_STYLE.row}>
                <span style={PANEL_STYLE.label}>Width</span>
                <span style={PANEL_STYLE.value}>{obj.width} mm</span>
              </div>
              <div style={PANEL_STYLE.row}>
                <span style={PANEL_STYLE.label}>Height</span>
                <span style={PANEL_STYLE.value}>{obj.height} mm</span>
              </div>
              <div style={PANEL_STYLE.row}>
                <span style={PANEL_STYLE.label}>Thickness</span>
                <span style={PANEL_STYLE.value}>{obj.thickness} mm</span>
              </div>
            </div>
          ))}
          <div style={PANEL_STYLE.section}>
            <div style={PANEL_STYLE.title}>Manufacturing</div>
            <div style={PANEL_STYLE.row}>
              <span style={PANEL_STYLE.label}>Process</span>
              <span style={PANEL_STYLE.value}>{doc.manufacturing.process.toUpperCase()}</span>
            </div>
            <div style={PANEL_STYLE.row}>
              <span style={PANEL_STYLE.label}>Material</span>
              <span style={PANEL_STYLE.value}>{doc.manufacturing.material}</span>
            </div>
            <div style={PANEL_STYLE.row}>
              <span style={PANEL_STYLE.label}>Nozzle</span>
              <span style={PANEL_STYLE.value}>{doc.manufacturing.nozzle}mm</span>
            </div>
          </div>
        </>
      ) : (
        <div style={PANEL_STYLE.empty}>Load a document to inspect</div>
      )}
    </div>
  )
}
