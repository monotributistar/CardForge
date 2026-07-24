// InteractiveCanvas — SEMANTIC 2D top-down editing view. Not a preview.
//
// Renders directly from the document (bounding boxes + type glyphs).
// The real geometry only exists in the Core's compiled 3MF (CompiledViewer).
// Edits (drag-to-move) are routed through DocumentStore.applyEdit.

import React, { useRef, useState, useCallback, useEffect } from 'react'
import type { Feature, Outline, Fill } from '../../types/cardforge'

import { useDocumentStore, getActiveTab, findFeature } from '../../state/DocumentStore'
import { useCompileStore, mergeIssues } from '../../state/CompileStore'
import {
  PX_PER_MM, documentToScreen, screenToDocument, getFeatureBoundsMm, outlineSize,
  type CanvasViewport, type BoundsMm,
} from './CanvasCoords'
import { SelectionHandles } from './handles'

const RELIEF_BADGES: Record<string, string> = {
  'emboss': '▲', 'deboss': '▼', 'flush': '▬', 'cut': '✂', 'deboss-backed': '▣',
}

// Drag gestures. `moved` gates the undo snapshot: only the first applyEdit
// of a gesture snapshots, so undo restores the pre-drag state in one step.
type DragState =
  | { mode: 'move'; start: { x: number; y: number }; items: Array<{ id: string; x: number; y: number }>; primary: string; collapseTo: string | null; moved: boolean }
  | { mode: 'scale'; featureId: string; center: { x: number; y: number }; startDiag: number; startScale: number; moved: boolean }
  | { mode: 'rotate'; featureId: string; center: { x: number; y: number }; moved: boolean }

export const InteractiveCanvas: React.FC = () => {
  const tab = useDocumentStore(getActiveTab)
  const applyEdit = useDocumentStore(s => s.applyEdit)
  const select = useDocumentStore(s => s.select)
  const selectObject = useDocumentStore(s => s.selectObject)
  const toggleSelect = useDocumentStore(s => s.toggleSelect)
  const setActiveFace = useDocumentStore(s => s.setActiveFace)
  const constraints = useCompileStore(s => s.constraints)
  const manufacturing = useCompileStore(s => s.manufacturing)
  // Merge geometry constraints + manufacturing issues so per-feature badges
  // surface both streams.
  const issuesMerged = mergeIssues({ constraints, manufacturing })

  const containerRef = useRef<HTMLDivElement>(null)
  const [containerSize, setContainerSize] = useState({ w: 800, h: 500 })
  const [viewport, setViewport] = useState<CanvasViewport>({ zoom: 1, offsetX: 0, offsetY: 0 })

  // Drag state kept in refs so pointer handlers never see stale values.
  const dragRef = useRef<DragState | null>(null)
  const panRef = useRef<{ startX: number; startY: number; baseX: number; baseY: number } | null>(null)
  const [, forceRender] = useState(0)
  // Alignment guides shown while dragging (document-mm coordinates)
  const [guides, setGuides] = useState<{ v: number[]; h: number[] }>({ v: [], h: [] })

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const obs = new ResizeObserver(() => setContainerSize({ w: el.clientWidth, h: el.clientHeight }))
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  const doc = tab?.doc ?? null
  const activeFace = tab?.activeFace ?? 'front'
  const outline = doc?.object.outline
  const size = outline ? outlineSize(outline) : { width: 85, height: 54 }
  const cardW = size.width
  const cardH = size.height
  const features: Feature[] = doc?.faces[activeFace]?.features ?? []
  const selectedIds = tab?.selectedFeatureIds ?? []
  const primaryId = tab?.selectedFeatureId ?? null
  const objectSelected = tab?.objectSelected ?? false

  const materialColor = useCallback((id: string): string =>
    doc?.materials.find(m => m.id === id)?.color ?? '#8b949e', [doc])

  const clientToDoc = useCallback((clientX: number, clientY: number, clamp = true) => {
    const el = containerRef.current
    const rect = el?.getBoundingClientRect() ?? { left: 0, top: 0 }
    return screenToDocument(
      clientX - rect.left, clientY - rect.top,
      cardW, cardH, viewport, containerSize.w, containerSize.h, clamp,
    )
  }, [cardW, cardH, viewport, containerSize])

  // ── Pointer handlers ──────────────────────────────────────────────

  const handleFeaturePointerDown = useCallback((e: React.PointerEvent, feature: Feature) => {
    e.stopPropagation()
    e.preventDefault()
    if (e.shiftKey) {
      // Shift+click toggles membership; no drag starts.
      toggleSelect(feature.id)
      return
    }
    // Plain click: replace selection — unless the feature is already part of
    // a multi-selection, in which case keep the group so the drag moves it all
    // (a click without movement collapses to this feature on pointer-up).
    const alreadySelected = selectedIds.includes(feature.id)
    const ids = alreadySelected ? selectedIds : [feature.id]
    if (!alreadySelected) select(feature.id)
    const pos = clientToDoc(e.clientX, e.clientY)
    const items: Array<{ id: string; x: number; y: number }> = []
    for (const id of ids) {
      const found = doc ? findFeature(doc, id) : null
      if (found) items.push({ id, x: found.feature.transform.x, y: found.feature.transform.y })
    }
    dragRef.current = {
      mode: 'move',
      start: pos,
      items,
      primary: feature.id,
      collapseTo: alreadySelected && ids.length > 1 ? feature.id : null,
      moved: false,
    }
    ;(e.currentTarget as Element).setPointerCapture?.(e.pointerId)
  }, [select, toggleSelect, selectedIds, doc, clientToDoc])

  const handleScaleStart = useCallback((e: React.PointerEvent, feature: Feature, b: BoundsMm) => {
    e.stopPropagation()
    e.preventDefault()
    const center = { x: b.x + b.w / 2, y: b.y + b.h / 2 }
    const pos = clientToDoc(e.clientX, e.clientY, false)
    const startDiag = Math.hypot(pos.x - center.x, pos.y - center.y)
    if (startDiag < 1e-6) return
    dragRef.current = {
      mode: 'scale',
      featureId: feature.id,
      center,
      startDiag,
      startScale: feature.transform.scale ?? 1,
      moved: false,
    }
    ;(e.currentTarget as Element).setPointerCapture?.(e.pointerId)
  }, [clientToDoc])

  const handleRotateStart = useCallback((e: React.PointerEvent, feature: Feature, b: BoundsMm) => {
    e.stopPropagation()
    e.preventDefault()
    dragRef.current = {
      mode: 'rotate',
      featureId: feature.id,
      center: { x: b.x + b.w / 2, y: b.y + b.h / 2 },
      moved: false,
    }
    ;(e.currentTarget as Element).setPointerCapture?.(e.pointerId)
  }, [])

  const handleBackgroundPointerDown = useCallback((e: React.PointerEvent) => {
    select(null)
    panRef.current = { startX: e.clientX, startY: e.clientY, baseX: viewport.offsetX, baseY: viewport.offsetY }
    ;(e.currentTarget as Element).setPointerCapture?.(e.pointerId)
  }, [select, viewport])

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    const drag = dragRef.current
    if (drag) {
      // Snapshot only once per drag gesture so undo restores the start state.
      if (drag.mode === 'move') {
        const pos = clientToDoc(e.clientX, e.clientY)
        let dx = pos.x - drag.start.x
        let dy = pos.y - drag.start.y
        // ── Snap to card center / other features' edges & centers ──────
        // (hold Alt to disable). Threshold ≈ 6 screen px in mm.
        const activeGuides: { v: number[]; h: number[] } = { v: [], h: [] }
        if (!e.altKey && doc) {
          const prim = drag.items.find(i => i.id === drag.primary) ?? drag.items[0]
          const found = findFeature(doc, prim.id)
          if (found) {
            const pb = getFeatureBoundsMm(found.feature, cardW, cardH)
            const draggedIds = new Set(drag.items.map(i => i.id))
            const xTargets: number[] = [cardW / 2]
            const yTargets: number[] = [cardH / 2]
            for (const other of features) {
              if (draggedIds.has(other.id) || other.visible === false) continue
              const ob = getFeatureBoundsMm(other, cardW, cardH)
              xTargets.push(ob.x, ob.x + ob.w / 2, ob.x + ob.w)
              yTargets.push(ob.y, ob.y + ob.h / 2, ob.y + ob.h)
            }
            const thr = 6 / (PX_PER_MM * viewport.zoom)
            const tentX = prim.x + dx
            const tentY = prim.y + dy
            const xLines = [tentX, tentX + pb.w / 2, tentX + pb.w]
            const yLines = [tentY, tentY + pb.h / 2, tentY + pb.h]
            let bestX: { d: number; at: number } | null = null
            for (const line of xLines) for (const t of xTargets) {
              const d = t - line
              if (Math.abs(d) <= thr && (!bestX || Math.abs(d) < Math.abs(bestX.d))) bestX = { d, at: t }
            }
            let bestY: { d: number; at: number } | null = null
            for (const line of yLines) for (const t of yTargets) {
              const d = t - line
              if (Math.abs(d) <= thr && (!bestY || Math.abs(d) < Math.abs(bestY.d))) bestY = { d, at: t }
            }
            if (bestX) { dx += bestX.d; activeGuides.v.push(bestX.at) }
            if (bestY) { dy += bestY.d; activeGuides.h.push(bestY.at) }
          }
        }
        setGuides(activeGuides)
        applyEdit(d => {
          for (const item of drag.items) {
            for (const face of ['front', 'back'] as const) {
              const f = d.faces[face]?.features.find(f => f.id === item.id)
              if (f) {
                f.transform.x = Math.round((item.x + dx) * 100) / 100
                f.transform.y = Math.round((item.y + dy) * 100) / 100
              }
            }
          }
        }, { snapshot: !drag.moved })
        drag.moved = true
        return
      }
      if (drag.mode === 'scale') {
        const pos = clientToDoc(e.clientX, e.clientY, false)
        const diag = Math.hypot(pos.x - drag.center.x, pos.y - drag.center.y)
        const scale = Math.max(0.1, Math.round(drag.startScale * (diag / drag.startDiag) * 100) / 100)
        applyEdit(d => {
          for (const face of ['front', 'back'] as const) {
            const f = d.faces[face]?.features.find(f => f.id === drag.featureId)
            if (f) f.transform.scale = scale
          }
        }, { snapshot: !drag.moved })
        drag.moved = true
        return
      }
      // rotate
      const pos = clientToDoc(e.clientX, e.clientY, false)
      // 0° = handle straight up from the bbox center; clockwise positive.
      let angle = Math.atan2(pos.x - drag.center.x, -(pos.y - drag.center.y)) * 180 / Math.PI
      if (e.shiftKey) angle = Math.round(angle / 5) * 5
      angle = Math.round(angle)
      applyEdit(d => {
        for (const face of ['front', 'back'] as const) {
          const f = d.faces[face]?.features.find(f => f.id === drag.featureId)
          if (f) f.transform.rotation = angle
        }
      }, { snapshot: !drag.moved })
      drag.moved = true
      return
    }
    const pan = panRef.current
    if (pan) {
      setViewport(v => ({ ...v, offsetX: pan.baseX + (e.clientX - pan.startX), offsetY: pan.baseY + (e.clientY - pan.startY) }))
    }
  }, [clientToDoc, applyEdit, doc, features, cardW, cardH, viewport.zoom])

  const handlePointerUp = useCallback(() => {
    const drag = dragRef.current
    // Click (no movement) on a member of a multi-selection collapses to it.
    if (drag && drag.mode === 'move' && !drag.moved && drag.collapseTo) {
      select(drag.collapseTo)
    }
    dragRef.current = null
    panRef.current = null
    setGuides({ v: [], h: [] })
    forceRender(n => n + 1)
  }, [select])

  const handleWheel = useCallback((e: React.WheelEvent) => {
    const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1
    setViewport(v => ({ ...v, zoom: Math.max(0.25, Math.min(6, v.zoom * factor)) }))
  }, [])

  // Align every selected feature to the PRIMARY selection (last clicked)
  const alignSelection = (edge: 'left' | 'centerX' | 'right' | 'top' | 'centerY' | 'bottom') => {
    if (!doc || !primaryId || selectedIds.length < 2) return
    const primFound = findFeature(doc, primaryId)
    if (!primFound) return
    const pb = getFeatureBoundsMm(primFound.feature, cardW, cardH)
    applyEdit(d => {
      for (const id of selectedIds) {
        if (id === primaryId) continue
        const found = findFeature(d, id)
        if (!found) continue
        const fb = getFeatureBoundsMm(found.feature, cardW, cardH)
        const t = found.feature.transform
        if (edge === 'left') t.x = pb.x
        else if (edge === 'right') t.x = pb.x + pb.w - fb.w
        else if (edge === 'centerX') t.x = pb.x + pb.w / 2 - fb.w / 2
        else if (edge === 'top') t.y = pb.y
        else if (edge === 'bottom') t.y = pb.y + pb.h - fb.h
        else t.y = pb.y + pb.h / 2 - fb.h / 2
        t.x = Math.round(t.x * 100) / 100
        t.y = Math.round(t.y * 100) / 100
      }
    })
  }

  const zoomBy = (factor: number) =>
    setViewport(v => ({ ...v, zoom: Math.max(0.25, Math.min(6, v.zoom * factor)) }))
  const resetView = () => setViewport({ zoom: 1, offsetX: 0, offsetY: 0 })

  if (!doc) {
    return (
      <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#484f58', fontSize: 13 }}>
        No document open
      </div>
    )
  }

  // ── SVG placement (same centering math as CanvasCoords) ──────────
  const origin = documentToScreen(0, 0, cardW, cardH, viewport, containerSize.w, containerSize.h)
  const svgW = cardW * PX_PER_MM * viewport.zoom
  const svgH = cardH * PX_PER_MM * viewport.zoom

  // Merged issue lookup per feature (geometry + manufacturing)
  const featureIssues = (id: string) => issuesMerged.filter(c => c.featureId === id)

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      {/* Controls */}
      <div style={{ padding: '6px 8px', display: 'flex', gap: 6, justifyContent: 'center', alignItems: 'center', borderBottom: '1px solid #21262d', flexShrink: 0 }}>
        <Btn active={activeFace === 'front'} onClick={() => setActiveFace('front')}>Front</Btn>
        <Btn active={activeFace === 'back'} onClick={() => setActiveFace('back')}>Back</Btn>
        <span style={{ width: 12 }} />
        <Btn onClick={() => zoomBy(1 / 1.25)}>−</Btn>
        <span style={{ fontSize: 11, color: '#8b949e', minWidth: 38, textAlign: 'center' }}>{Math.round(viewport.zoom * 100)}%</span>
        <Btn onClick={() => zoomBy(1.25)}>+</Btn>
        <Btn onClick={resetView}>Reset</Btn>
        {selectedIds.length >= 2 && (
          <>
            <span style={{ width: 1, height: 16, background: '#30363d', margin: '0 4px' }} />
            <span style={{ fontSize: 10, color: '#484f58' }}>Align</span>
            <Btn title="Alinear izquierdas (al primario)" onClick={() => alignSelection('left')}>⇤</Btn>
            <Btn title="Centrar en X (al primario)" onClick={() => alignSelection('centerX')}>⇹</Btn>
            <Btn title="Alinear derechas (al primario)" onClick={() => alignSelection('right')}>⇥</Btn>
            <Btn title="Alinear superiores (al primario)" onClick={() => alignSelection('top')}>⤒</Btn>
            <Btn title="Centrar en Y (al primario)" onClick={() => alignSelection('centerY')}>⇕</Btn>
            <Btn title="Alinear inferiores (al primario)" onClick={() => alignSelection('bottom')}>⤓</Btn>
          </>
        )}
      </div>

      {/* Canvas area */}
      <div
        ref={containerRef}
        style={{ flex: 1, position: 'relative', overflow: 'hidden', cursor: dragRef.current ? 'grabbing' : 'default', background: '#0d1117' }}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerDown={handleBackgroundPointerDown}
        onWheel={handleWheel}
      >
        <svg
          width={svgW}
          height={svgH}
          viewBox={`0 0 ${cardW} ${cardH}`}
          style={{ position: 'absolute', left: origin.x, top: origin.y, overflow: 'visible' }}
        >
          <defs>
            {features.filter(f => f.type === 'pattern').map(f => (
              <pattern key={f.id} id={`hatch-${f.id}`} width="2" height="2" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <line x1="0" y1="0" x2="0" y2="2" stroke={materialColor(f.material)} strokeWidth="0.5" opacity="0.3" />
              </pattern>
            ))}
            <LatticeHintPattern fill={doc.object.fill} />
          </defs>

          {/* Object outline (click selects the base object) */}
          <g onPointerDown={e => { e.stopPropagation(); selectObject() }} style={{ cursor: 'pointer' }}>
            <ObjectOutline outline={doc.object.outline} fill={doc.object.fill} selected={objectSelected} />
          </g>
          {/* Safe margin (1mm inset, dashed) */}
          <rect
            x={1} y={1} width={cardW - 2} height={cardH - 2}
            rx={doc.object.outline.type === 'rounded-rect' ? Math.max(0, doc.object.outline.radius - 1) : 0}
            fill="none" stroke="#30363d" strokeWidth={0.2} strokeDasharray="1.5 1.5"
            pointerEvents="none"
          />

          {/* Alignment guides while dragging */}
          {guides.v.map(x => (
            <line key={`gv-${x}`} x1={x} y1={-2} x2={x} y2={cardH + 2}
              stroke="#e3b341" strokeWidth={0.25} strokeDasharray="1 0.8" pointerEvents="none" />
          ))}
          {guides.h.map(y => (
            <line key={`gh-${y}`} x1={-2} y1={y} x2={cardW + 2} y2={y}
              stroke="#e3b341" strokeWidth={0.25} strokeDasharray="1 0.8" pointerEvents="none" />
          ))}

          {/* Features */}
          {features.filter(f => f.visible !== false).map(f => {
            const b = getFeatureBoundsMm(f, cardW, cardH)
            const isSel = selectedIds.includes(f.id)
            const issues = featureIssues(f.id)
            const hasError = issues.some(i => i.severity === 'error')
            const color = materialColor(f.material)
            const isCut = f.relief.mode === 'cut'
            const rot = f.transform.rotation ?? 0
            return (
              <g
                key={f.id}
                onPointerDown={e => handleFeaturePointerDown(e, f)}
                style={{ cursor: isSel ? 'grab' : 'pointer' }}
              >
                <title>{`${f.type}: ${f.name ?? f.id}`}</title>
                <g transform={rot ? `rotate(${rot} ${b.x + b.w / 2} ${b.y + b.h / 2})` : undefined}>
                  {/* Glyph */}
                  <FeatureGlyph feature={f} bounds={b} color={color} />
                  {/* Bounding box / cut outline / selection */}
                  <rect
                    x={b.x} y={b.y} width={b.w} height={b.h}
                    fill={isSel ? 'rgba(88,166,255,0.08)' : 'transparent'}
                    stroke={isCut ? '#f85149' : isSel ? '#58a6ff' : '#30363d'}
                    strokeWidth={isSel ? 2 : 1}
                    strokeDasharray={isCut ? '1.2 0.8' : undefined}
                    vectorEffect="non-scaling-stroke"
                  />
                  {/* Relief badge (corner) */}
                  <text
                    x={b.x + b.w - 0.4} y={b.y + 2} fontSize={2}
                    textAnchor="end" fill="#8b949e" style={{ userSelect: 'none' }}
                  >{RELIEF_BADGES[f.relief.mode] ?? ''}</text>
                  {/* Backing pad badge */}
                  {(f.backing?.mode === 'on' || (f.backing?.mode !== 'off' && doc.object.fill?.type === 'lattice')) && (
                    <text x={b.x + 0.4} y={b.y + 2} fontSize={2} textAnchor="start" fill="#8b949e" style={{ userSelect: 'none' }}>
                      <title>Backing pad</title>▤
                    </text>
                  )}
                  {/* Material chip (8px at 100%) */}
                  <rect x={b.x} y={b.y + b.h + 0.5} width={2} height={2} fill={color} stroke="#30363d" strokeWidth={0.1} />
                  {/* Scale / rotate handles on the primary selection */}
                  {f.id === primaryId && (
                    <SelectionHandles
                      bounds={b}
                      zoom={viewport.zoom}
                      onScaleStart={e => handleScaleStart(e, f, b)}
                      onRotateStart={e => handleRotateStart(e, f, b)}
                    />
                  )}
                </g>
                {/* Constraint badge */}
                {issues.length > 0 && (
                  <circle cx={b.x - 0.5} cy={b.y - 0.5} r={1.2} fill={hasError ? '#f85149' : '#d29922'} stroke="#0d1117" strokeWidth={0.3}>
                    <title>{issues.map(i => i.message).join('\n')}</title>
                  </circle>
                )}
              </g>
            )
          })}
        </svg>
      </div>
    </div>
  )
}

// ── Outline ──────────────────────────────────────────────────────────

/** Build an SVG path for a rounded rect with independent per-corner radii.
 *  A radius of 0 renders a square corner. */
function roundedRectPath(w: number, h: number, r: { tl: number; tr: number; br: number; bl: number }): string {
  const clamp = (v: number) => Math.max(0, Math.min(v, w / 2, h / 2))
  const tl = clamp(r.tl), tr = clamp(r.tr), br = clamp(r.br), bl = clamp(r.bl)
  return [
    `M ${tl} 0`,
    `H ${w - tr}`,
    tr > 0 ? `A ${tr} ${tr} 0 0 1 ${w} ${tr}` : `L ${w} 0`,
    `V ${h - br}`,
    br > 0 ? `A ${br} ${br} 0 0 1 ${w - br} ${h}` : `L ${w} ${h}`,
    `H ${bl}`,
    bl > 0 ? `A ${bl} ${bl} 0 0 1 0 ${h - bl}` : `L 0 ${h}`,
    `V ${tl}`,
    tl > 0 ? `A ${tl} ${tl} 0 0 1 ${tl} 0` : `L 0 0`,
    'Z',
  ].join(' ')
}

const LATTICE_HINT_ID = 'lattice-hint'

/** A faint <pattern> hinting a non-solid (lattice) base fill. */
const LatticeHintPattern: React.FC<{ fill: Fill | undefined }> = ({ fill }) => {
  if (fill?.type !== 'lattice') return null
  const s = Math.max(1, fill.spacing)
  const lw = fill.lineWidth ?? 1.2
  const stroke = '#8b949e'
  const content = fill.pattern === 'dots'
    ? <circle cx={s / 2} cy={s / 2} r={Math.max(0.3, lw / 2)} fill={stroke} />
    : fill.pattern === 'lines'
      ? <line x1={0} y1={s / 2} x2={s} y2={s / 2} stroke={stroke} strokeWidth={lw} />
      : fill.pattern === 'hex'
        ? <path d={`M0 ${s / 2} L${s / 2} 0 L${s} ${s / 2} L${s / 2} ${s} Z`} fill="none" stroke={stroke} strokeWidth={lw * 0.6} />
        : ( // grid
          <>
            <line x1={0} y1={0} x2={0} y2={s} stroke={stroke} strokeWidth={lw * 0.6} />
            <line x1={0} y1={0} x2={s} y2={0} stroke={stroke} strokeWidth={lw * 0.6} />
          </>
        )
  return (
    <pattern id={LATTICE_HINT_ID} width={s} height={s} patternUnits="userSpaceOnUse" opacity={0.15}>
      {content}
    </pattern>
  )
}

const ObjectOutline: React.FC<{ outline: Outline; fill: Fill | undefined; selected: boolean }> = ({ outline, fill, selected }) => {
  const stroke = selected ? '#58a6ff' : '#484f58'
  const strokeWidth = selected ? 0.6 : 0.3
  const common = { fill: '#161b22', stroke, strokeWidth }
  const isLattice = fill?.type === 'lattice'
  const hint = isLattice ? `url(#${LATTICE_HINT_ID})` : undefined

  if (outline.type === 'circle') {
    const r = outline.diameter / 2
    return (
      <g>
        <circle cx={r} cy={r} r={r} {...common} />
        {isLattice && <circle cx={r} cy={r} r={r} fill={hint} stroke="none" />}
      </g>
    )
  }
  if (outline.type === 'rounded-rect') {
    const c = outline.corners
    if (c) {
      const d = roundedRectPath(outline.width, outline.height, {
        tl: c.tl ?? outline.radius, tr: c.tr ?? outline.radius,
        br: c.br ?? outline.radius, bl: c.bl ?? outline.radius,
      })
      return (
        <g>
          <path d={d} {...common} />
          {isLattice && <path d={d} fill={hint} stroke="none" />}
        </g>
      )
    }
    return (
      <g>
        <rect x={0} y={0} width={outline.width} height={outline.height} rx={outline.radius} {...common} />
        {isLattice && <rect x={0} y={0} width={outline.width} height={outline.height} rx={outline.radius} fill={hint} stroke="none" />}
      </g>
    )
  }
  if (outline.type === 'path') {
    if (outline.svgInline) {
      // Full-markup outline: show the actual artwork (its colors preview the
      // multicolor base), stretched to the document's width×height exactly
      // like the kernel scales it.
      return (
        <g>
          <rect x={0} y={0} width={outline.width} height={outline.height} fill="none" stroke={stroke} strokeWidth={strokeWidth} strokeDasharray="1 1" />
          <image
            href={`data:image/svg+xml,${encodeURIComponent(outline.svgInline)}`}
            x={0} y={0} width={outline.width} height={outline.height}
            preserveAspectRatio="none"
          />
          {isLattice && <rect x={0} y={0} width={outline.width} height={outline.height} fill={hint} stroke="none" />}
        </g>
      )
    }
    return (
      <g>
        <rect x={0} y={0} width={outline.width} height={outline.height} fill="none" stroke="#30363d" strokeWidth={0.15} strokeDasharray="1 1" />
        <path d={outline.svgPath} {...common} />
        {isLattice && <path d={outline.svgPath} fill={hint} stroke="none" />}
      </g>
    )
  }
  return (
    <g>
      <rect x={0} y={0} width={outline.width} height={outline.height} {...common} />
      {isLattice && <rect x={0} y={0} width={outline.width} height={outline.height} fill={hint} stroke="none" />}
    </g>
  )
}

// ── Inline SVG preview (icon features) ───────────────────────────────

// Parsed + sanitized inline SVGs, keyed by source text. `null` = unparseable.
const svgParseCache = new Map<string, { inner: string; viewBox: string } | null>()
// Measured artwork bounding boxes ("x y w h"), keyed by source text.
const svgBBoxCache = new Map<string, string>()

function parseSvgForPreview(svgText: string): { inner: string; viewBox: string } | null {
  const hit = svgParseCache.get(svgText)
  if (hit !== undefined) return hit
  const dom = new DOMParser().parseFromString(svgText, 'image/svg+xml')
  let out: { inner: string; viewBox: string } | null = null
  if (!dom.querySelector('parsererror')) {
    dom.querySelectorAll('script, foreignObject').forEach(el => el.remove())
    dom.querySelectorAll('*').forEach(el => {
      for (const a of [...el.attributes]) if (a.name.startsWith('on')) el.removeAttribute(a.name)
    })
    const root = dom.documentElement
    out = { inner: root.innerHTML, viewBox: root.getAttribute('viewBox') ?? '' }
  }
  svgParseCache.set(svgText, out)
  return out
}

// Draws the feature's inline SVG inside its bounds. The viewBox is the
// measured artwork bbox — matching the kernel, which scales the filled
// shapes' bbox (not the viewBox) to the feature width, anchored top-left.
const SvgGlyph: React.FC<{ svgText: string; bounds: BoundsMm; stretch: boolean }> = ({ svgText, bounds: b, stretch }) => {
  const parsed = parseSvgForPreview(svgText)
  const [measuredVb, setMeasuredVb] = useState<string | undefined>(() => svgBBoxCache.get(svgText))
  const ref = useRef<SVGSVGElement>(null)

  useEffect(() => {
    const cached = svgBBoxCache.get(svgText)
    if (cached) { setMeasuredVb(cached); return }
    const el = ref.current
    if (!el) return
    const bb = el.getBBox()
    if (bb.width > 0 && bb.height > 0) {
      const vb = `${bb.x} ${bb.y} ${bb.width} ${bb.height}`
      svgBBoxCache.set(svgText, vb)
      setMeasuredVb(vb)
    }
  }, [svgText])

  if (!parsed) return null
  return (
    <svg
      ref={ref} x={b.x} y={b.y} width={b.w} height={b.h}
      viewBox={measuredVb ?? (parsed.viewBox || undefined)}
      preserveAspectRatio={stretch ? 'none' : 'xMinYMin meet'}
      dangerouslySetInnerHTML={{ __html: parsed.inner }}
    />
  )
}

// ── Per-type glyphs ──────────────────────────────────────────────────

const FeatureGlyph: React.FC<{ feature: Feature; bounds: BoundsMm; color: string }> = ({ feature, bounds: b, color }) => {
  switch (feature.type) {
    case 'text-block': {
      const size = feature.font.size
      const anchor = feature.align === 'center' ? 'middle' : feature.align === 'right' ? 'end' : 'start'
      const tx = anchor === 'middle' ? b.x + b.w / 2 : anchor === 'end' ? b.x + b.w : b.x
      return (
        <g>
          <text
            x={tx} y={b.y + size} fontSize={size} textAnchor={anchor}
            fill={color} fontFamily={feature.font.family || 'sans-serif'}
            fontWeight={feature.font.weight ?? 400}
            fontStyle={feature.font.italic ? 'italic' : 'normal'}
            style={{ userSelect: 'none' }}
          >{feature.lines[0] ?? ''}</text>
          {feature.lines.length > 1 && (
            <text x={b.x} y={b.y + b.h - 0.5} fontSize={1.8} fill="#8b949e" style={{ userSelect: 'none' }}>
              +{feature.lines.length - 1} line{feature.lines.length > 2 ? 's' : ''}
            </text>
          )}
        </g>
      )
    }
    case 'text-pattern':
      return (
        <text x={b.x + 0.5} y={b.y + b.h * 0.75} fontSize={feature.font.size} fill={color} opacity={0.8} style={{ userSelect: 'none' }}>
          ⧉ {feature.text}
        </text>
      )
    case 'qr': {
      const cell = b.w / 5
      const cells: React.ReactNode[] = []
      for (let i = 0; i < 5; i++) {
        for (let j = 0; j < 5; j++) {
          if ((i + j) % 2 === 0) {
            cells.push(<rect key={`${i}-${j}`} x={b.x + i * cell} y={b.y + j * cell} width={cell} height={cell} fill={color} opacity={0.35} />)
          }
        }
      }
      return (
        <g>
          {cells}
          <text x={b.x + b.w / 2} y={b.y + b.h / 2 + 1.5} fontSize={4} textAnchor="middle" fill={color} fontWeight={700} style={{ userSelect: 'none' }}>QR</text>
        </g>
      )
    }
    case 'pattern':
      return <rect x={b.x} y={b.y} width={b.w} height={b.h} fill={`url(#hatch-${feature.id})`} />
    case 'icon':
      if (feature.svgInline) {
        return <SvgGlyph svgText={feature.svgInline} bounds={b} stretch={!!feature.height} />
      }
      return (
        <g>
          <text x={b.x + b.w / 2} y={b.y + b.h / 2 + 1} fontSize={Math.min(b.w, b.h) * 0.5} textAnchor="middle" style={{ userSelect: 'none' }}>🖼</text>
          <text x={b.x + b.w / 2} y={b.y + b.h - 0.5} fontSize={1.8} textAnchor="middle" fill="#8b949e" style={{ userSelect: 'none' }}>
            {feature.name ?? feature.svgAsset ?? 'icon'}
          </text>
        </g>
      )
    case 'shape':
      return <ShapeGlyph feature={feature} bounds={b} color={color} />
    case 'hole':
      return <HoleGlyph feature={feature} bounds={b} color={color} />
  }
}

// Hole: dark void (through-cut) + dashed lug outline when tab is on.
const HoleGlyph: React.FC<{ feature: Extract<Feature, { type: 'hole' }>; bounds: BoundsMm; color: string }> = ({ feature: f, bounds: b, color }) => {
  const hole = { fill: 'rgba(0,0,0,0.55)', stroke: color, strokeWidth: 0.35 }
  const m = f.tab ? (f.tabMargin ?? 3) : 0
  const tab = f.tab && (
    f.holeType === 'slot'
      ? <rect x={b.x - m} y={b.y - m} width={b.w + 2 * m} height={b.h + 2 * m} rx={b.h / 2 + m}
          fill="none" stroke={color} strokeWidth={0.3} strokeDasharray="1 0.8" opacity={0.7} />
      : <circle cx={b.x + b.w / 2} cy={b.y + b.h / 2} r={b.w / 2 + m}
          fill="none" stroke={color} strokeWidth={0.3} strokeDasharray="1 0.8" opacity={0.7} />
  )
  return (
    <g>
      {tab}
      {f.holeType === 'slot'
        ? <rect x={b.x} y={b.y} width={b.w} height={b.h} rx={b.h / 2} {...hole} />
        : <circle cx={b.x + b.w / 2} cy={b.y + b.h / 2} r={b.w / 2} {...hole} />}
    </g>
  )
}

const ShapeGlyph: React.FC<{ feature: Extract<Feature, { type: 'shape' }>; bounds: BoundsMm; color: string }> = ({ feature: f, bounds: b, color }) => {
  const stroke = { fill: 'none', stroke: color, strokeWidth: 0.35 }
  switch (f.shapeType) {
    case 'circle':
      return <circle cx={b.x + b.w / 2} cy={b.y + b.h / 2} r={b.w / 2} {...stroke} />
    case 'ring': {
      const r = b.w / 2
      const inner = Math.max(0.5, r - (f.strokeWidth ?? 1.5))
      return (
        <g>
          <circle cx={b.x + r} cy={b.y + r} r={r} {...stroke} />
          <circle cx={b.x + r} cy={b.y + r} r={inner} {...stroke} strokeDasharray="0.8 0.8" />
        </g>
      )
    }
    case 'frame': {
      const t = f.strokeWidth ?? 2
      return (
        <g>
          <rect x={b.x} y={b.y} width={b.w} height={b.h} rx={f.radius ?? 0} {...stroke} />
          <rect x={b.x + t} y={b.y + t} width={Math.max(0, b.w - 2 * t)} height={Math.max(0, b.h - 2 * t)} rx={Math.max(0, (f.radius ?? 0) - t)} {...stroke} strokeDasharray="0.8 0.8" />
        </g>
      )
    }
    case 'corner-marks': {
      const len = f.length ?? 5
      const marks = [
        `M ${b.x} ${b.y + len} L ${b.x} ${b.y} L ${b.x + len} ${b.y}`,
        `M ${b.x + b.w - len} ${b.y} L ${b.x + b.w} ${b.y} L ${b.x + b.w} ${b.y + len}`,
        `M ${b.x + b.w} ${b.y + b.h - len} L ${b.x + b.w} ${b.y + b.h} L ${b.x + b.w - len} ${b.y + b.h}`,
        `M ${b.x + len} ${b.y + b.h} L ${b.x} ${b.y + b.h} L ${b.x} ${b.y + b.h - len}`,
      ]
      return <g>{marks.map((d, i) => <path key={i} d={d} {...stroke} />)}</g>
    }
    case 'path':
      return (
        <g transform={`translate(${b.x} ${b.y})`}>
          <path d={f.svgPath ?? ''} {...stroke} />
        </g>
      )
    case 'rounded-rect':
      return <rect x={b.x} y={b.y} width={b.w} height={b.h} rx={f.radius ?? 2} {...stroke} />
    default:
      return <rect x={b.x} y={b.y} width={b.w} height={b.h} {...stroke} />
  }
}

// ── Buttons ──────────────────────────────────────────────────────────

const Btn: React.FC<{ active?: boolean; onClick: () => void; children: React.ReactNode; title?: string }> =
  ({ active, onClick, children, title }) => (
    <button onClick={onClick} title={title} style={{
      background: active ? '#1f6feb' : '#21262d', color: active ? '#fff' : '#8b949e',
      border: '1px solid #30363d', padding: '2px 10px', borderRadius: 4, cursor: 'pointer', fontSize: 11,
    }}>{children}</button>
  )
