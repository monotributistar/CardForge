// NewCardWizard — guided setup for a new card:
//   1. Template  2. Shape & size  3. Colours  4. Extras
// Builds a full v2 document (buildWizardDocument) and opens it in a tab.
//
// Every step past the first shows a live sketch of the card, so the choices
// are visible while they are being made rather than after Create.

import React, { useState } from 'react'
import type { Material, Outline } from '../types/cardforge'
import { DEFAULT_POCKET_CLEARANCE, DEFAULT_POCKET_DEPTH_CLEARANCE } from '../types/cardforge'
import { useDocumentStore } from '../state/DocumentStore'
import { useUIStore } from '../state/UIStore'
import {
  buildWizardDocument, minThicknessForPocket, WIZARD_POCKETS,
  type WizardOptions, type WizardPocket,
} from '../studio/document/defaults'
import { applySvgOutline, extractSvgFillColors, svgNaturalSize, DEFAULT_COLOR_DEPTH } from '../studio/services/SvgImport'
import { PALETTES } from '../studio/services/Filaments'
import { PaletteEditor, materialsFromPalette } from './PaletteEditor'
import { WizardPreview } from './WizardPreview'
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
  pocket?: string
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
    key: 'magnet', icon: '🧲', label: 'Fridge magnet',
    desc: '70 × 45 mm with a pocket for a Ø6 magnet',
    outline: { type: 'rounded-rect', width: 70, height: 45, radius: 4 },
    thickness: 3.0, hole: 'none', holeTab: false, pocket: 'magnet6',
  },
  {
    key: 'nfc', icon: '📶', label: 'NFC card',
    desc: '85 × 54 mm with a pocket for a Ø25 NFC tag',
    outline: { type: 'rounded-rect', width: 85, height: 54, radius: 4 },
    thickness: 2.4, hole: 'none', holeTab: false, pocket: 'rfid25',
  },
  {
    key: 'svg', icon: '🎨', label: 'SVG logo shape',
    desc: 'Upload an SVG — its shape becomes the card, its colors print on the front, the back stays free for text & QR',
    outline: { type: 'rounded-rect', width: 80, height: 50, radius: 4 },
    thickness: 2.0, hole: 'none', holeTab: false,
  },
  {
    key: 'custom', icon: '✏️', label: 'Custom',
    desc: 'Start from a blank 85 × 54 card',
    outline: { type: 'rounded-rect', width: 85, height: 54, radius: 4 },
    thickness: 1.8, hole: 'none', holeTab: false,
  },
]

const STEPS = ['Template', 'Shape', 'Colours', 'Extras']
const LAST = STEPS.length - 1

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
  const [materials, setMaterials] = useState<Material[]>(() => materialsFromPalette(PALETTES[0]))
  const [nozzle, setNozzle] = useState(0.4)
  const [hole, setHole] = useState<WizardOptions['hole']>(PRESETS[0].hole)
  const [holeTab, setHoleTab] = useState(PRESETS[0].holeTab)
  const [pocket, setPocket] = useState<WizardPocket | null>(null)
  const [sampleText, setSampleText] = useState(true)
  const [svgText, setSvgText] = useState<string | null>(null)
  const [svgColors, setSvgColors] = useState(0)
  // Where the artwork's colors live. 'through' = colors run the whole
  // thickness (both faces colored, nothing left as a clean canvas).
  const [colorSide, setColorSide] = useState<'front' | 'back' | 'both' | 'through'>('front')
  const [colorDepth, setColorDepth] = useState(DEFAULT_COLOR_DEPTH)
  const [backStarter, setBackStarter] = useState(true)

  const dims = outline.type === 'circle'
    ? { w: outline.diameter, h: outline.diameter }
    : { w: outline.width, h: outline.height }

  /** A pocket needs a body deep enough to hold the insert and still have a
   *  floor. Picking one raises the thickness rather than letting the card be
   *  created with an error already in it. */
  const choosePocket = (p: WizardPocket | null) => {
    setPocket(p)
    if (p) setThickness(t => Math.max(t, minThicknessForPocket(p)))
  }

  const pickPreset = (p: Preset) => {
    setPreset(p)
    setOutline(p.outline)
    setThickness(p.thickness)
    setHole(p.hole)
    setHoleTab(p.holeTab)
    setPocket(WIZARD_POCKETS.find(x => x.key === p.pocket) ?? null)
    setSvgText(null)
    setSvgColors(0)
    setColorSide('front')
    setColorDepth(DEFAULT_COLOR_DEPTH)
    setSampleText(p.key !== 'svg')  // the front belongs to the artwork
    setName(p.key === 'custom' ? 'My Card' : p.label)
    setStep(1)
  }

  const loadSvg = (file: File) => {
    void file.text().then(text => {
      const colors = extractSvgFillColors(text)
      if (!colors.length) return
      setSvgText(text)
      setSvgColors(colors.length)
      // Keep the chosen width, derive height from the artwork's aspect
      setOutline(o => {
        const w = o.type === 'circle' ? o.diameter : o.width
        const nat = svgNaturalSize(text)
        const h = nat ? Math.round(w * (nat.height / nat.width) * 100) / 100
          : (o.type === 'circle' ? o.diameter : o.height)
        return { type: 'rect', width: w, height: h }
      })
    })
  }

  const create = () => {
    const doc = buildWizardDocument({
      name, outline, thickness, nozzle, materials,
      hole, holeTab, pocket, sampleText,
      backStarter: svgText && backStarter ? 'text-qr' : 'none',
    })
    if (svgText) {
      applySvgOutline(doc, svgText, dims.w, {
        colorDepth: colorSide === 'through' ? 0 : colorDepth,
        ...(colorSide === 'through' ? {} : { colorFace: colorSide }),
      })
    }
    newTab(doc)
    closeWizard()
  }

  const setDim = (k: 'w' | 'h', v: number) => setOutline(o => {
    if (o.type === 'circle') return o
    if (svgText && k === 'w') {
      // SVG shape: width drives, height follows the artwork's aspect ratio
      const nat = svgNaturalSize(svgText)
      const h = nat ? Math.round(v * (nat.height / nat.width) * 100) / 100 : o.height
      return { ...o, width: v, height: h }
    }
    return { ...o, [k === 'w' ? 'width' : 'height']: v }
  })

  // ── Blocking problems (Create stays disabled while any is present) ──
  const problems: string[] = []
  if (pocket) {
    const need = minThicknessForPocket(pocket)
    if (thickness < need) {
      problems.push(`A ${pocket.label} pocket needs at least ${need}mm of thickness — the card is ${thickness}mm.`)
    }
    const bore = pocket.diameter + DEFAULT_POCKET_CLEARANCE
    if (bore + 2 > Math.min(dims.w, dims.h)) {
      problems.push(`A ${pocket.label} pocket is Ø${bore.toFixed(1)}mm and does not fit inside a ${dims.w} × ${dims.h}mm card.`)
    }
  }
  if (preset.key === 'svg' && !svgText) {
    problems.push('Upload an SVG, or go back and pick another template.')
  }

  const next = () => setStep(s => Math.min(LAST, s + 1))
  const canAdvance = step < LAST
  const onKeyDown = (e: React.KeyboardEvent) => {
    // Enter advances; on the last step it creates — unless a field is
    // mid-edit, where Enter means "commit this value".
    if (e.key !== 'Enter' || e.shiftKey) return
    const tag = (e.target as HTMLElement).tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
    e.preventDefault()
    if (step === 0) pickPreset(preset)
    else if (canAdvance) next()
    else if (!problems.length) create()
  }

  const showPreview = step > 0 && !narrow

  return (
    <Overlay onClose={closeWizard}>
      <div
        onKeyDown={onKeyDown}
        style={{
          width: showPreview ? 780 : 620, maxWidth: '94vw', maxHeight: '92vh', overflowY: 'auto',
          background: '#161b22', border: '1px solid #30363d', borderRadius: 12,
          boxShadow: '0 12px 40px rgba(0,0,0,0.6)', padding: '22px 26px 16px',
          display: 'flex', flexDirection: 'column', gap: 14,
        }}
      >
        {/* Header + step rail */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#e6edf3', flexShrink: 0 }}>New card</div>
          <div style={{ display: 'flex', gap: 4, flex: 1, minWidth: 0, overflow: 'hidden' }}>
            {STEPS.map((label, i) => {
              const done = i < step
              const active = i === step
              return (
                <button
                  key={label}
                  type="button"
                  // Going back is always allowed; jumping ahead is not, so a
                  // step is never skipped without its defaults being seen.
                  disabled={i > step}
                  onClick={() => setStep(i)}
                  className="cf-btn"
                  style={{
                    background: 'transparent', border: 'none', padding: '2px 6px',
                    fontSize: 11, cursor: i > step ? 'default' : 'pointer',
                    color: active ? '#58a6ff' : done ? '#3fb950' : '#484f58',
                    fontWeight: active ? 700 : 400, whiteSpace: 'nowrap',
                  }}
                >{i + 1}. {label}</button>
              )
            })}
          </div>
          <button onClick={closeWizard} title="Close (Esc)" style={{ background: 'transparent', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: 15, padding: 4, flexShrink: 0 }}>✕</button>
        </div>

        <div style={{ display: 'flex', gap: 18, alignItems: 'flex-start' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            {/* ── Step 1: template ─────────────────────────────────── */}
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

            {/* ── Step 2: shape & size ─────────────────────────────── */}
            {step === 1 && (
              <div>
                <Row label="Name" hint="Document name — also used for the exported file name">
                  <TextInput value={name} onCommit={setName} />
                </Row>
                {preset.key === 'svg' && (
                  <>
                    <Row label="SVG file" hint="The artwork's silhouette becomes the card shape; each color prints in its own filament">
                      <input type="file" accept=".svg,image/svg+xml" style={{ fontSize: 11, color: '#8b949e', maxWidth: 200 }}
                        onChange={e => { const f = e.target.files?.[0]; if (f) loadSvg(f); e.target.value = '' }} />
                    </Row>
                    {svgText && (
                      <>
                        <div style={{ fontSize: 11, color: '#3fb950', padding: '2px 0' }}>
                          ✓ SVG loaded — {svgColors} color{svgColors === 1 ? '' : 's'} detected (each gets a material)
                        </div>
                        <Row label="Colors on" hint="Which face shows the artwork. The other face prints solid in the base material — that's where text and QR go">
                          <Select
                            value={colorSide}
                            options={[['front', 'Front only'], ['back', 'Back only'], ['both', 'Both faces'], ['through', 'Through (solid colors)']]}
                            onCommit={v => setColorSide(v as typeof colorSide)}
                          />
                        </Row>
                        {colorSide !== 'through' && (
                          <Row label="Color depth (mm)" hint="How deep the colored layer goes. 0.6mm (3 layers) reads solid; the rest of the body stays base material">
                            <NumInput value={colorDepth} step={0.2} min={0.2} max={Math.max(0.2, thickness / 2)}
                              onCommit={setColorDepth} />
                          </Row>
                        )}
                      </>
                    )}
                  </>
                )}
                {/* With artwork loaded the silhouette IS the shape — but until
                    then the card is still an ordinary rectangle to size. */}
                {!svgText && (
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
                )}
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
                    <Row label="Height (mm)" hint={svgText ? 'Follows the artwork’s aspect ratio' : 'Card height in millimeters'}>
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

            {/* ── Step 3: colours ──────────────────────────────────── */}
            {step === 2 && (
              <div>
                <PaletteEditor materials={materials} onChange={setMaterials} />
                {svgText && (
                  <div style={{ fontSize: 11, color: '#8b949e', marginTop: 12 }}>
                    The artwork's {svgColors} colour{svgColors === 1 ? '' : 's'} get their own materials on top of these
                    when the card is created.
                  </div>
                )}
              </div>
            )}

            {/* ── Step 4: extras ───────────────────────────────────── */}
            {step === 3 && (
              <div>
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
                <Row label="Insert pocket" hint="A blind cavity for a magnet or an RFID/NFC tag, open at the front face so the insert drops in after printing">
                  <Select
                    value={pocket?.key ?? 'none'}
                    options={[['none', 'None'], ...WIZARD_POCKETS.map(p => [p.key, p.label] as [string, string])]}
                    onCommit={v => choosePocket(WIZARD_POCKETS.find(p => p.key === v) ?? null)}
                  />
                </Row>
                {pocket && (
                  <div style={{ fontSize: 11, color: '#8b949e', margin: '-2px 0 8px' }}>
                    Bore Ø{(pocket.diameter + DEFAULT_POCKET_CLEARANCE).toFixed(1)}mm × {(pocket.depth + DEFAULT_POCKET_DEPTH_CLEARANCE).toFixed(1)}mm deep
                    (insert + fit clearance) — needs {minThicknessForPocket(pocket)}mm of thickness.
                    Fine-tune the fit in the inspector afterwards.
                  </div>
                )}
                <Row label="Sample text" hint="Start with an editable 6mm name text on the front">
                  <input type="checkbox" checked={sampleText} onChange={e => setSampleText(e.target.checked)} style={{ width: 15, height: 15 }} />
                </Row>
                {svgText && (
                  <Row label="Back starter" hint="Puts a QR and a caption on the back as flush inlays — the face the artwork's colors leave free">
                    <input type="checkbox" checked={backStarter} onChange={e => setBackStarter(e.target.checked)} style={{ width: 15, height: 15 }} />
                  </Row>
                )}
              </div>
            )}
          </div>

          {showPreview && (
            <div style={{ width: 300, flexShrink: 0, position: 'sticky', top: 0 }}>
              <WizardPreview
                outline={outline} materials={materials} thickness={thickness}
                hole={hole} holeTab={holeTab} pocket={pocket}
                sampleText={sampleText} svgText={svgText}
              />
            </div>
          )}
        </div>

        {problems.length > 0 && step === LAST && (
          <div style={{
            padding: '8px 10px', borderRadius: 6, fontSize: 11, lineHeight: 1.5,
            background: 'rgba(248,81,73,0.08)', border: '1px solid rgba(248,81,73,0.4)', color: '#f85149',
          }}>
            {problems.map((p, i) => <div key={i}>{p}</div>)}
          </div>
        )}

        {/* Footer nav */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', justifyContent: 'flex-end', borderTop: '1px solid #21262d', paddingTop: 12 }}>
          {step > 0 && <Btn onClick={() => setStep(s => s - 1)}>← Back</Btn>}
          <span style={{ flex: 1 }} />
          {canAdvance && <Btn primary onClick={next}>Next →</Btn>}
          {!canAdvance && (
            <Btn primary onClick={create} disabled={problems.length > 0}
              title={problems.length ? problems[0] : 'Create the card (Enter)'}>Create card</Btn>
          )}
        </div>
      </div>
    </Overlay>
  )
}
