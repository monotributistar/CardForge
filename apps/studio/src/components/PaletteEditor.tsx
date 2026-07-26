// PaletteEditor — the wizard's colour step: as many filaments as the printer
// has slots, not a fixed three.
//
// One material is the body (role 'base'); the rest are what features print
// in. Every non-body colour is rated against the body as you pick it, so an
// unreadable pairing is caught here instead of in the compile report.

import React from 'react'
import type { Material } from '../types/cardforge'
import { PALETTES, bestTextColor, filamentName, judgeContrast, type Palette } from '../studio/services/Filaments'
import { ColorPicker } from './ColorPicker'
import { CONTROL_H, FONT_SIZE, TextInput, Btn } from './ui'

/** Printer slots we let the wizard fill — matches the 3MF slot range. */
export const MAX_WIZARD_MATERIALS = 8

const ROLES: Array<[NonNullable<Material['role']>, string]> = [
  ['base', 'Body'], ['text', 'Text'], ['accent', 'Accent'], ['detail', 'Detail'],
]

/** Materials for a curated palette, with slots numbered in order. */
export function materialsFromPalette(p: Palette): Material[] {
  // Through reindex so ids are unique by construction, whatever roles a
  // palette happens to use.
  return reindex(p.entries.map(e => ({ id: '', name: e.name, color: e.color, slot: 0, role: e.role })))
}

/** Stable ids: the body is always `base`, the first text material `text`, and
 *  the rest are numbered — features reference these, so they must not collide. */
function reindex(materials: Material[]): Material[] {
  let textSeen = false
  return materials.map((m, i) => {
    let id: string
    if (m.role === 'base') {
      id = 'base'
    } else if (m.role === 'text' && !textSeen) {
      id = 'text'
      textSeen = true
    } else {
      id = `mat${i + 1}`
    }
    return { ...m, id, slot: i + 1 }
  })
}

export const PaletteEditor: React.FC<{
  materials: Material[]
  onChange: (materials: Material[]) => void
}> = ({ materials, onChange }) => {
  const base = materials.find(m => m.role === 'base') ?? materials[0]
  const baseColor = base?.color ?? null

  const update = (i: number, patch: Partial<Material>) => {
    const next = materials.map((m, j) => (j === i ? { ...m, ...patch } : m))
    // Exactly one body: promoting a row demotes whoever held it.
    if (patch.role === 'base') {
      for (let j = 0; j < next.length; j++) {
        if (j !== i && next[j].role === 'base') next[j] = { ...next[j], role: 'accent' }
      }
    }
    onChange(reindex(next))
  }

  const add = () => {
    // Default the new colour to something that reads on the body, so a fresh
    // row is useful before it is even touched.
    const suggestion = baseColor ? bestTextColor(baseColor) : { name: 'PLA Grey', color: '#8b8b8d' }
    const taken = new Set(materials.map(m => m.color.toLowerCase()))
    const pick = taken.has(suggestion.color) ? { name: 'PLA Grey', color: '#8b8b8d' } : suggestion
    onChange(reindex([...materials, { ...pick, id: 'tmp', slot: 0, role: 'accent' }]))
  }

  const remove = (i: number) => onChange(reindex(materials.filter((_, j) => j !== i)))

  // Worst pairing in the palette — surfaced once, under the list, so the step
  // has a single verdict instead of a row of scattered warnings.
  const worst = materials
    .filter(m => m.role !== 'base' && baseColor)
    .map(m => ({ m, v: judgeContrast(m.color, baseColor!) }))
    .sort((a, b) => a.v.ratio - b.v.ratio)[0]

  return (
    <div>
      {/* Curated starting points */}
      <div style={{ fontSize: 11, color: '#8b949e', marginBottom: 6 }}>
        Start from a combination, then adjust. The first colour is the card body.
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 14 }}>
        {PALETTES.map(p => {
          const active = p.entries.length === materials.length
            && p.entries.every((e, i) => e.color === materials[i]?.color.toLowerCase())
          return (
            <button
              key={p.key}
              type="button"
              title={p.entries.map(e => e.name).join(' · ')}
              onClick={() => onChange(materialsFromPalette(p))}
              className="cf-btn"
              style={{
                display: 'flex', alignItems: 'center', gap: 6, padding: '4px 8px 4px 5px',
                background: active ? 'rgba(88,166,255,0.12)' : '#0d1117',
                border: `1px solid ${active ? '#1f6feb' : '#30363d'}`,
                borderRadius: 20, cursor: 'pointer', fontSize: 11,
                color: active ? '#58a6ff' : '#c9d1d9',
              }}
            >
              <span style={{ display: 'flex' }}>
                {p.entries.map((e, i) => (
                  <span key={i} style={{
                    width: 13, height: 13, borderRadius: '50%', background: e.color,
                    border: '1px solid #30363d', marginLeft: i ? -4 : 0,
                  }} />
                ))}
              </span>
              {p.label}
            </button>
          )
        })}
      </div>

      {/* Rows */}
      {materials.map((m, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 7, minHeight: CONTROL_H }}>
          <span style={{ width: 16, fontSize: 10, color: '#484f58', flexShrink: 0, textAlign: 'right' }}
            title="Printer filament slot (AMS/CFS)">{i + 1}</span>
          <ColorPicker
            color={m.color}
            base={m.role === 'base' ? null : baseColor}
            size={CONTROL_H - 6}
            onPick={(color, name) => update(i, name ? { color, name } : { color })}
          />
          <div style={{ flex: 1, minWidth: 0 }}>
            <TextInput value={m.name} onCommit={v => update(i, { name: v })} />
          </div>
          <select
            value={m.role ?? 'detail'}
            title="Body = the card itself. The rest are what text, logos and QR print in."
            onChange={e => update(i, { role: e.target.value as Material['role'] })}
            style={{
              background: '#0d1117', color: '#c9d1d9', border: '1px solid #30363d',
              borderRadius: 4, padding: '4px 6px', fontSize: FONT_SIZE, height: CONTROL_H,
              width: 84, flexShrink: 0, cursor: 'pointer',
            }}
          >
            {ROLES.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
          </select>
          <button
            type="button"
            title={m.role === 'base' ? 'The body colour cannot be removed' : 'Remove this filament'}
            disabled={m.role === 'base' || materials.length <= 1}
            onClick={() => remove(i)}
            style={{
              background: 'transparent', border: 'none', fontSize: 12, padding: '0 2px', flexShrink: 0,
              cursor: m.role === 'base' ? 'not-allowed' : 'pointer',
              opacity: m.role === 'base' ? 0.3 : 1,
            }}
          >🗑</button>
        </div>
      ))}

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 10 }}>
        <Btn onClick={add} disabled={materials.length >= MAX_WIZARD_MATERIALS}
          style={{ padding: '5px 10px', minHeight: 28, fontSize: 12 }}>
          + Add filament
        </Btn>
        <span style={{ fontSize: 11, color: '#484f58' }}>
          {materials.length} of {MAX_WIZARD_MATERIALS} slots
          {materials.length >= MAX_WIZARD_MATERIALS ? ' — full' : ''}
        </span>
      </div>

      {worst && worst.v.level !== 'good' && (
        <div style={{
          marginTop: 12, padding: '8px 10px', borderRadius: 6, fontSize: 11, lineHeight: 1.5,
          background: worst.v.level === 'bad' ? 'rgba(248,81,73,0.08)' : 'rgba(210,153,34,0.08)',
          border: `1px solid ${worst.v.level === 'bad' ? 'rgba(248,81,73,0.4)' : 'rgba(210,153,34,0.4)'}`,
          color: worst.v.level === 'bad' ? '#f85149' : '#d29922',
        }}>
          <b>{filamentName(worst.m.color) ?? worst.m.name}</b> against the body is {worst.v.text}.{' '}
          {worst.v.level === 'bad'
            ? 'Anything flush in it will be invisible — only embossed or debossed shapes will read.'
            : 'Fine for large shapes; small text will be hard to read.'}
        </div>
      )}
    </div>
  )
}
