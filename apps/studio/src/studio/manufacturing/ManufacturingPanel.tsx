// Manufacturing Panel — shows manufacturing report data
//
// Consumes: ManufacturingReport (from Workspace)
// Does NOT consume: Document, Canvas, Selection

import React from 'react'
import type { ManufacturingReport } from '../types'

interface ManufacturingPanelProps {
  report: ManufacturingReport | null
  errors: string[]
}

export const ManufacturingPanel: React.FC<ManufacturingPanelProps> = ({ report, errors }) => {
  if (errors.length > 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, width: '100%' }}>
        <div style={{ fontSize: 12, color: '#f85149' }}>Errors:</div>
        {errors.map((e, i) => <div key={i} style={{ fontSize: 11, color: '#f85149' }}>• {e}</div>)}
      </div>
    )
  }

  if (!report) {
    return <div style={{ fontSize: 12, color: '#484f58', fontStyle: 'italic' }}>No manufacturing report</div>
  }

  const scoreColor = report.score >= 80 ? '#3fb950' : report.score >= 60 ? '#d29922' : '#f85149'

  return (
    <div style={{ display: 'flex', gap: 24, width: '100%', alignItems: 'flex-start' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 100 }}>
        <span style={{ fontSize: 32, fontWeight: 700, color: scoreColor }}>{report.score}</span>
        <div>
          <div style={{ fontSize: 11, color: scoreColor }}>{report.score_label}</div>
          <div style={{ fontSize: 11, color: report.is_manufacturable ? '#3fb950' : '#f85149' }}>
            {report.is_manufacturable ? 'Manufacturable' : 'Not manufacturable'}
          </div>
        </div>
      </div>
      <div style={{ flex: 1 }}>
        {report.issues?.filter(i => i.severity === 'warning').slice(0, 3).map((w, i) => (
          <div key={i} style={{ fontSize: 11, color: '#8b949e' }}>• {w.message}</div>
        ))}
        {report.suggestions?.slice(0, 2).map((s, i) => (
          <div key={i} style={{ fontSize: 11, color: '#58a6ff' }}>→ {s}</div>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 12, fontSize: 11, color: '#8b949e' }}>
        <span title="Overall">{report.score >= 80 ? '✅' : report.score >= 60 ? '⚠️' : '❌'} Overall</span>
        <span title="QR">{report.issues?.some((i: any) => i.code?.includes('qr')) ? '⚠️' : '✅'} QR</span>
        <span title="Text">{report.issues?.some((i: any) => i.code?.includes('text')) ? '⚠️' : '✅'} Text</span>
        <span title="Relief">{report.issues?.some((i: any) => i.code?.includes('emboss') || i.code?.includes('deboss')) ? '⚠️' : '✅'} Relief</span>
        <span>{report.profile?.material ?? 'PLA'}</span>
      </div>
    </div>
  )
}
