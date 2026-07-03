// Selection handles — 4 corner scale handles + 1 rotate handle for the
// primary selected feature. Rendered inside the feature's (rotated) group
// in InteractiveCanvas; sizes are specified in screen px and converted to
// document mm so they stay a constant on-screen size under zoom.

import React from 'react'
import { PX_PER_MM, type BoundsMm } from './CanvasCoords'

const HANDLE_PX = 8   // corner squares (and rotate circle diameter)
const ROTATE_LINE_PX = 12 // connector line above the top edge

export const SelectionHandles: React.FC<{
  bounds: BoundsMm
  zoom: number
  onScaleStart: (e: React.PointerEvent) => void
  onRotateStart: (e: React.PointerEvent) => void
}> = ({ bounds: b, zoom, onScaleStart, onRotateStart }) => {
  const pxToMm = (px: number) => px / (PX_PER_MM * zoom)
  const size = pxToMm(HANDLE_PX)
  const r = size / 2
  const line = pxToMm(ROTATE_LINE_PX)
  const stroke = pxToMm(1)
  const cx = b.x + b.w / 2

  const corners: Array<{ x: number; y: number; cursor: string }> = [
    { x: b.x, y: b.y, cursor: 'nwse-resize' },
    { x: b.x + b.w, y: b.y, cursor: 'nesw-resize' },
    { x: b.x, y: b.y + b.h, cursor: 'nesw-resize' },
    { x: b.x + b.w, y: b.y + b.h, cursor: 'nwse-resize' },
  ]

  return (
    <g>
      {/* Rotate handle: 12px connector line, then a circle */}
      <line x1={cx} y1={b.y} x2={cx} y2={b.y - line} stroke="#58a6ff" strokeWidth={stroke} />
      <circle
        cx={cx} cy={b.y - line - r} r={r}
        fill="#58a6ff" stroke="#fff" strokeWidth={stroke}
        style={{ cursor: 'grab' }}
        onPointerDown={onRotateStart}
      />
      {/* Corner scale handles */}
      {corners.map((c, i) => (
        <rect
          key={i}
          x={c.x - r} y={c.y - r} width={size} height={size}
          fill="#58a6ff" stroke="#fff" strokeWidth={stroke}
          style={{ cursor: c.cursor }}
          onPointerDown={onScaleStart}
        />
      ))}
    </g>
  )
}
