import React from 'react'

const PANEL_STYLE: Record<string, React.CSSProperties> = {
  section: { marginBottom: 16 },
  title: { fontSize: 11, fontWeight: 600, color: '#8b949e', textTransform: 'uppercase', marginBottom: 6 },
  item: { fontSize: 13, padding: '4px 8px', borderRadius: 4, cursor: 'pointer', color: '#c9d1d9' },
  itemActive: { fontSize: 13, padding: '4px 8px', borderRadius: 4, cursor: 'pointer', background: '#1f6feb33', color: '#58a6ff' },
}

export default function LeftPanel() {
  return (
    <div>
      <div style={PANEL_STYLE.section}>
        <div style={PANEL_STYLE.title}>Document</div>
        <div style={PANEL_STYLE.itemActive}>main-card</div>
      </div>
      <div style={PANEL_STYLE.section}>
        <div style={PANEL_STYLE.title}>Faces</div>
        <div style={PANEL_STYLE.item}>Front</div>
        <div style={PANEL_STYLE.item}>Back</div>
      </div>
      <div style={PANEL_STYLE.section}>
        <div style={PANEL_STYLE.title}>Layers</div>
        <div style={PANEL_STYLE.item}>content</div>
        <div style={PANEL_STYLE.item}>decorative</div>
      </div>
      <div style={PANEL_STYLE.section}>
        <div style={PANEL_STYLE.title}>Features</div>
        <div style={PANEL_STYLE.item}>TextBlock</div>
        <div style={PANEL_STYLE.item}>QR Code</div>
        <div style={PANEL_STYLE.item}>Pattern</div>
        <div style={PANEL_STYLE.item}>Logo</div>
      </div>
    </div>
  )
}
