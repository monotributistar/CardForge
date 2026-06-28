// InteractiveCanvas — renders SVG preview with selection overlay and drag-to-move
//
// The Canvas does NOT modify Geometry IR or SVG directly.
// It executes Commands that modify the Document, then recompiles.

import React, { useRef, useState, useCallback, useEffect } from 'react'
import { documentToScreen, screenToDocument, getFeatureBounds, type CanvasViewport } from './CanvasCoords'

interface InteractiveCanvasProps {
  frontSvg: string | null
  backSvg: string | null
  activeFace: 'front' | 'back'
  zoom: number
  offsetX: number
  offsetY: number
  document: any | null
  selectedFeatureId: string | null
  onToggleFace: () => void
  onZoomIn: () => void
  onZoomOut: () => void
  onResetZoom: () => void
  onSelectFeature: (featureId: string) => void
  onMoveFeature: (featureId: string, x: number, y: number) => void
}

export const InteractiveCanvas: React.FC<InteractiveCanvasProps> = ({
  frontSvg, backSvg, activeFace, zoom, offsetX, offsetY,
  document, selectedFeatureId,
  onToggleFace, onZoomIn, onZoomOut, onResetZoom,
  onSelectFeature, onMoveFeature,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const [containerSize, setContainerSize] = useState({ w: 800, h: 500 })
  const [dragging, setDragging] = useState<string | null>(null)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })

  const svgContent = activeFace === 'front' ? frontSvg : backSvg
  const hasBoth = frontSvg && backSvg
  const cardW = document?.objects?.[0]?.width ?? 85    // mm
  const cardH = document?.objects?.[0]?.height ?? 54
  const vp: CanvasViewport = { zoom, offsetX, offsetY }

  // Track container size
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const obs = new ResizeObserver(() => {
      setContainerSize({ w: el.clientWidth, h: el.clientHeight })
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  // Get features for the active face
  const features = document?.objects?.[0]?.faces?.[activeFace]?.features ?? []

  // Compute bounding boxes in screen coords
  const getScreenBounds = useCallback((feature: any) => {
    const b = getFeatureBounds(feature)
    if (!b) return null
    const tl = documentToScreen(b.x, b.y, cardW, cardH, vp, containerSize.w, containerSize.h)
    const br = documentToScreen(b.x + b.w, b.y + b.h, cardW, cardH, vp, containerSize.w, containerSize.h)
    return { x: tl.x, y: tl.y, w: br.x - tl.x, h: br.y - tl.y }
  }, [cardW, cardH, zoom, offsetX, offsetY, containerSize])

  // ── Pointer handlers ──────────────────────────────────────────────
  const handlePointerDown = useCallback((e: React.PointerEvent, featureId: string) => {
    e.stopPropagation()
    e.preventDefault()
    onSelectFeature(featureId)
    const feat = features.find((f: any) => f.id === featureId)
    const b = getScreenBounds(feat)
    if (b) {
      setDragOffset({ x: e.clientX - b.x, y: e.clientY - b.y })
      setDragging(featureId)
    }
    ;(e.target as HTMLElement).setPointerCapture?.(e.pointerId)
  }, [features, onSelectFeature, getScreenBounds])

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragging) return
    const docPos = screenToDocument(
      e.clientX - dragOffset.x, e.clientY - dragOffset.y,
      cardW, cardH, vp, containerSize.w, containerSize.h,
    )
    onMoveFeature(dragging, docPos.x, docPos.y)
  }, [dragging, dragOffset, cardW, cardH, vp, containerSize, onMoveFeature])

  const handlePointerUp = useCallback(() => {
    if (dragging) {
      setDragging(null)
    }
  }, [dragging])

  const handleCanvasClick = useCallback(() => {
    onSelectFeature('')
  }, [onSelectFeature])

  return (
    <div style={{ textAlign: 'center', width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Controls */}
      <div style={{ padding: '8px 0', display: 'flex', gap: 8, justifyContent: 'center' }}>
        {hasBoth && (
          <>
            <Btn active={activeFace === 'front'} onClick={onToggleFace}>Front</Btn>
            <Btn active={activeFace === 'back'} onClick={onToggleFace}>Back</Btn>
          </>
        )}
        <Btn onClick={onZoomOut}>−</Btn>
        <span style={{ fontSize: 11, color: '#8b949e', alignSelf: 'center' }}>{Math.round(zoom * 100)}%</span>
        <Btn onClick={onZoomIn}>+</Btn>
        {zoom !== 1 && <Btn onClick={onResetZoom}>Reset</Btn>}
      </div>

      {/* Canvas area with overlay */}
      <div
        ref={containerRef}
        style={{
          flex: 1, position: 'relative', overflow: 'hidden',
          cursor: dragging ? 'grabbing' : 'default',
        }}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onClick={handleCanvasClick}
      >
        {/* SVG layer */}
        {svgContent && (
          <div style={{
            position: 'absolute',
            left: `${(containerSize.w - cardW * 4 * zoom) / 2 + offsetX}px`,
            top: `${(containerSize.h - cardH * 4 * zoom) / 2 + offsetY}px`,
            width: `${cardW * 4}px`,
            height: `${cardH * 4}px`,
            transform: `scale(${zoom})`, transformOrigin: 'top left',
            pointerEvents: 'none',
          }} dangerouslySetInnerHTML={{ __html: svgContent }} />
        )}

        {/* Selection overlay */}
        {features.map((feat: any) => {
          const b = getScreenBounds(feat)
          if (!b) return null
          const isSel = feat.id === selectedFeatureId
          return (
            <div
              key={feat.id}
              onPointerDown={(e) => handlePointerDown(e, feat.id)}
              style={{
                position: 'absolute', left: b.x, top: b.y, width: b.w, height: b.h,
                border: isSel ? '2px solid #58a6ff' : '1px solid transparent',
                background: isSel ? 'rgba(88,166,255,0.08)' : 'transparent',
                cursor: isSel ? 'grab' : 'pointer',
                borderRadius: 2,
                transition: isSel ? 'none' : 'border-color 0.15s',
              }}
              title={`${feat.type}: ${feat.id}`}
            />
          )
        })}

        {/* Empty state */}
        {!svgContent && (
          <div style={{
            position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#484f58', fontSize: 13,
          }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>🃏</div>
              <div>No preview loaded</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

const Btn: React.FC<{ active?: boolean; onClick: () => void; children: React.ReactNode }> =
  ({ active, onClick, children }) => (
    <button onClick={onClick} style={{
      background: active ? '#1f6feb' : '#21262d', color: active ? '#fff' : '#8b949e',
      border: '1px solid #30363d', padding: '2px 10px', borderRadius: 4, cursor: 'pointer', fontSize: 11,
    }}>{children}</button>
  )
