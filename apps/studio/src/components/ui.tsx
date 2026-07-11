// ui — shared UI kit for the Studio: sections, labeled rows with hint
// tooltips, commit inputs, the [−][ value ][+] numeric stepper, selects and
// buttons. Sizing tokens live here so the whole app scales together.
//
// The app styles inline; this is the single place that injects a stylesheet
// (number-spinner hiding, stepper button states, hint tooltips).

import React from 'react'
import type { Material } from '../types/cardforge'

// ── Sizing tokens ────────────────────────────────────────────────────
export const CONTROL_H = 30      // control height — comfortable click target
export const FONT_SIZE = 13      // value/input font size
export const LABEL_W = 92        // Row label column width

// ── One-time stylesheet ──────────────────────────────────────────────
if (typeof document !== 'undefined' && !document.getElementById('cf-ui-style')) {
  const el = document.createElement('style')
  el.id = 'cf-ui-style'
  el.textContent = [
    // numeric stepper: hide native spinners (redundant with the +/- buttons)
    '.cf-num-stepper input[type=number]::-webkit-inner-spin-button,',
    '.cf-num-stepper input[type=number]::-webkit-outer-spin-button{-webkit-appearance:none;margin:0}',
    '.cf-num-stepper input[type=number]{-moz-appearance:textfield;appearance:textfield}',
    '.cf-num-stepper button:hover:not(:disabled){background:#30363d;color:#fff}',
    '.cf-num-stepper button:active:not(:disabled){background:#1f6feb;color:#fff}',
    '.cf-num-stepper button:disabled{opacity:.4;cursor:default}',
    // hint tooltips: dotted label, bubble above on hover
    '.cf-hint{position:relative;cursor:help;border-bottom:1px dotted #484f58}',
    '.cf-hint:hover::after{content:attr(data-hint);position:absolute;left:0;bottom:calc(100% + 6px);',
    'background:#1c2128;color:#c9d1d9;border:1px solid #30363d;border-radius:6px;padding:6px 9px;',
    'font-size:11px;line-height:1.45;width:max-content;max-width:240px;white-space:normal;',
    'z-index:1000;box-shadow:0 4px 12px rgba(0,0,0,.55);pointer-events:none}',
    // generic buttons
    '.cf-btn:hover:not(:disabled){filter:brightness(1.15)}',
    '.cf-btn:disabled{opacity:.45;cursor:default}',
  ].join('')
  document.head.appendChild(el)
}

// ── Layout primitives ────────────────────────────────────────────────

export const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div style={{ marginBottom: 16 }}>
    <div style={{
      fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.6,
      color: '#8b949e', borderBottom: '1px solid #21262d', paddingBottom: 5, marginBottom: 8,
    }}>{title}</div>
    {children}
  </div>
)

/** Labeled row. `hint` shows a tooltip bubble on hover over the label. */
export const Row: React.FC<{ label: string; hint?: string; vertical?: boolean; children: React.ReactNode }> = ({ label, hint, vertical, children }) => (
  <div style={{
    display: 'flex', flexDirection: vertical ? 'column' : 'row',
    alignItems: vertical ? 'stretch' : 'center', gap: vertical ? 4 : 8, marginBottom: 7,
    minHeight: vertical ? undefined : CONTROL_H,
  }}>
    <span
      className={hint ? 'cf-hint' : undefined}
      data-hint={hint}
      style={{ width: vertical ? 'auto' : LABEL_W, flexShrink: 0, color: '#8b949e', fontSize: 12, alignSelf: vertical ? undefined : 'center' }}
    >{label}</span>
    {children}
  </div>
)

/** Standalone ⓘ hint — for section headers or free-form spots. */
export const HelpTip: React.FC<{ text: string }> = ({ text }) => (
  <span className="cf-hint" data-hint={text} style={{ color: '#484f58', fontSize: 11, marginLeft: 5, borderBottom: 'none' }}>ⓘ</span>
)

// ── Inputs ───────────────────────────────────────────────────────────

export const inputStyle: React.CSSProperties = {
  flex: 1, minWidth: 0, width: '100%', background: '#0d1117', color: '#c9d1d9',
  border: '1px solid #30363d', borderRadius: 4, padding: '4px 8px',
  fontSize: FONT_SIZE, height: CONTROL_H, boxSizing: 'border-box',
}

export const ReadOnly: React.FC<{ value: string }> = ({ value }) => (
  <span style={{ fontSize: 11, color: '#484f58', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{value}</span>
)

/** Text input that commits on blur/Enter (avoids clobbering while typing). */
export const CommitInput: React.FC<{
  value: string
  placeholder?: string
  style?: React.CSSProperties
  onCommit: (v: string) => void
}> = ({ value, placeholder, style, onCommit }) => {
  const [local, setLocal] = React.useState(value)
  React.useEffect(() => setLocal(value), [value])
  const commit = () => { if (local !== value) onCommit(local) }
  return (
    <input
      style={style ?? inputStyle}
      value={local}
      placeholder={placeholder}
      onChange={e => setLocal(e.target.value)}
      onBlur={commit}
      onKeyDown={e => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur() }}
    />
  )
}

export const TextInput: React.FC<{ value: string; placeholder?: string; onCommit: (v: string) => void }> = (props) => (
  <CommitInput {...props} />
)

export const TextArea: React.FC<{ value: string; rows?: number; placeholder?: string; onCommit: (v: string) => void }> = ({ value, rows, placeholder, onCommit }) => {
  const [local, setLocal] = React.useState(value)
  React.useEffect(() => setLocal(value), [value])
  return (
    <textarea
      style={{ ...inputStyle, height: 'auto', resize: 'vertical', fontFamily: 'inherit' }}
      rows={rows ?? 3}
      value={local}
      placeholder={placeholder}
      onChange={e => setLocal(e.target.value)}
      onBlur={() => { if (local !== value) onCommit(local) }}
    />
  )
}

const stepBtnStyle: React.CSSProperties = {
  width: CONTROL_H, flexShrink: 0, background: '#21262d', color: '#c9d1d9',
  border: '1px solid #30363d', cursor: 'pointer', fontSize: 17, lineHeight: 1,
  padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', userSelect: 'none',
}

/** Numeric field as a [−][ value ][+] stepper. Buttons nudge by `step`
 *  (respecting min/max); the value stays editable by typing. Used everywhere
 *  a number is edited, so the whole app gets the same control. */
export const NumInput: React.FC<{ value: number; step?: number; min?: number; max?: number; placeholder?: string; onCommit: (v: number) => void }> = ({ value, step = 1, min, max, placeholder, onCommit }) => {
  const clamp = (n: number) => Math.min(max ?? Infinity, Math.max(min ?? -Infinity, n))
  // Snap to the step's decimal precision so 0.1 + 0.2 doesn't drift to 0.3000004.
  const decimals = (String(step).split('.')[1] ?? '').length
  const snap = (n: number) => Number(n.toFixed(decimals))
  const bump = (dir: 1 | -1) => onCommit(snap(clamp(value + dir * step)))
  const atMin = min != null && value <= min
  const atMax = max != null && value >= max
  return (
    <div className="cf-num-stepper" style={{ display: 'flex', flex: 1, minWidth: 0, height: CONTROL_H }}>
      <button type="button" title={`−${step}`} aria-label="decrement" disabled={atMin} onClick={() => bump(-1)}
        style={{ ...stepBtnStyle, borderRadius: '4px 0 0 4px', borderRight: 'none' }}>−</button>
      <input
        type="number"
        style={{ ...inputStyle, flex: 1, width: 'auto', height: '100%', borderRadius: 0, textAlign: 'center', fontVariantNumeric: 'tabular-nums' }}
        value={value}
        step={step}
        min={min}
        max={max}
        placeholder={placeholder}
        onChange={e => {
          const n = e.target.valueAsNumber
          if (Number.isNaN(n)) return
          if (min != null && n < min) return
          if (max != null && n > max) return
          onCommit(n)
        }}
      />
      <button type="button" title={`+${step}`} aria-label="increment" disabled={atMax} onClick={() => bump(1)}
        style={{ ...stepBtnStyle, borderRadius: '0 4px 4px 0', borderLeft: 'none' }}>+</button>
    </div>
  )
}

export const Select: React.FC<{ value: string; options: Array<[string, string]>; onCommit: (v: string) => void }> = ({ value, options, onCommit }) => (
  <select value={value} onChange={e => onCommit(e.target.value)} style={{ ...inputStyle, cursor: 'pointer' }}>
    {options.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
  </select>
)

export const MaterialSelect: React.FC<{ materials: Material[]; value: string; allowEmpty?: boolean; emptyLabel?: string; onCommit: (v: string) => void }> = ({ materials, value, allowEmpty, emptyLabel, onCommit }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1, minWidth: 0 }}>
    <span style={{
      width: 14, height: 14, borderRadius: 3, flexShrink: 0,
      background: materials.find(m => m.id === value)?.color ?? 'transparent',
      border: '1px solid #30363d',
    }} />
    <select value={value} onChange={e => onCommit(e.target.value)} style={{ ...inputStyle, cursor: 'pointer' }}>
      {allowEmpty && <option value="">{emptyLabel ?? '(none)'}</option>}
      {materials.map(m => <option key={m.id} value={m.id}>{m.name} ({m.id})</option>)}
    </select>
  </div>
)

// ── Buttons ──────────────────────────────────────────────────────────

/** Square icon button (bring-forward, duplicate, delete…). */
export const ActionBtn: React.FC<{ title: string; onClick: () => void; children: React.ReactNode }> = ({ title, onClick, children }) => (
  <button
    className="cf-btn"
    title={title}
    onClick={onClick}
    style={{
      width: CONTROL_H, height: CONTROL_H, background: '#21262d', color: '#c9d1d9',
      border: '1px solid #30363d', borderRadius: 4, cursor: 'pointer', fontSize: 13,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 0,
    }}
  >{children}</button>
)

/** General-purpose button (splash / wizard / dialogs). */
export const Btn: React.FC<{
  onClick: () => void
  primary?: boolean
  disabled?: boolean
  title?: string
  style?: React.CSSProperties
  children: React.ReactNode
}> = ({ onClick, primary, disabled, title, style, children }) => (
  <button
    className="cf-btn"
    onClick={onClick}
    disabled={disabled}
    title={title}
    style={{
      background: primary ? '#1f6feb' : '#21262d',
      color: primary ? '#fff' : '#c9d1d9',
      border: primary ? '1px solid #1f6feb' : '1px solid #30363d',
      padding: '7px 14px', borderRadius: 6, cursor: disabled ? 'default' : 'pointer',
      fontSize: FONT_SIZE, minHeight: 34,
      ...style,
    }}
  >{children}</button>
)

// ── Modal shell ──────────────────────────────────────────────────────

/** Fullscreen backdrop that centers its child. Esc / backdrop click close. */
export const Overlay: React.FC<{ onClose?: () => void; children: React.ReactNode }> = ({ onClose, children }) => {
  React.useEffect(() => {
    if (!onClose) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <div
      onMouseDown={e => { if (e.target === e.currentTarget) onClose?.() }}
      style={{
        position: 'fixed', inset: 0, zIndex: 200, background: 'rgba(1,4,9,0.65)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
      }}
    >
      {children}
    </div>
  )
}

// ── Hooks ────────────────────────────────────────────────────────────

export function useMediaQuery(query: string): boolean {
  const [match, setMatch] = React.useState<boolean>(() =>
    typeof window !== 'undefined' && window.matchMedia(query).matches)
  React.useEffect(() => {
    const mq = window.matchMedia(query)
    const onChange = () => setMatch(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [query])
  return match
}

/** Narrow-viewport breakpoint shared by the whole app. */
export const useIsNarrow = () => useMediaQuery('(max-width: 900px)')
