// WizardPreview — what you are about to create, drawn to scale.
//
// Deliberately a sketch, not a render: it reads the same wizard state the
// document is built from, so shape, size, colours, hole and pocket all move
// as you choose them. The compiled 3D view takes over once the card exists.

import React from 'react'
import type { Material, Outline } from '../types/cardforge'
import { DEFAULT_POCKET_CLEARANCE } from '../types/cardforge'
import type { WizardOptions, WizardPocket } from '../studio/document/defaults'
import { relativeLuminance } from '../studio/services/Filaments'

const BOX_W = 300
const BOX_H = 168

export const WizardPreview: React.FC<{
  outline: Outline
  materials: Material[]
  thickness: number
  hole: WizardOptions['hole']
  holeTab: boolean
  pocket: WizardPocket | null
  sampleText: boolean
  svgText: string | null
}> = ({ outline, materials, thickness, hole, holeTab, pocket, sampleText, svgText }) => {
  const W = outline.type === 'circle' ? outline.diameter : outline.width
  const H = outline.type === 'circle' ? outline.diameter : outline.height
  const base = materials.find(m => m.role === 'base') ?? materials[0]
  const ink = materials.find(m => m.role === 'text')
    ?? materials.find(m => m.id !== base?.id)
    ?? base
  const baseColor = base?.color ?? '#1a1a1a'
  const inkColor = ink?.color ?? '#ffffff'

  // Fit the card in the box with a little air around it.
  const scale = Math.min((BOX_W - 24) / W, (BOX_H - 24) / H)
  const w = W * scale
  const h = H * scale
  const ox = (BOX_W - w) / 2
  const oy = (BOX_H - h) / 2

  // The card sits on a neutral stage; a pale card needs an outline to be
  // visible against it, a dark one does not.
  const edge = relativeLuminance(baseColor) > 0.7 ? '#8b949e' : '#30363d'
  const mm = (v: number) => v * scale

  const bodyShape = () => {
    if (outline.type === 'circle') {
      return <circle cx={ox + w / 2} cy={oy + h / 2} r={w / 2} fill={baseColor} stroke={edge} strokeWidth={0.75} />
    }
    const r = outline.type === 'rounded-rect' ? mm(outline.radius) : 0
    return <rect x={ox} y={oy} width={w} height={h} rx={r} fill={baseColor} stroke={edge} strokeWidth={0.75} />
  }

  const holeGlyph = () => {
    if (hole === 'none') return null
    const void_ = { fill: '#0d1117', stroke: edge, strokeWidth: 0.6 }
    const dashed = { fill: 'none', stroke: inkColor, strokeWidth: 0.6, strokeDasharray: '3 2', opacity: 0.55 }
    if (hole === 'keyring') {
      const d = mm(5)
      const cx = ox + (holeTab ? 0 : mm(5))
      const cy = oy + h / 2
      return (
        <g>
          {holeTab && <circle cx={cx} cy={cy} r={d / 2 + mm(3)} fill={baseColor} stroke={edge} strokeWidth={0.75} />}
          <circle cx={cx} cy={cy} r={d / 2} {...void_} />
          {holeTab && <circle cx={cx} cy={cy} r={d / 2 + mm(3)} {...dashed} />}
        </g>
      )
    }
    const sw = mm(14)
    const sh = mm(5)
    return <rect x={ox + (w - sw) / 2} y={oy + mm(3)} width={sw} height={sh} rx={sh / 2} {...void_} />
  }

  const pocketGlyph = () => {
    if (!pocket) return null
    const bore = mm(pocket.diameter + DEFAULT_POCKET_CLEARANCE)
    const cx = ox + (outline.type === 'circle' || bore > w * 0.5 ? w / 2 : w * 0.72)
    const cy = oy + h / 2
    return (
      <g>
        <circle cx={cx} cy={cy} r={bore / 2} fill="rgba(0,0,0,0.45)" stroke={inkColor} strokeWidth={0.6} />
        <circle cx={cx} cy={cy} r={mm(pocket.diameter) / 2} fill="none" stroke={inkColor}
          strokeWidth={0.5} strokeDasharray="2 2" opacity={0.75} />
        <text x={cx} y={cy + bore * 0.16} fontSize={Math.max(7, bore * 0.42)} textAnchor="middle"
          style={{ userSelect: 'none' }}>{pocket.insert === 'rfid' ? '📶' : '🧲'}</text>
      </g>
    )
  }

  return (
    <div style={{
      background: '#0d1117', border: '1px solid #21262d', borderRadius: 8,
      padding: 8, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
    }}>
      <svg width="100%" viewBox={`0 0 ${BOX_W} ${BOX_H}`} style={{ display: 'block', maxWidth: BOX_W }}>
        <defs>
          <clipPath id="cf-wiz-clip">
            {outline.type === 'circle'
              ? <circle cx={ox + w / 2} cy={oy + h / 2} r={w / 2} />
              : <rect x={ox} y={oy} width={w} height={h}
                  rx={outline.type === 'rounded-rect' ? mm(outline.radius) : 0} />}
          </clipPath>
        </defs>
        {svgText
          // The artwork IS the card: its silhouette and its own colours.
          ? <g dangerouslySetInnerHTML={{ __html: svgWithBox(svgText, ox, oy, w, h) }} />
          : bodyShape()}
        <g clipPath="url(#cf-wiz-clip)">
          {sampleText && !svgText && (
            <text x={ox + Math.max(mm(6), w * 0.1)} y={oy + h / 2 + mm(2)}
              fontSize={Math.max(6, mm(6))} fontWeight={700} fill={inkColor}
              style={{ userSelect: 'none' }}>Your Name</text>
          )}
          {pocketGlyph()}
        </g>
        {holeGlyph()}
      </svg>
      <div style={{ fontSize: 10, color: '#484f58', fontVariantNumeric: 'tabular-nums' }}>
        {outline.type === 'circle' ? `Ø${W}` : `${W} × ${H}`} × {thickness} mm
        {materials.length > 1 ? ` · ${materials.length} filaments` : ' · 1 filament'}
      </div>
    </div>
  )
}

/** Re-wrap uploaded artwork into a positioned <svg> inside our preview box.
 *  The markup is the user's own file, rendered only for them — but it is
 *  still parsed and re-serialised (scripts and event handlers dropped) rather
 *  than injected verbatim. */
function svgWithBox(svgText: string, x: number, y: number, w: number, h: number): string {
  const dom = new DOMParser().parseFromString(svgText, 'image/svg+xml')
  const root = dom.querySelector('svg')
  if (!root || dom.querySelector('parsererror')) return ''
  root.querySelectorAll('script, foreignObject, style').forEach(el => el.remove())
  root.querySelectorAll('*').forEach(el => {
    for (const attr of [...el.attributes]) {
      if (attr.name.toLowerCase().startsWith('on')) el.removeAttribute(attr.name)
    }
  })
  root.setAttribute('x', String(x))
  root.setAttribute('y', String(y))
  root.setAttribute('width', String(w))
  root.setAttribute('height', String(h))
  root.setAttribute('preserveAspectRatio', 'xMidYMid meet')
  return new XMLSerializer().serializeToString(root)
}
