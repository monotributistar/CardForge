import React from 'react'

interface CanvasProps {
  project: string
}

export default function Canvas({ project }: CanvasProps) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{
        width: 340, height: 216, background: '#161b22',
        border: '2px solid #30363d', borderRadius: 8,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: '#8b949e', fontSize: 13,
      }}>
        <div>
          <div style={{ fontSize: 24, marginBottom: 8 }}>🃏</div>
          <div>CardForge Preview</div>
          <div style={{ fontSize: 11, marginTop: 4 }}>{project}</div>
          <div style={{ fontSize: 10, marginTop: 8, color: '#58a6ff' }}>
            SVG preview loads here
          </div>
        </div>
      </div>
    </div>
  )
}
