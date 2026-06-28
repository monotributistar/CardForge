import React from 'react'

const PANEL_STYLE: Record<string, React.CSSProperties> = {
  section: { marginBottom: 16 },
  title: { fontSize: 11, fontWeight: 600, color: '#8b949e', textTransform: 'uppercase', marginBottom: 6 },
  row: { display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '2px 0' },
  label: { color: '#8b949e' },
  value: { color: '#c9d1d9' },
}

export default function RightPanel() {
  return (
    <div>
      <div style={PANEL_STYLE.section}>
        <div style={PANEL_STYLE.title}>Inspector</div>
        <div style={{ fontSize: 12, color: '#8b949e' }}>
          Select a feature to inspect
        </div>
      </div>
      <div style={PANEL_STYLE.section}>
        <div style={PANEL_STYLE.title}>Properties</div>
        <div style={PANEL_STYLE.row}>
          <span style={PANEL_STYLE.label}>Type</span>
          <span style={PANEL_STYLE.value}>business-card</span>
        </div>
        <div style={PANEL_STYLE.row}>
          <span style={PANEL_STYLE.label}>Width</span>
          <span style={PANEL_STYLE.value}>85.0 mm</span>
        </div>
        <div style={PANEL_STYLE.row}>
          <span style={PANEL_STYLE.label}>Height</span>
          <span style={PANEL_STYLE.value}>54.0 mm</span>
        </div>
        <div style={PANEL_STYLE.row}>
          <span style={PANEL_STYLE.label}>Thickness</span>
          <span style={PANEL_STYLE.value}>1.8 mm</span>
        </div>
      </div>
      <div style={PANEL_STYLE.section}>
        <div style={PANEL_STYLE.title}>Material</div>
        <div style={PANEL_STYLE.row}>
          <span style={PANEL_STYLE.label}>Base</span>
          <span style={PANEL_STYLE.value}>PLA</span>
        </div>
      </div>
    </div>
  )
}
