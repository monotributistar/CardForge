// EngineControl — the "Motor" (compile engine) connection widget.
//
// The engine is optional: the 2D editor, validation and quick fixes run with
// no engine. This control shows the live connection state and lets the user
// point the Studio at any engine (or retry the default) at runtime. It's the
// single place the engine URL is configured — no rebuild, no env file.

import React, { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'
import {
  useEngineStore,
  refreshEngine,
  setEngineUrl,
  type EngineStatus,
} from '../state/EngineStore'

/** Calm palette — offline is steel (a feature that's off), never red. */
export const ENGINE_COLORS: Record<EngineStatus, string> = {
  online: '#1F9D63',
  offline: '#5B6673',
  checking: '#E0A32E',
  unknown: '#5B6673',
}

export function engineLabel(status: EngineStatus): string {
  switch (status) {
    case 'online': return 'Conectado'
    case 'offline': return 'Sin motor'
    case 'checking': return 'Conectando…'
    default: return 'Motor'
  }
}

export const EngineControl: React.FC = () => {
  const { url, defaultUrl, status } = useEngineStore()
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState(url)
  const btnRef = useRef<HTMLButtonElement>(null)
  const popRef = useRef<HTMLDivElement>(null)
  // Where to anchor the portalled popover (fixed, viewport coords).
  const [anchor, setAnchor] = useState<{ top: number; right: number }>({ top: 0, right: 0 })

  // Keep the field in sync when the effective URL changes elsewhere.
  useEffect(() => { setDraft(url) }, [url])

  // The menu bar clips overflow, so the popover is portalled to <body> and
  // positioned under the trigger with fixed coordinates.
  useEffect(() => {
    if (!open) return
    const place = () => {
      const r = btnRef.current?.getBoundingClientRect()
      if (r) setAnchor({ top: r.bottom + 6, right: Math.max(8, window.innerWidth - r.right) })
    }
    place()
    const onDocClick = (e: MouseEvent) => {
      const t = e.target as Node
      if (btnRef.current?.contains(t) || popRef.current?.contains(t)) return
      setOpen(false)
    }
    window.addEventListener('resize', place)
    document.addEventListener('mousedown', onDocClick)
    return () => {
      window.removeEventListener('resize', place)
      document.removeEventListener('mousedown', onDocClick)
    }
  }, [open])

  const dot = ENGINE_COLORS[status]
  const apply = () => {
    if (draft.trim() === url) void refreshEngine()
    else setEngineUrl(draft)
  }

  return (
    <div style={{ position: 'relative' }}>
      <button
        ref={btnRef}
        onClick={() => setOpen(o => !o)}
        title="Motor de compilación — opcional; el diseño 2D funciona sin él"
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          background: '#1E232A', color: '#AEB6C0', border: '1px solid #2A313A',
          padding: '6px 10px', borderRadius: 5, cursor: 'pointer', fontSize: 12, whiteSpace: 'nowrap',
        }}
      >
        <span style={{
          width: 8, height: 8, borderRadius: '50%', background: dot, flexShrink: 0,
          boxShadow: status === 'online' ? `0 0 5px ${dot}` : 'none',
        }} />
        <span>Motor</span>
        <span style={{ color: '#5B6673' }}>{engineLabel(status)}</span>
      </button>

      {open && createPortal(
        <div ref={popRef} style={{
          position: 'fixed', top: anchor.top, right: anchor.right, zIndex: 1000, width: 320,
          background: '#1A1E24', border: '1px solid #2A313A', borderRadius: 8,
          boxShadow: '0 8px 24px rgba(0,0,0,0.5)', padding: 14,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={{ width: 9, height: 9, borderRadius: '50%', background: dot, flexShrink: 0 }} />
            <span style={{ fontSize: 13, fontWeight: 600, color: '#E6E9ED' }}>
              Motor de compilación
            </span>
            <span style={{ fontSize: 11, color: '#5B6673', marginLeft: 'auto' }}>{engineLabel(status)}</span>
          </div>

          <p style={{ fontSize: 11, color: '#AEB6C0', lineHeight: '16px', margin: '0 0 10px' }}>
            {status === 'online'
              ? 'El motor convierte tu diseño en geometría 3D imprimible (vista 3D y exportación).'
              : 'Diseñá, validá y corregí sin conexión. El motor solo hace falta para la vista 3D y la exportación.'}
          </p>

          <label style={{ fontSize: 10, fontWeight: 600, letterSpacing: 0.5, textTransform: 'uppercase', color: '#5B6673', display: 'block', marginBottom: 4 }}>
            Dirección del motor
          </label>
          <input
            value={draft}
            onChange={e => setDraft(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') apply() }}
            spellCheck={false}
            placeholder={defaultUrl}
            style={{
              width: '100%', boxSizing: 'border-box', background: '#13161B', color: '#E6E9ED',
              border: '1px solid #2A313A', borderRadius: 5, padding: '7px 9px', fontSize: 12,
              fontFamily: 'var(--cf-font-mono)',
            }}
          />

          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 10 }}>
            <button
              onClick={apply}
              disabled={status === 'checking'}
              style={{
                background: '#C24A1C', color: '#fff', border: 'none', borderRadius: 5,
                padding: '6px 14px', fontSize: 12, fontWeight: 600,
                cursor: status === 'checking' ? 'default' : 'pointer', opacity: status === 'checking' ? 0.6 : 1,
              }}
            >{status === 'checking' ? 'Conectando…' : draft.trim() === url ? 'Reintentar' : 'Conectar'}</button>

            {draft.trim().replace(/\/+$/, '') !== defaultUrl && (
              <button
                onClick={() => { setDraft(defaultUrl); setEngineUrl(defaultUrl) }}
                style={{ background: 'transparent', color: '#AEB6C0', border: '1px solid #2A313A', borderRadius: 5, padding: '6px 12px', fontSize: 12, cursor: 'pointer' }}
              >Usar predeterminado</button>
            )}
          </div>

          <p style={{ fontSize: 10, color: '#5B6673', lineHeight: '14px', margin: '10px 0 0' }}>
            Local: <code style={{ fontFamily: 'var(--cf-font-mono)' }}>pnpm core:api</code> levanta el motor en{' '}
            <code style={{ fontFamily: 'var(--cf-font-mono)' }}>{defaultUrl}</code>.
          </p>
        </div>,
        document.body,
      )}
    </div>
  )
}
