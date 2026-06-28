import React from 'react'

const BAR_STYLE: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex', alignItems: 'center', gap: 12,
    width: '100%', justifyContent: 'space-between',
  },
  left: { display: 'flex', alignItems: 'center', gap: 8 },
  title: { fontWeight: 700, fontSize: 14, color: '#58a6ff' },
  badge: {
    fontSize: 10, background: '#238636', color: '#fff',
    padding: '1px 6px', borderRadius: 8,
  },
  btn: {
    background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d',
    padding: '3px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 12,
  },
  btnPrimary: {
    background: '#238636', color: '#fff', border: '1px solid #2ea043',
    padding: '3px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 12,
  },
}

interface TopBarProps {
  project: string
  onBuild: () => void
}

export default function TopBar({ project, onBuild }: TopBarProps) {
  return (
    <div style={BAR_STYLE.container}>
      <div style={BAR_STYLE.left}>
        <span style={BAR_STYLE.title}>CardForge Studio</span>
        <span style={BAR_STYLE.badge}>v0.1</span>
        <span style={{ fontSize: 13, color: '#8b949e' }}>— {project}</span>
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <button style={BAR_STYLE.btn}>Open</button>
        <button style={BAR_STYLE.btnPrimary} onClick={onBuild}>Build</button>
        <button style={BAR_STYLE.btn}>Export</button>
      </div>
    </div>
  )
}
