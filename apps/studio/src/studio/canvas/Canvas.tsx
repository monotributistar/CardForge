// Canvas — renders the Scene into a visual preview
//
// Consumes: Scene (what to show), Viewport (how to view it), Workspace (SVG data)
// Does NOT consume: Document directly, Selection

import React from 'react'

interface CanvasProps {
  frontSvg: string | null
  backSvg: string | null
  activeFace: 'front' | 'back'
  zoom: number
  onToggleFace: () => void
  onZoomIn: () => void
  onZoomOut: () => void
  onResetZoom: () => void
}

export const Canvas: React.FC<CanvasProps> = ({
  frontSvg, backSvg, activeFace, zoom, onToggleFace,
  onZoomIn, onZoomOut, onResetZoom,
}) => {
  const svgContent = activeFace === 'front' ? frontSvg : backSvg
  const hasBoth = frontSvg && backSvg

  return (
    <div style={{ textAlign: 'center', width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '8px 0', display: 'flex', gap: 8, justifyContent: 'center' }}>
        {hasBoth && (
          <>
            <CanvasBtn active={activeFace === 'front'} onClick={() => onToggleFace()}>Front</CanvasBtn>
            <CanvasBtn active={activeFace === 'back'} onClick={() => onToggleFace()}>Back</CanvasBtn>
          </>
        )}
        <CanvasBtn onClick={onZoomOut}>−</CanvasBtn>
        <span style={{ fontSize: 11, color: '#8b949e', alignSelf: 'center' }}>{Math.round(zoom * 100)}%</span>
        <CanvasBtn onClick={onZoomIn}>+</CanvasBtn>
        {zoom !== 1 && <CanvasBtn onClick={onResetZoom}>Reset</CanvasBtn>}
      </div>
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'auto', padding: 16 }}>
        {svgContent ? (
          <div style={{ transform: `scale(${zoom})`, transformOrigin: 'center center', transition: 'transform 0.15s' }}
            dangerouslySetInnerHTML={{ __html: svgContent }} />
        ) : (
          <div style={{ color: '#484f58', fontSize: 13, textAlign: 'center' }}>
            <div style={{ fontSize: 28, marginBottom: 8 }}>🃏</div>
            <div>No preview loaded</div>
          </div>
        )}
      </div>
    </div>
  )
}

const CanvasBtn: React.FC<{ active?: boolean; onClick: () => void; children: React.ReactNode }> =
  ({ active, onClick, children }) => (
    <button onClick={onClick} style={{
      background: active ? '#1f6feb' : '#21262d', color: active ? '#fff' : '#8b949e',
      border: '1px solid #30363d', padding: '2px 10px', borderRadius: 4, cursor: 'pointer', fontSize: 11,
    }}>{children}</button>
  )
