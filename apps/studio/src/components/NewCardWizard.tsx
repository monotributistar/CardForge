// NewCardWizard — 3-step guided setup for a new card:
//   1. Template  2. Shape & size  3. Materials & extras
// Builds a full v2 document (buildWizardDocument) and opens it in a tab.

import React, { useState } from 'react'
import type { Outline } from '../types/cardforge'
import { useDocumentStore } from '../state/DocumentStore'
import { useUIStore } from '../state/UIStore'
import { buildWizardDocument, type WizardOptions } from '../studio/document/defaults'
import { Overlay, Btn, Row, NumInput, TextInput, Select, useIsNarrow } from './ui'

// ── Presets ──────────────────────────────────────────────────────────

interface Preset {
  key: string
  icon: string
  label: string
  desc: string
  outline: Outline
  thickness: number
  hole: WizardOptions['hole']
  holeTab: boolean
}

const PRESETS: Preset[] = [
  {
    key: 'business', icon: '💼', label: 'Business card',
    desc: '85 × 54 mm — the classic pocket card',
    outline: { type: 'rounded-rect', width: 85, height: 54, radius: 4 },
    thickness: 1.8, hole: 'none', holeTab: false,
  },
  {
    key: 'keychain', icon: '🔑', label: 'Keychain tag',
    desc: '50 × 30 mm with a keyring hole on a tab',
    outline: { type: 'rounded-rect', width: 50, height: 30, radius: 5 },
    thickness: 2.4, hole: 'keyring', holeTab: true,
  },
  {
    key: 'badge', icon: '🪪', label: 'Badge / credential',
    desc: '86 × 54 mm with a lanyard slot on top',
    outline: { type: 'rounded-rect', width: 86, height: 54, radius: 3 },
    thickness: 1.6, hole: 'lanyard', holeTab: false,
  },
  {
    key: 'round', icon: '⭕', label: 'Round tag',
    desc: 'Ø 40 mm disc with a keyring hole',
    outline: { type: 'circle', diameter: 40 },
    thickness: 2.0, hole: 'keyring', holeTab: false,
  },
  {
    key: 'custom', icon: '✏️', label: 'Custom',
    desc: 'Start from a blank 85 × 54 card',
    outline: { type: 'rounded-rect', width: 85, height: 54, radius: 4 },
    thickness: 1.8, hole: 'none', holeTab: false,
  },
]

// ── Wizard ───────────────────────────────────────────────────────────

export const NewCardWizard: React.FC = () => {
  const closeWizard = useUIStore(s => s.closeWizard)
  const newTab = useDocumentStore(s => s.newTab)
  const narrow = useIsNarrow()

  const [step, setStep] = useState(0)
  const [preset, setPreset] = useState<Preset>(PRESETS[0])
  const [name, setName] = useState('My Card')
  const [outline, setOutline] = useState<Outline>(PRESETS[0].outline)
  const [thickness, setThickness] = useState(PRESETS[0].thickness)
  const [baseColor, setBaseColor] = useState('#1a1a1a')
  const [baseName, setBaseName] = useState('PLA Black')
  const [textColor, setTextColor] = useState('#ffffff')
  const [textName, setTextName] = useState('PLA White')
  const [accentOn, setAccentOn] = useState(true)
  const [accentColor, setAccentColor] = useState('#d4af37')
  const [accentName, setAccentName] = useState('PLA Gold')
  const [nozzle, setNozzle] = useState(0.4)
  const [hole, setHole] = useState<WizardOptions['hole']>(PRESETS[0].hole)
  const [holeTab, setHoleTab] = useState(PRESETS[0].holeTab)
  const [sampleText, setSampleText] = useState(true)

  const pickPreset = (p: Preset) => {
    setPreset(p)
    setOutline(p.outline)
    setThickness(p.thickness)
    setHole(p.hole)
    setHoleTab(p.holeTab)
    setName(p.key === 'custom' ? 'My Card' : p.label)
    setStep(1)
  }

  const create = () => {
    const doc = buildWizardDocument({
      name, outline, thickness, nozzle,
      baseColor, baseName, textColor, textName,
      ...(accentOn ? { accentColor, accentName } : {}),
      hole, holeTab, sampleText,
    })
    newTab(doc)
    closeWizard()
  }

  const dims = outline.type === 'circle'
    ? { w: outline.diameter, h: outline.diameter }
    : { w: outline.width, h: outline.height }

  const setDim = (k: 'w' | 'h', v: number) => setOutline(o =>
    o.type === 'circle' ? o : { ...o, [k === 'w' ? 'width' : 'height']: v })

  return (
    <Overlay onClose={closeWizard}>
      <div style={{
        width: 620, maxWidth: '94vw', maxHeight: '92vh', overflowY: 'auto',
        background: '#161b22', border: '1px solid #30363d', borderRadius: 12,
        boxShadow: '0 12px 40px rgba(0,0,0,0.6)', padding: '22px 26px 16px',
        display: 'flex', flexDirection: 'column', gap: 14,
      }}>
        {/* Header + step dots */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#e6edf3', flex: 1 }}>New card</div>
          <div style={{ display: 'flex', gap: 6 }}>
            {[0, 1, 2].map(i => (
              <span key={i} style={{
                width: 8, height: 8, borderRadius: '50%',
                background: i === step ? '#1f6feb' : i < step ? '#3fb950' : '#30363d',
              }} />
            ))}
          </div>
          <button onClick={closeWizard} style={{ background: 'transparent', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: 15, padding: 4 }}>✕</button>
        </div>

        {/* ── Step 1: template ─────────────────────────────────────── */}
        {step === 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: narrow ? '1fr' : '1fr 1fr', gap: 10 }}>
            {PRESETS.map(p => (
              <div
                key={p.key}
                onClick={() => pickPreset(p)}
                style={{
                  display: 'flex', gap: 12, alignItems: 'center', padding: '14px 14px',
                  border: `1px solid ${preset.key === p.key ? '#1f6feb' : '#30363d'}`,
                  borderRadius: 8, cursor: 'pointer', background: '#0d1117',
                }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = '#58a6ff' }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = preset.key === p.key ? '#1f6feb' : '#30363d' }}
              >
                <span style={{ fontSize: 24 }}>{p.icon}</span>
                <span style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#e6edf3' }}>{p.label}</div>
                  <div style={{ fontSize: 11, color: '#8b949e' }}>{p.desc}</div>
                </span>
              </div>
            ))}
          </div>
        )}

        {/* ── Step 2: shape & size ─────────────────────────────────── */}
        {step === 1 && (
          <div>
            <Row label="Name" hint="Document name — also used for the exported file name">
              <TextInput value={name} onCommit={setName} />
            </Row>
            <Row label="Shape" hint="Overall outline of the card body">
              <Select
                value={outline.type === 'circle' ? 'circle' : outline.type}
                options={[['rounded-rect', 'Rounded rectangle'], ['rect', 'Rectangle'], ['circle', 'Circle']]}
                onCommit={v => setOutline(o => {
                  const { w, h } = o.type === 'circle' ? { w: o.diameter, h: o.diameter } : { w: o.width, h: o.height }
                  if (v === 'circle') return { type: 'circle', diameter: Math.min(w, h) }
                  if (v === 'rect') return { type: 'rect', width: w, height: h }
                  return { type: 'rounded-rect', width: w, height: h, radius: 4 }
                })}
              />
            </Row>
            {outline.type === 'circle' ? (
              <Row label="Diameter (mm)" hint="Disc diameter in millimeters">
                <NumInput value={outline.diameter} step={1} min={10}
                  onCommit={v => setOutline({ type: 'circle', diameter: v })} />
              </Row>
            ) : (
              <>
                <Row label="Width (mm)" hint="Card width in millimeters">
                  <NumInput value={dims.w} step={1} min={10} onCommit={v => setDim('w', v)} />
                </Row>
                <Row label="Height (mm)" hint="Card height in millimeters">
                  <NumInput value={dims.h} step={1} min={10} onCommit={v => setDim('h', v)} />
                </Row>
              </>
            )}
            {outline.type === 'rounded-rect' && (
              <Row label="Corner radius" hint="Rounding of the four corners, in mm">
                <NumInput value={outline.radius} step={0.5} min={0}
                  onCommit={v => setOutline(o => o.type === 'rounded-rect' ? { ...o, radius: v } : o)} />
              </Row>
            )}
            <Row label="Thickness (mm)" hint="Body thickness. 1.6–2.4mm prints rigid without wasting filament">
              <NumInput value={thickness} step={0.1} min={0.6} max={10} onCommit={setThickness} />
            </Row>
          </div>
        )}

        {/* ── Step 3: materials & extras ───────────────────────────── */}
        {step === 2 && (
          <div>
            <ColorRow label="Base" hint="Body color — filament slot 1" color={baseColor} name={baseName}
              onColor={setBaseColor} onName={setBaseName} />
            <ColorRow label="Text" hint="Text & details color — filament slot 2" color={textColor} name={textName}
              onColor={setTextColor} onName={setTextName} />
            <Row label="Accent" hint="Optional third color — filament slot 3">
              <input type="checkbox" checked={accentOn} onChange={e => setAccentOn(e.target.checked)} style={{ width: 15, height: 15 }} />
            </Row>
            {accentOn && (
              <ColorRow label="" hint="" color={accentColor} name={accentName}
                onColor={setAccentColor} onName={setAccentName} />
            )}
            <Row label="Nozzle (mm)" hint="Printer nozzle — drives the minimum printable detail checks">
              <Select value={String(nozzle)} options={[['0.2', '0.2'], ['0.4', '0.4 (standard)'], ['0.6', '0.6']]}
                onCommit={v => setNozzle(Number(v))} />
            </Row>
            <Row label="Hole" hint="Through-hole for a keyring or a lanyard strap">
              <Select value={hole} options={[['none', 'None'], ['keyring', 'Keyring (Ø5 circle)'], ['lanyard', 'Lanyard slot (14×5)']]}
                onCommit={v => setHole(v as WizardOptions['hole'])} />
            </Row>
            {hole !== 'none' && (
              <Row label="Hole tab" hint="Adds material around the hole so it can sit on the card edge">
                <input type="checkbox" checked={holeTab} onChange={e => setHoleTab(e.target.checked)} style={{ width: 15, height: 15 }} />
              </Row>
            )}
            <Row label="Sample text" hint="Start with an editable 6mm name text on the front">
              <input type="checkbox" checked={sampleText} onChange={e => setSampleText(e.target.checked)} style={{ width: 15, height: 15 }} />
            </Row>
          </div>
        )}

        {/* Footer nav */}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', borderTop: '1px solid #21262d', paddingTop: 12 }}>
          {step > 0 && <Btn onClick={() => setStep(s => s - 1)}>← Back</Btn>}
          <span style={{ flex: 1 }} />
          {step < 2 && <Btn primary onClick={() => setStep(s => s + 1)}>Next →</Btn>}
          {step === 2 && <Btn primary onClick={create}>Create card</Btn>}
        </div>
      </div>
    </Overlay>
  )
}

// Color + name pair for a material row.
const ColorRow: React.FC<{
  label: string; hint: string; color: string; name: string
  onColor: (v: string) => void; onName: (v: string) => void
}> = ({ label, hint, color, name, onColor, onName }) => (
  <Row label={label} hint={hint || undefined}>
    <div style={{ display: 'flex', gap: 8, flex: 1, minWidth: 0, alignItems: 'center' }}>
      <input
        type="color" value={color} onChange={e => onColor(e.target.value)}
        style={{ width: 38, height: 30, padding: 0, border: '1px solid #30363d', borderRadius: 4, background: 'transparent', cursor: 'pointer', flexShrink: 0 }}
      />
      <TextInput value={name} onCommit={onName} />
    </div>
  </Row>
)
