import React from 'react'

export default function BottomPanel() {
  return (
    <div style={{ display: 'flex', gap: 24, width: '100%', alignItems: 'center' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 28 }}>100</span>
        <div>
          <div style={{ fontSize: 12, color: '#3fb950' }}>Excellent</div>
          <div style={{ fontSize: 11, color: '#8b949e' }}>Manufacturable</div>
        </div>
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 11, color: '#8b949e', marginBottom: 4 }}>Manufacturing Report</div>
        <div style={{ fontSize: 12, color: '#c9d1d9' }}>
          No issues found. Ready to print with FDM 0.4mm.
        </div>
      </div>
      <div style={{ display: 'flex', gap: 16, fontSize: 11, color: '#8b949e' }}>
        <span>Profile: FDM Standard</span>
        <span>Material: PLA</span>
        <span>Nozzle: 0.4mm</span>
      </div>
    </div>
  )
}
