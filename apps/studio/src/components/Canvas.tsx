import React, { useState } from 'react'
import { useStudio } from '../state/studioStore'

export default function Canvas() {
  const { state } = useStudio()
  const [showFront, setShowFront] = useState(true)
  const [zoom, setZoom] = useState(1)

  const svgContent = showFront ? state.frontSvg : state.backSvg
  const hasBoth = state.frontSvg && state.backSvg

  return (
    <div style={{ textAlign: 'center', width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Controls */}
      <div style={{ padding: '8px 0', display: 'flex', gap: 8, justifyContent: 'center' }}>
        {hasBoth && (
          <>
            <button
              onClick={() => setShowFront(true)}
              style={{
                background: showFront ? '#1f6feb' : '#21262d',
                color: showFront ? '#fff' : '#8b949e',
                border: '1px solid #30363d', padding: '2px 10px', borderRadius: 4,
                cursor: 'pointer', fontSize: 11,
              }}
            >
              Front
            </button>
            <button
              onClick={() => setShowFront(false)}
              style={{
                background: !showFront ? '#1f6feb' : '#21262d',
                color: !showFront ? '#fff' : '#8b949e',
                border: '1px solid #30363d', padding: '2px 10px', borderRadius: 4,
                cursor: 'pointer', fontSize: 11,
              }}
            >
              Back
            </button>
          </>
        )}
        <button
          onClick={() => setZoom(z => Math.max(0.25, z - 0.25))}
          style={{
            background: '#21262d', color: '#8b949e', border: '1px solid #30363d',
            padding: '2px 8px', borderRadius: 4, cursor: 'pointer', fontSize: 11,
          }}
        >
          −
        </button>
        <span style={{ fontSize: 11, color: '#8b949e', alignSelf: 'center' }}>{Math.round(zoom * 100)}%</span>
        <button
          onClick={() => setZoom(z => Math.min(3, z + 0.25))}
          style={{
            background: '#21262d', color: '#8b949e', border: '1px solid #30363d',
            padding: '2px 8px', borderRadius: 4, cursor: 'pointer', fontSize: 11,
          }}
        >
          +
        </button>
        {zoom !== 1 && (
          <button
            onClick={() => setZoom(1)}
            style={{
              background: '#21262d', color: '#8b949e', border: '1px solid #30363d',
              padding: '2px 8px', borderRadius: 4, cursor: 'pointer', fontSize: 11,
            }}
          >
            Reset
          </button>
        )}
      </div>

      {/* Preview area */}
      <div style={{
        flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
        overflow: 'auto', padding: 16,
      }}>
        {svgContent ? (
          <div
            style={{
              transform: `scale(${zoom})`,
              transformOrigin: 'center center',
              transition: 'transform 0.15s',
            }}
            dangerouslySetInnerHTML={{ __html: svgContent }}
          />
        ) : (
          <div style={{ color: '#484f58', fontSize: 13, textAlign: 'center' }}>
            <div style={{ fontSize: 28, marginBottom: 8 }}>🃏</div>
            <div>No preview loaded</div>
            <div style={{ fontSize: 11, marginTop: 4 }}>Load a .svg file to preview</div>
          </div>
        )}
      </div>
    </div>
  )
}
