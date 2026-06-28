import React from 'react'
import { useStudio } from '../state/studioStore'

export default function BottomPanel() {
  const { state } = useStudio()
  const report = state.manufacturingReport
  const errors = state.errors

  // Show file loading errors
  if (errors.length > 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, width: '100%' }}>
        <div style={{ fontSize: 12, color: '#f85149' }}>
          Errors loading files:
        </div>
        {errors.map((err, i) => (
          <div key={i} style={{ fontSize: 11, color: '#f85149' }}>• {err}</div>
        ))}
      </div>
    )
  }

  if (!report) {
    return (
      <div style={{ fontSize: 12, color: '#484f58', fontStyle: 'italic' }}>
        Load a manufacturing report to see analysis
      </div>
    )
  }

  const scoreColor = report.score >= 80 ? '#3fb950' : report.score >= 60 ? '#d29922' : '#f85149'
  const statusColor = report.is_manufacturable ? '#3fb950' : '#f85149'

  return (
    <div style={{ display: 'flex', gap: 24, width: '100%', alignItems: 'flex-start' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 100 }}>
        <span style={{ fontSize: 32, fontWeight: 700, color: scoreColor }}>{report.score}</span>
        <div>
          <div style={{ fontSize: 11, color: scoreColor }}>{report.score_label}</div>
          <div style={{ fontSize: 11, color: statusColor }}>
            {report.is_manufacturable ? 'Manufacturable' : 'Not manufacturable'}
          </div>
        </div>
      </div>
      <div style={{ flex: 1 }}>
        {report.warning_count > 0 && (
          <div style={{ marginBottom: 4 }}>
            <span style={{ fontSize: 11, color: '#d29922' }}>
              {report.warning_count} warning{report.warning_count > 1 ? 's' : ''}
            </span>
            {report.issues.filter(i => i.severity === 'warning').slice(0, 3).map((w, i) => (
              <div key={i} style={{ fontSize: 11, color: '#8b949e', marginLeft: 8 }}>• {w.message}</div>
            ))}
          </div>
        )}
        {report.suggestions?.length > 0 && (
          <div style={{ fontSize: 11, color: '#58a6ff' }}>
            {report.suggestions.slice(0, 2).map((s, i) => (
              <div key={i}>→ {s}</div>
            ))}
          </div>
        )}
      </div>
      <div style={{ display: 'flex', gap: 12, fontSize: 11, color: '#8b949e' }}>
        <span>{report.profile?.printer_name ?? 'FDM'}</span>
        <span>{report.profile?.material ?? 'PLA'}</span>
        <span>{report.profile?.nozzle ? `${report.profile.nozzle}mm` : ''}</span>
      </div>
    </div>
  )
}
