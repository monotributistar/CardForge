// Inspector — organized property editor for selected feature
import React from 'react'
import type { Feature, CardForgeDocument } from '../types'
import { FIELD_DEFS, type QRType, getQRFields } from '../services/QRFields'

interface InspectorProps {
  selectedFeature: Feature | null
  document: CardForgeDocument | null
  onUpdateText: (featureId: string, lines: string[]) => void
  onUpdateFont: (featureId: string, font: string) => void
  onUpdateFontSize: (featureId: string, size: number) => void
  onUpdateRelief: (featureId: string, height: number) => void
  onUpdateMaterial: (featureId: string, mat: string) => void
  onUpdateQRValue: (featureId: string, value: string) => void
  onUpdateQRType: (featureId: string, type: string) => void
  onUpdateQRField: (featureId: string, field: string, value: string) => void
  onUpdateQRSize: (featureId: string, size: number) => void
  onUpdatePosX: (featureId: string, x: number) => void
  onUpdatePosY: (featureId: string, y: number) => void
  onReplaceLogo: (featureId: string, svgContent: string) => void
  reliefPreset: string
  onReliefPreset: (preset: string) => void
  theme: string
  onTheme: (theme: string) => void
}

const RELIEF_PRESETS: Record<string, { height: number; label: string }> = {
  flat:    { height: 0.0, label: 'Flat (0mm)' },
  subtle:  { height: 0.2, label: 'Subtle (0.2mm)' },
  standard:{ height: 0.4, label: 'Standard (0.4mm)' },
  strong:  { height: 0.6, label: 'Strong (0.6mm)' },
}

const THEMES: Record<string, { base: string; text: string; accent: string; label: string }> = {
  minimal:    { base: 'white', text: 'black', accent: 'black', label: 'Minimal' },
  'dark-luxury': { base: 'black', text: 'white', accent: 'gold', label: 'Dark Luxury' },
  tech:       { base: '#0a0a0a', text: '#00ff88', accent: '#00ff88', label: 'Tech' },
  industrial: { base: '#2a2a2a', text: '#ff6b35', accent: '#ff6b35', label: 'Industrial' },
}

const S = {
  section: { marginBottom: 14 } as React.CSSProperties,
  title: { fontSize: 11, fontWeight: 600, color: '#8b949e', textTransform: 'uppercase' as const, marginBottom: 6, borderBottom: '1px solid #21262d', paddingBottom: 4 },
  row: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12, padding: '3px 0' },
  label: { color: '#8b949e', minWidth: 55, fontSize: 11 },
  input: { background: '#0d1117', color: '#c9d1d9', border: '1px solid #30363d', borderRadius: 4, padding: '2px 6px', fontSize: 12, width: 90 },
  textarea: { background: '#0d1117', color: '#c9d1d9', border: '1px solid #30363d', borderRadius: 4, padding: '4px 6px', fontSize: 12, width: '100%', minHeight: 50, resize: 'vertical' as const, fontFamily: 'monospace' },
  select: { background: '#0d1117', color: '#c9d1d9', border: '1px solid #30363d', borderRadius: 4, padding: '2px 4px', fontSize: 12 },
  presetRow: { display: 'flex', gap: 4, marginBottom: 8 },
  presetBtn: (active: boolean): React.CSSProperties => ({
    background: active ? '#1f6feb' : '#21262d', color: active ? '#fff' : '#8b949e',
    border: '1px solid #30363d', padding: '2px 8px', borderRadius: 4, cursor: 'pointer', fontSize: 11,
  }),
  empty: { fontSize: 12, color: '#484f58', fontStyle: 'italic' as const },
  value: { color: '#c9d1d9', fontSize: 12 },
}

export const Inspector: React.FC<InspectorProps> = (props) => {
  const { selectedFeature: f, document: doc, reliefPreset, onReliefPreset, theme, onTheme } = props

  if (f && f.type === 'text-block') {
    return (
      <div>
        <Section t="🎨 Theme">
          <div style={S.presetRow}>
            {Object.entries(THEMES).map(([k, v]) => (
              <button key={k} style={S.presetBtn(theme === k)} onClick={() => onTheme(k)}>{v.label}</button>
            ))}
          </div>
        </Section>
        <Section t="📝 Content">
          <textarea style={S.textarea}
            value={(f as any).lines?.join('\n') ?? ''}
            onChange={e => props.onUpdateText(f.id, e.target.value.split('\n'))}
          />
        </Section>
        <Section t="📐 Position">
          <Row l="X mm"><input type="number" style={S.input} step={0.1} value={f.position?.x ?? 0}
            onChange={e => props.onUpdatePosX(f.id, parseFloat(e.target.value) || 0)} /></Row>
          <Row l="Y mm"><input type="number" style={S.input} step={0.1} value={f.position?.y ?? 0}
            onChange={e => props.onUpdatePosY(f.id, parseFloat(e.target.value) || 0)} /></Row>
        </Section>
        <Section t="✨ Appearance">
          <Row l="Font">
            <select style={{ ...S.select, width: 110 }} value={f.font ?? 'Montserrat'}
              onChange={e => props.onUpdateFont(f.id, e.target.value)}>
              {['Arial', 'Helvetica', 'Montserrat', 'Roboto', 'Courier New', 'Inter', 'Georgia', 'Times New Roman'].map(fn => (
                <option key={fn} value={fn}>{fn}</option>
              ))}
            </select>
          </Row>
          <Row l="Font Size">
            <input type="number" style={S.input} step={0.1} min={2} max={8}
              value={f.fontSize ?? 3}
              onChange={e => props.onUpdateFontSize(f.id, parseFloat(e.target.value) || 3)} />
          </Row>
          <Row l="Material">
            <select style={S.select} value={f.material ?? 'text'}
              onChange={e => props.onUpdateMaterial(f.id, e.target.value)}>
              <option value="text">Text</option><option value="base">Base</option><option value="accent">Accent</option>
            </select>
          </Row>
        </Section>
        <Section t="🔧 Relief">
          <div style={S.presetRow}>
            {Object.entries(RELIEF_PRESETS).map(([k, v]) => (
              <button key={k} style={S.presetBtn(reliefPreset === k)}
                onClick={() => { onReliefPreset(k); props.onUpdateRelief(f.id, v.height) }}>{v.label}</button>
            ))}
          </div>
        </Section>
      </div>
    )
  }

  if (f && f.type === 'qr') {
    const qrType = ((f as any).qrType || 'url') as QRType
    const fields = getQRFields(f)
    const defs = FIELD_DEFS[qrType]
    return (
      <div>
        <Section t="📝 QR Code">
          <Row l="Type">
            <select style={{ ...S.select, width: 100 }} value={qrType}
              onChange={e => props.onUpdateQRType(f.id, e.target.value)}>
              <option value="url">Link</option>
              <option value="vcard">vCard</option>
              <option value="wifi">WiFi</option>
              <option value="email">Email</option>
              <option value="text">Text</option>
            </select>
          </Row>
          {defs.map(d => {
            const val = (fields as any)[d.key] || ''
            if (d.type === 'select') {
              return <Row key={d.key} l={d.label}>
                <select style={{ ...S.select, width: 100 }} value={val}
                  onChange={e => (props as any).onUpdateQRField(f.id, d.key, e.target.value)}>
                  <option value="WPA">WPA</option>
                  <option value="WEP">WEP</option>
                  <option value="nopass">Open</option>
                </select>
              </Row>
            }
            if (d.type === 'textarea') {
              return <div key={d.key} style={{ marginBottom: 6 }}>
                <div style={{ fontSize: 11, color: '#8b949e', marginBottom: 2 }}>{d.label}</div>
                <textarea style={{ ...S.textarea, minHeight: 40 }} value={val}
                  onChange={e => (props as any).onUpdateQRField(f.id, d.key, e.target.value)}
                  placeholder={d.placeholder} />
              </div>
            }
            return <Row key={d.key} l={d.label}>
              <input style={{ ...S.input, width: '100%' }} value={val}
                onChange={e => (props as any).onUpdateQRField(f.id, d.key, e.target.value)}
                placeholder={d.placeholder} />
            </Row>
          })}
          <Row l="Size mm"><input type="number" style={S.input} step={1} min={16} max={60}
            value={typeof f.size === 'number' ? f.size : (f.size as any)?.width ?? 24}
            onChange={e => props.onUpdateQRSize(f.id, parseInt(e.target.value) || 24)} /></Row>
          <Row l="Material">
            <select style={S.select} value={f.material ?? 'text'}
              onChange={e => props.onUpdateMaterial(f.id, e.target.value)}>
              <option value="text">Text / White</option>
              <option value="base">Base / Dark</option>
              <option value="accent">Accent / Gold</option>
            </select>
          </Row>
        </Section>
        <Section t="📐 Position">
          <Row l="X mm"><input type="number" style={S.input} step={0.1} value={f.position?.x ?? 0}
            onChange={e => props.onUpdatePosX(f.id, parseFloat(e.target.value) || 0)} /></Row>
          <Row l="Y mm"><input type="number" style={S.input} step={0.1} value={f.position?.y ?? 0}
            onChange={e => props.onUpdatePosY(f.id, parseFloat(e.target.value) || 0)} /></Row>
        </Section>
      </div>
    )
  }

  if (f && f.type === 'logo') {
    return (
      <div>
        <Section t="🖼️ Logo">
          <Row l="File" v={(f as any).file ?? '(none)'} />
          <input type="file" accept=".svg" style={{ marginTop: 4, fontSize: 11 }}
            onChange={async e => {
              const file = e.target.files?.[0]; if (!file) return
              const text = await file.text()
              props.onReplaceLogo(f.id, text)
            }} />
        </Section>
        <Section t="📐 Position">
          <Row l="X mm"><input type="number" style={S.input} step={0.1} value={f.position?.x ?? 0}
            onChange={e => props.onUpdatePosX(f.id, parseFloat(e.target.value) || 0)} /></Row>
          <Row l="Y mm"><input type="number" style={S.input} step={0.1} value={f.position?.y ?? 0}
            onChange={e => props.onUpdatePosY(f.id, parseFloat(e.target.value) || 0)} /></Row>
        </Section>
      </div>
    )
  }

  if (f) {
    return <Section t="Feature"><Row l="ID" v={f.id} /><Row l="Type" v={f.type} /></Section>
  }

  if (doc) {
    return (
      <div>
        <Section t="📄 Document"><Row l="Name" v={doc.document.name} /></Section>
        <Section t="🎨 Theme">
          <div style={S.presetRow}>
            {Object.entries(THEMES).map(([k, v]) => (
              <button key={k} style={S.presetBtn(theme === k)} onClick={() => onTheme(k)}>{v.label}</button>
            ))}
          </div>
        </Section>
        {doc.manufacturing && <Section t="⚙️ Manufacturing"><Row l="Process" v={doc.manufacturing.process.toUpperCase()} /><Row l="Material" v={doc.manufacturing.material} /><Row l="Nozzle" v={`${doc.manufacturing.nozzle}mm`} /></Section>}
      </div>
    )
  }

  return <div style={S.empty}>Select a feature to edit</div>
}

const Section: React.FC<{ t: string; children: React.ReactNode }> = ({ t, children }) => (
  <div style={S.section}><div style={S.title}>{t}</div>{children}</div>)
const Row: React.FC<{ l: string; v?: string; children?: React.ReactNode }> = ({ l, v, children }) => (
  <div style={S.row}><span style={S.label}>{l}</span>{children ?? <span style={S.value}>{v}</span>}</div>)
