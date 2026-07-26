// ColorPicker — a colour swatch that opens the filament library.
//
// Picking a filament sets the colour AND the name together, because on a
// printer those are one decision: you load a spool, not a hex value. The
// free-form hex input stays for anything not on the shelf.

import React, { useEffect, useRef, useState } from 'react'
import { FILAMENT_GROUPS, filamentName, judgeContrast, type Filament } from '../studio/services/Filaments'

const VERDICT_COLOR = { good: '#3fb950', weak: '#d29922', bad: '#f85149' } as const

const POPOVER_W = 250
const POPOVER_H = 340

/** Contrast read-out against the body colour. Null base = nothing to compare.
 *  Three densities, because the same fact has to fit three places:
 *    full  — "4.6:1 — reads clearly"
 *    ratio — "4.6:1", the verdict moves into the tooltip (lists, where the
 *            name it sits next to needs the width more)
 *    flag  — a lone ⚠, and only when there is something wrong (dense rows) */
export const ContrastBadge: React.FC<{
  color: string; base: string | null; variant?: 'full' | 'ratio' | 'flag'
}> = ({ color, base, variant = 'full' }) => {
  if (!base || base.toLowerCase() === color.toLowerCase()) return null
  const v = judgeContrast(color, base)
  if (variant === 'flag' && v.level === 'good') return null
  const title = `${v.text}. Contrast against the body colour (WCAG); under 2.5:1 `
    + 'a flush colour is invisible and only relief makes the shape readable.'
  return (
    <span
      title={title}
      style={{ fontSize: 10, color: VERDICT_COLOR[v.level], whiteSpace: 'nowrap', flexShrink: 0, cursor: 'help' }}
    >{variant === 'flag' ? '⚠' : variant === 'ratio' ? `${v.ratio.toFixed(1)}:1` : v.text}</span>
  )
}

export const ColorPicker: React.FC<{
  color: string
  /** Called with the chosen colour; `name` is set when it came from the
   *  library (so the caller can rename the material to match). `snapshot` is
   *  false for the frames of a drag through the OS colour wheel — undoable
   *  callers should coalesce those into one history entry. */
  onPick: (color: string, name?: string, snapshot?: boolean) => void
  /** Body colour to rate contrast against inside the popover. */
  base?: string | null
  size?: number
  title?: string
}> = ({ color, onPick, base, size = 18, title }) => {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  // The list is tall and the swatches sit low in a side panel as often as not,
  // so the popover opens towards whichever side has room.
  const [place, setPlace] = useState<{ up: boolean; right: boolean }>({ up: false, right: false })
  const wrapRef = useRef<HTMLDivElement>(null)
  const btnRef = useRef<HTMLButtonElement>(null)
  // The native colour input fires continuously while dragged; only the first
  // change of a gesture starts a new undo step.
  const gestureRef = useRef(false)

  const toggle = () => {
    setOpen(o => {
      if (o) return false
      const r = btnRef.current?.getBoundingClientRect()
      if (r) {
        setPlace({
          up: r.bottom + POPOVER_H > window.innerHeight && r.top > POPOVER_H,
          right: r.left + POPOVER_W > window.innerWidth,
        })
      }
      return true
    })
  }

  // Click-away / Esc close — the popover floats over the panel it belongs to.
  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') { e.stopPropagation(); setOpen(false) } }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey, true)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey, true)
    }
  }, [open])

  const q = query.trim().toLowerCase()
  const groups = FILAMENT_GROUPS
    .map(g => ({ ...g, items: g.items.filter(f => !q || f.name.toLowerCase().includes(q)) }))
    .filter(g => g.items.length > 0)

  const choose = (f: Filament) => { onPick(f.color, f.name, true); setOpen(false) }

  return (
    <div ref={wrapRef} style={{ position: 'relative', flexShrink: 0, lineHeight: 0 }}>
      <button
        ref={btnRef}
        type="button"
        title={title ?? `${filamentName(color) ?? color} — click to pick a filament`}
        onClick={toggle}
        style={{
          width: size, height: size, padding: 0, borderRadius: 3, cursor: 'pointer',
          background: color, border: `1px solid ${open ? '#58a6ff' : '#30363d'}`,
          boxShadow: open ? '0 0 0 2px rgba(88,166,255,0.35)' : undefined,
        }}
      />
      {open && (
        <div style={{
          position: 'absolute', zIndex: 300,
          ...(place.up ? { bottom: size + 6 } : { top: size + 6 }),
          ...(place.right ? { right: 0 } : { left: 0 }),
          width: POPOVER_W, maxHeight: POPOVER_H - 20, overflowY: 'auto',
          background: '#161b22', border: '1px solid #30363d', borderRadius: 8,
          boxShadow: '0 8px 24px rgba(0,0,0,0.6)', padding: 8, lineHeight: 1.4,
        }}>
          <input
            autoFocus
            value={query}
            placeholder="Search filaments…"
            onChange={e => setQuery(e.target.value)}
            style={{
              width: '100%', boxSizing: 'border-box', marginBottom: 8,
              background: '#0d1117', color: '#c9d1d9', border: '1px solid #30363d',
              borderRadius: 4, padding: '5px 7px', fontSize: 12,
            }}
          />
          {groups.map(g => (
            <div key={g.label} style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.6, color: '#8b949e', marginBottom: 4 }}>
                {g.label}
              </div>
              {g.items.map(f => {
                const selected = f.color === color.toLowerCase()
                return (
                  <div
                    key={f.name}
                    onClick={() => choose(f)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 7, padding: '4px 5px',
                      borderRadius: 4, cursor: 'pointer', fontSize: 12,
                      color: selected ? '#58a6ff' : '#c9d1d9',
                      background: selected ? 'rgba(88,166,255,0.12)' : 'transparent',
                    }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = '#21262d' }}
                    onMouseLeave={e => {
                      (e.currentTarget as HTMLElement).style.background =
                        selected ? 'rgba(88,166,255,0.12)' : 'transparent'
                    }}
                  >
                    <span style={{
                      width: 14, height: 14, borderRadius: 3, flexShrink: 0,
                      background: f.color, border: '1px solid #30363d',
                    }} />
                    <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {f.name}
                    </span>
                    <ContrastBadge color={f.color} base={base ?? null} variant="ratio" />
                  </div>
                )
              })}
            </div>
          ))}
          {groups.length === 0 && (
            <div style={{ fontSize: 11, color: '#484f58', padding: '2px 5px 8px' }}>No filament matches that.</div>
          )}
          <div style={{ borderTop: '1px solid #21262d', paddingTop: 8, display: 'flex', alignItems: 'center', gap: 7 }}>
            <input
              type="color"
              value={color}
              title="Custom colour"
              onChange={e => { onPick(e.target.value, undefined, !gestureRef.current); gestureRef.current = true }}
              onBlur={() => { gestureRef.current = false }}
              style={{ width: 26, height: 24, padding: 0, border: '1px solid #30363d', borderRadius: 4, background: 'transparent', cursor: 'pointer', flexShrink: 0 }}
            />
            <span style={{ fontSize: 11, color: '#8b949e' }}>Custom colour</span>
          </div>
        </div>
      )}
    </div>
  )
}
