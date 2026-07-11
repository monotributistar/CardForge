// Inspector — per-type property editors bound to the selected feature.
// When nothing is selected, shows the document properties instead.
// Every change goes through DocumentStore.applyEdit (undoable).

import React from 'react'
import type {
  DocumentV2, Feature, Material, ReliefMode, Outline, Fill,
  TextBlockFeature, TextPatternFeature, PatternFeature, QRFeature, IconFeature, ShapeFeature, HoleFeature,
} from '../../types/cardforge'
import { useDocumentStore, getActiveTab, findFeature, removeFeatures } from '../../state/DocumentStore'
import { FIELD_DEFS, QR_TYPE_LABELS, type QRType } from '../services/QRFields'
import { applySvgToFeature, extractSvgPathD } from '../services/SvgImport'
import { ICON_LIBRARY, ICON_CATEGORY_LABELS, libraryIconSvg, type IconCategory, type LibraryIcon } from '../services/IconLibrary'
import { listFonts, type FontInfo } from '../core/CoreClient'

// One-time CSS injection: hide the native number spinners (redundant with the
// stepper's own +/- buttons) and give those buttons hover/active feedback.
// The app styles inline, so this is the single place that needs a stylesheet.
if (typeof document !== 'undefined' && !document.getElementById('cf-num-stepper-style')) {
  const el = document.createElement('style')
  el.id = 'cf-num-stepper-style'
  el.textContent =
    '.cf-num-stepper input[type=number]::-webkit-inner-spin-button,' +
    '.cf-num-stepper input[type=number]::-webkit-outer-spin-button{-webkit-appearance:none;margin:0}' +
    '.cf-num-stepper input[type=number]{-moz-appearance:textfield;appearance:textfield}' +
    '.cf-num-stepper button:hover:not(:disabled){background:#30363d;color:#fff}' +
    '.cf-num-stepper button:active:not(:disabled){background:#1f6feb;color:#fff}' +
    '.cf-num-stepper button:disabled{opacity:.4;cursor:default}'
  document.head.appendChild(el)
}

// Font families the Core can render — fetched once, cached in CoreClient.
function useFonts(): FontInfo[] {
  const [fonts, setFonts] = React.useState<FontInfo[]>([])
  React.useEffect(() => {
    let alive = true
    listFonts().then(f => { if (alive) setFonts(f) })
    return () => { alive = false }
  }, [])
  return fonts
}

type ApplyEdit = (mutator: (doc: DocumentV2) => void) => void

// ── Root ─────────────────────────────────────────────────────────────

export const Inspector: React.FC = () => {
  const tab = useDocumentStore(getActiveTab)
  const applyEdit = useDocumentStore(s => s.applyEdit)

  if (!tab) {
    return <Empty text="No document open" />
  }
  const doc = tab.doc
  const found = tab.selectedFeatureId && !tab.objectSelected ? findFeature(doc, tab.selectedFeatureId) : null

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: 10, fontSize: 12, color: '#c9d1d9' }}>
      {found
        ? <FeatureInspector doc={doc} feature={found.feature} selectedIds={tab.selectedFeatureIds} applyEdit={applyEdit} />
        : <DocumentInspector doc={doc} applyEdit={applyEdit} />}
    </div>
  )
}

const Empty: React.FC<{ text: string }> = ({ text }) => (
  <div style={{ padding: 16, color: '#484f58', fontSize: 12 }}>{text}</div>
)

// ── Feature inspector ────────────────────────────────────────────────

const FeatureInspector: React.FC<{ doc: DocumentV2; feature: Feature; selectedIds: string[]; applyEdit: ApplyEdit }> = ({ doc, feature, selectedIds, applyEdit }) => {
  const select = useDocumentStore(s => s.select)
  const edit = <T extends Feature>(fn: (f: T) => void) => {
    applyEdit(d => {
      for (const face of ['front', 'back'] as const) {
        const f = d.faces[face]?.features.find(x => x.id === feature.id)
        if (f) { fn(f as T); return }
      }
    })
  }

  const duplicate = () => {
    let newId = `${feature.id}-copy`
    applyEdit(d => {
      for (const face of ['front', 'back'] as const) {
        const list = d.faces[face]?.features
        const src = list?.find(x => x.id === feature.id)
        if (!list || !src) continue
        while (findFeature(d, newId)) newId = `${newId}-copy`
        const copy = structuredClone(src)
        copy.id = newId
        copy.transform.x = Math.round((copy.transform.x + 3) * 10) / 10
        copy.transform.y = Math.round((copy.transform.y + 3) * 10) / 10
        list.push(copy)
        return
      }
    })
    select(newId)
  }

  const deleteSelected = () => {
    const ids = selectedIds.length > 0 ? selectedIds : [feature.id]
    applyEdit(d => removeFeatures(d, ids))
    select(null)
  }

  return (
    <div>
      <Section title={`${feature.type}`}>
        <Row label="Actions">
          <div style={{ display: 'flex', gap: 4 }}>
            <ActionBtn title="Bring forward (zOrder +1)" onClick={() => edit(f => { f.zOrder = (f.zOrder ?? 0) + 1 })}>⬆</ActionBtn>
            <ActionBtn title="Send back (zOrder −1)" onClick={() => edit(f => { f.zOrder = (f.zOrder ?? 0) - 1 })}>⬇</ActionBtn>
            <ActionBtn title="Duplicate" onClick={duplicate}>⧉</ActionBtn>
            <ActionBtn title={selectedIds.length > 1 ? `Delete ${selectedIds.length} features` : 'Delete'} onClick={deleteSelected}>🗑</ActionBtn>
          </div>
        </Row>
        <Row label="ID"><ReadOnly value={feature.id} /></Row>
        <Row label="Name">
          <TextInput value={feature.name ?? ''} placeholder={feature.id}
            onCommit={v => edit(f => { if (v) f.name = v; else delete f.name })} />
        </Row>
        <Row label="X (mm)"><NumInput value={feature.transform.x} step={0.1} onCommit={v => edit(f => { f.transform.x = v })} /></Row>
        <Row label="Y (mm)"><NumInput value={feature.transform.y} step={0.1} onCommit={v => edit(f => { f.transform.y = v })} /></Row>
        <Row label="Rotation"><NumInput value={feature.transform.rotation ?? 0} step={1} onCommit={v => edit(f => { f.transform.rotation = v })} /></Row>
        <Row label="Material"><MaterialSelect materials={doc.materials} value={feature.material} onCommit={v => edit(f => { f.material = v })} /></Row>
        <Row label="Z-order"><NumInput value={feature.zOrder ?? 0} step={1} onCommit={v => edit(f => { f.zOrder = v })} /></Row>
        <Row label="Visible">
          <input type="checkbox" checked={feature.visible !== false}
            onChange={e => edit(f => { f.visible = e.target.checked })} />
        </Row>
      </Section>

      {/* A hole is always a through-cut: relief and backing don't apply. */}
      {feature.type !== 'hole' && (
        <>
          <ReliefEditor feature={feature} materials={doc.materials} edit={edit}
            isBack={doc.faces.back?.features.some(f => f.id === feature.id) ?? false} />

          <BackingEditor feature={feature} materials={doc.materials} edit={edit} />
        </>
      )}

      {feature.type === 'text-block' && <TextBlockEditor feature={feature} edit={edit} />}
      {feature.type === 'text-pattern' && <TextPatternEditor feature={feature} edit={edit} />}
      {feature.type === 'pattern' && <PatternEditor feature={feature} edit={edit} />}
      {feature.type === 'qr' && <QREditor feature={feature} edit={edit} />}
      {feature.type === 'icon' && <IconEditor feature={feature} materials={doc.materials} edit={edit} />}
      {feature.type === 'shape' && <ShapeEditor feature={feature} edit={edit} />}
      {feature.type === 'hole' && <HoleEditor feature={feature} edit={edit} />}
    </div>
  )
}

type EditFn = <T extends Feature>(fn: (f: T) => void) => void

// ── Relief ───────────────────────────────────────────────────────────

const RELIEF_MODES: ReliefMode[] = ['emboss', 'deboss', 'flush', 'cut', 'deboss-backed']
// The bed-facing (back) face must stay flat — no emboss (raised) geometry.
const BACK_RELIEF_MODES: ReliefMode[] = ['deboss', 'flush', 'cut', 'deboss-backed']

const ReliefEditor: React.FC<{ feature: Feature; materials: Material[]; edit: EditFn; isBack: boolean }> = ({ feature, materials, edit, isBack }) => {
  const relief = feature.relief
  const modes = isBack ? BACK_RELIEF_MODES : RELIEF_MODES
  return (
    <Section title="Relief">
      <Row label="Mode">
        <Select value={relief.mode} options={modes.map(m => [m, m])}
          onCommit={v => edit(f => {
            // Rebuild the relief with only the new mode's params — stale
            // leftovers (e.g. emboss height on a deboss) fail validation.
            const prev = f.relief
            const mode = v as ReliefMode
            if (mode === 'emboss') {
              f.relief = { mode, height: prev.height ?? 0.4 }
            } else if (mode === 'cut') {
              f.relief = { mode }
            } else if (mode === 'deboss-backed') {
              const floor = (prev.floorMaterial && prev.floorMaterial !== f.material)
                ? prev.floorMaterial
                : materials.find(m => m.id !== f.material)?.id
              f.relief = {
                mode, depth: prev.depth ?? 0.4,
                ...(floor ? { floorMaterial: floor } : {}),
                floorThickness: prev.floorThickness ?? 0.4,
              }
            } else { // deboss | flush
              f.relief = { mode, depth: prev.depth ?? 0.4 }
            }
          })} />
      </Row>
      {isBack && relief.mode === 'emboss' && (
        <div style={{ fontSize: 11, color: '#f85149', padding: '2px 0' }}>
          Emboss is not printable on the bed-facing face — pick deboss, cut or flush.
        </div>
      )}
      {relief.mode === 'emboss' && (
        <Row label="Height (mm)"><NumInput value={relief.height ?? 0.4} step={0.1} onCommit={v => edit(f => { f.relief.height = v })} /></Row>
      )}
      {(relief.mode === 'deboss' || relief.mode === 'deboss-backed') && (
        <Row label="Depth (mm)"><NumInput value={relief.depth ?? 0.4} step={0.1} onCommit={v => edit(f => { f.relief.depth = v })} /></Row>
      )}
      {relief.mode === 'deboss' && (
        <Row label="Background">
          <MaterialSelect materials={materials.filter(m => m.id !== feature.material)}
            value={''} allowEmpty emptyLabel="None (empty cavity)"
            onCommit={v => edit(f => {
              // A background color turns the cavity into deboss-backed:
              // same depth, floor of the chosen material.
              if (!v) return
              const depth = f.relief.depth ?? 0.4
              f.relief = {
                mode: 'deboss-backed', depth,
                floorMaterial: v,
                floorThickness: Math.min(0.2, depth / 2),
              }
            })} />
        </Row>
      )}
      {relief.mode === 'deboss-backed' && (
        <>
          <Row label="Floor material">
            <MaterialSelect materials={materials.filter(m => m.id !== feature.material)}
              value={relief.floorMaterial ?? ''} allowEmpty emptyLabel="None → plain deboss"
              onCommit={v => edit(f => {
                if (v) { f.relief.floorMaterial = v; return }
                f.relief = { mode: 'deboss', depth: f.relief.depth ?? 0.4 }
              })} />
          </Row>
          <Row label="Floor thickness"><NumInput value={relief.floorThickness ?? 0.4} step={0.1} onCommit={v => edit(f => { f.relief.floorThickness = v })} /></Row>
        </>
      )}
    </Section>
  )
}

// ── Backing ──────────────────────────────────────────────────────────

const BackingEditor: React.FC<{ feature: Feature; materials: Material[]; edit: EditFn }> = ({ feature, materials, edit }) => {
  const mode = feature.backing?.mode ?? 'auto'
  return (
    <Section title="Backing">
      <Row label="Mode">
        <Select value={mode} options={[['auto', 'Auto'], ['on', 'Always on'], ['off', 'Off']]}
          onCommit={v => edit(f => {
            if (v === 'auto') delete f.backing
            else f.backing = { ...(f.backing ?? {}), mode: v as 'on' | 'off' }
          })} />
      </Row>
      {mode !== 'off' && (
        <>
          <Row label="Shape">
            <Select value={feature.backing?.shape ?? 'rect'} options={[['rect', 'Rectangle'], ['circle', 'Circle']]}
              onCommit={v => edit(f => {
                if (!f.backing) f.backing = { mode }
                if (v === 'circle') f.backing.shape = 'circle'; else delete f.backing.shape
              })} />
          </Row>
          <Row label="Thickness">
            <NumInput value={feature.backing?.thickness ?? 0} step={0.1} placeholder="0 = auto"
              onCommit={v => edit(f => {
                if (!f.backing) f.backing = { mode }
                if (v > 0) f.backing.thickness = v; else delete f.backing.thickness
              })} />
          </Row>
          <Row label="Material">
            <MaterialSelect materials={materials} value={feature.backing?.material ?? ''} allowEmpty emptyLabel="Base (default)"
              onCommit={v => edit(f => {
                if (!f.backing) f.backing = { mode }
                if (v) f.backing.material = v; else delete f.backing.material
              })} />
          </Row>
          <Row label="Padding (mm)">
            <NumInput value={feature.backing?.padding ?? 0} step={0.5} placeholder="QR: quiet zone · resto: 1.5"
              onCommit={v => edit(f => {
                if (!f.backing) f.backing = { mode }
                if (v > 0) f.backing.padding = v; else delete f.backing.padding
              })} />
          </Row>
        </>
      )}
      <div style={{ fontSize: 11, color: '#484f58', padding: '2px 0' }}>
        Adds a solid pad so the feature isn't left floating over a lattice base.
        Thickness auto: full column over lattice · 0.6 mm plate on a solid base.
      </div>
    </Section>
  )
}

// ── text-block ───────────────────────────────────────────────────────

const TextBlockEditor: React.FC<{ feature: TextBlockFeature; edit: EditFn }> = ({ feature, edit }) => (
  <>
    <Section title="Text">
      <Row label="Lines" vertical>
        <TextArea value={feature.lines.join('\n')} rows={3}
          onCommit={v => edit<TextBlockFeature>(f => { f.lines = v.split('\n') })} />
      </Row>
      <Row label="Align">
        <Select value={feature.align ?? 'left'} options={[['left', 'Left'], ['center', 'Center'], ['right', 'Right']]}
          onCommit={v => edit<TextBlockFeature>(f => { f.align = v as TextBlockFeature['align'] })} />
      </Row>
      <Row label="Line height"><NumInput value={feature.lineHeight ?? 1.2} step={0.05} onCommit={v => edit<TextBlockFeature>(f => { f.lineHeight = v })} /></Row>
    </Section>
    <FontEditor feature={feature} edit={edit} weight minSize={MIN_TEXT_SIZE_MM} />
  </>
)

// Manufacturing floor for text-block size: below this the printed strokes fall
// under the nozzle and the glyphs don't come out. Enforced as the Size field's
// minimum (and the starter defaults sit at/above it).
const MIN_TEXT_SIZE_MM = 6

const FontEditor: React.FC<{ feature: TextBlockFeature | TextPatternFeature; edit: EditFn; weight?: boolean; minSize?: number }> = ({ feature, edit, weight, minSize }) => {
  const fonts = useFonts()
  const current = feature.font.family
  const isVariable = fonts.find(f => f.family === current)?.variable ?? false
  // Always include the current family so a font the Core doesn't have still
  // shows (flagged), rather than silently vanishing from the dropdown.
  const known = fonts.some(f => f.family === current)
  const options: [string, string][] = [
    ...(known ? [] : [[current, `${current} (not installed)`] as [string, string]]),
    ...fonts.map(f => [f.family, f.variable ? `${f.family} · var` : f.family] as [string, string]),
  ]
  return (
  <Section title="Font">
    <Row label="Family">
      {fonts.length > 0
        ? <Select value={current} options={options}
            onCommit={v => edit<TextBlockFeature | TextPatternFeature>(f => { f.font.family = v })} />
        : <TextInput value={current}
            onCommit={v => edit<TextBlockFeature | TextPatternFeature>(f => { f.font.family = v })} />}
    </Row>
    <Row label="Size (mm)"><NumInput value={feature.font.size} step={0.5} min={minSize} onCommit={v => edit<TextBlockFeature | TextPatternFeature>(f => { f.font.size = v })} /></Row>
    {weight && (
      <Row label="Weight">
        <NumInput value={feature.font.weight ?? 400} step={50} min={100} max={900}
          onCommit={v => edit<TextBlockFeature>(f => { f.font.weight = v })} />
      </Row>
    )}
    {weight && !isVariable && current && known && (
      <div style={{ fontSize: 10, color: '#8b949e', padding: '0 0 2px' }}>
        {(() => {
          const w = fonts.find(f => f.family === current)?.weights ?? []
          return w.length > 1
            ? `Pesos disponibles: ${w.join(', ')} (se usa el más cercano)`
            : 'Esta familia tiene un solo peso instalado'
        })()}
      </div>
    )}
    <Row label="Italic">
      <input type="checkbox" checked={feature.font.italic === true}
        onChange={e => edit<TextBlockFeature | TextPatternFeature>(f => { f.font.italic = e.target.checked })} />
    </Row>
    <Row label="Variable axes" vertical>
      <NumberMapEditor
        value={feature.font.axes ?? {}}
        keyPlaceholder="wght"
        onCommit={axes => edit<TextBlockFeature | TextPatternFeature>(f => {
          if (Object.keys(axes).length) f.font.axes = axes
          else delete f.font.axes
        })}
      />
    </Row>
  </Section>
  )
}

// ── text-pattern ─────────────────────────────────────────────────────

const TextPatternEditor: React.FC<{ feature: TextPatternFeature; edit: EditFn }> = ({ feature, edit }) => (
  <>
    <Section title="Text pattern">
      <Row label="Text"><TextInput value={feature.text} onCommit={v => edit<TextPatternFeature>(f => { f.text = v })} /></Row>
      <Row label="Gap X (mm)"><NumInput value={feature.spacing} step={0.5} min={0.1} onCommit={v => edit<TextPatternFeature>(f => { f.spacing = v })} /></Row>
      <Row label="Gap Y (mm)">
        <NumInput value={feature.spacingY ?? feature.spacing} step={0.5} min={0.1}
          onCommit={v => edit<TextPatternFeature>(f => {
            if (v === f.spacing) delete f.spacingY
            else f.spacingY = v
          })} />
      </Row>
      <Row label="Angle"><NumInput value={feature.angle ?? 0} step={1} onCommit={v => edit<TextPatternFeature>(f => { f.angle = v })} /></Row>
      <div style={{ fontSize: 10, color: '#484f58', padding: '2px 0' }}>
        Gap = separación entre repeticiones — se mantiene al cambiar el texto.
      </div>
    </Section>
    <FontEditor feature={feature} edit={edit} weight />
  </>
)

// ── pattern ──────────────────────────────────────────────────────────

const PatternEditor: React.FC<{ feature: PatternFeature; edit: EditFn }> = ({ feature, edit }) => {
  const handleSvgUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    void file.text().then(text => {
      useDocumentStore.getState().applyEdit(d => {
        applySvgToFeature(d, feature.id, text)
      })
    })
    e.target.value = ''
  }
  return (
  <Section title="Pattern">
    <Row label="Type">
      <Select value={feature.patternType} options={[['dots', 'Dots'], ['lines', 'Lines'], ['grid', 'Grid'], ['hex', 'Hex'], ['svg', 'SVG motif']]}
        onCommit={v => edit<PatternFeature>(f => { f.patternType = v as PatternFeature['patternType'] })} />
    </Row>
    {feature.patternType === 'svg' && (
      <>
        <Row label="Library" vertical>
          <IconPicker featureId={feature.id} />
        </Row>
        <Row label="Upload .svg">
          <input type="file" accept=".svg,image/svg+xml" onChange={handleSvgUpload} style={{ fontSize: 11, color: '#8b949e', maxWidth: 160 }} />
        </Row>
        {feature.svgInline && (
          <Row label="Motif"><ReadOnly value={`${Object.keys(feature.colorMap ?? {}).length || 1} color(s), ${feature.svgInline.length} chars`} /></Row>
        )}
      </>
    )}
    <Row label={feature.patternType === 'svg' ? 'Gap X (mm)' : 'Spacing (mm)'}><NumInput value={feature.spacing} step={0.5} min={0.1} onCommit={v => edit<PatternFeature>(f => { f.spacing = v })} /></Row>
    {feature.patternType === 'svg' && (
      <Row label="Gap Y (mm)">
        <NumInput value={feature.spacingY ?? feature.spacing} step={0.5} min={0.1}
          onCommit={v => edit<PatternFeature>(f => {
            if (v === f.spacing) delete f.spacingY
            else f.spacingY = v
          })} />
      </Row>
    )}
    <Row label={feature.patternType === 'svg' ? 'Motif size (mm)' : 'Element size'}><NumInput value={feature.elementSize ?? 1} step={0.1} min={0.1} onCommit={v => edit<PatternFeature>(f => { f.elementSize = v })} /></Row>
    <Row label="Angle"><NumInput value={feature.angle ?? 0} step={1} onCommit={v => edit<PatternFeature>(f => { f.angle = v })} /></Row>
    <Row label="Region">
      <Select value={feature.region ?? 'bounds'} options={[['face', 'Whole face'], ['bounds', 'Bounds']]}
        onCommit={v => edit<PatternFeature>(f => { f.region = v as PatternFeature['region'] })} />
    </Row>
    {(feature.region ?? 'bounds') === 'bounds' && (
      <>
        <Row label="Width (mm)"><NumInput value={feature.width ?? 20} step={1} onCommit={v => edit<PatternFeature>(f => { f.width = v })} /></Row>
        <Row label="Height (mm)"><NumInput value={feature.height ?? 20} step={1} onCommit={v => edit<PatternFeature>(f => { f.height = v })} /></Row>
      </>
    )}
  </Section>
  )
}

// ── qr ───────────────────────────────────────────────────────────────

const QREditor: React.FC<{ feature: QRFeature; edit: EditFn }> = ({ feature, edit }) => {
  const qrType = feature.qrType as QRType
  const defs = FIELD_DEFS[qrType] ?? []
  return (
    <Section title="QR Code">
      <Row label="Type">
        <Select value={qrType} options={(Object.keys(QR_TYPE_LABELS) as QRType[]).map(t => [t, QR_TYPE_LABELS[t]])}
          onCommit={v => edit<QRFeature>(f => { f.qrType = v as QRFeature['qrType'] })} />
      </Row>
      {defs.map(def => (
        <Row key={def.key} label={def.label} vertical={def.type === 'textarea'}>
          {def.type === 'select' ? (
            <Select value={feature.fields[def.key] ?? def.options?.[0] ?? ''}
              options={(def.options ?? []).map(o => [o, o])}
              onCommit={v => edit<QRFeature>(f => { f.fields[def.key] = v })} />
          ) : def.type === 'textarea' ? (
            <TextArea value={feature.fields[def.key] ?? ''} rows={3} placeholder={def.placeholder}
              onCommit={v => edit<QRFeature>(f => { f.fields[def.key] = v })} />
          ) : (
            <TextInput value={feature.fields[def.key] ?? ''} placeholder={def.placeholder}
              onCommit={v => edit<QRFeature>(f => { f.fields[def.key] = v })} />
          )}
        </Row>
      ))}
      <Row label="Size (mm)"><NumInput value={feature.size} step={1} onCommit={v => edit<QRFeature>(f => { f.size = v })} /></Row>
      <Row label="Error corr.">
        <Select value={feature.errorCorrection ?? 'M'} options={[['L', 'L (7%)'], ['M', 'M (15%)'], ['Q', 'Q (25%)'], ['H', 'H (30%)']]}
          onCommit={v => edit<QRFeature>(f => { f.errorCorrection = v as QRFeature['errorCorrection'] })} />
      </Row>
      <Row label="Quiet zone"><NumInput value={feature.quietZone ?? 2} step={1} onCommit={v => edit<QRFeature>(f => { f.quietZone = v })} /></Row>
    </Section>
  )
}

// ── icon library picker ──────────────────────────────────────────────

// Grid of built-in glyphs (social + general). Clicking one stores it as
// the feature's inline SVG through the same path as an uploaded file.
const IconPicker: React.FC<{ featureId: string }> = ({ featureId }) => {
  const apply = (icon: LibraryIcon) => {
    useDocumentStore.getState().applyEdit(d => {
      applySvgToFeature(d, featureId, libraryIconSvg(icon))
    })
  }
  return (
    <div>
      {(Object.keys(ICON_CATEGORY_LABELS) as IconCategory[]).map(cat => (
        <div key={cat} style={{ marginBottom: 4 }}>
          <div style={{ fontSize: 10, color: '#484f58', padding: '2px 0' }}>{ICON_CATEGORY_LABELS[cat]}</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {ICON_LIBRARY.filter(i => i.category === cat).map(icon => (
              <button key={icon.id} title={icon.name} onClick={() => apply(icon)}
                style={{
                  width: 26, height: 26, padding: 4, cursor: 'pointer',
                  background: '#161b22', border: '1px solid #30363d', borderRadius: 4,
                  color: '#8b949e', display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
                onMouseEnter={e => { e.currentTarget.style.color = '#c9d1d9'; e.currentTarget.style.borderColor = '#8b949e' }}
                onMouseLeave={e => { e.currentTarget.style.color = '#8b949e'; e.currentTarget.style.borderColor = '#30363d' }}>
                <svg viewBox={`0 0 ${icon.vb ?? 24} ${icon.vb ?? 24}`} width="16" height="16">
                  <path d={icon.d} fill="currentColor" />
                </svg>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── icon ─────────────────────────────────────────────────────────────

const IconEditor: React.FC<{ feature: IconFeature; materials: Material[]; edit: EditFn }> = ({ feature, materials, edit }) => {
  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    void file.text().then(text => {
      // Doc-level edit: stores the SVG inline AND creates one material per
      // fill color (colorMap), so multicolor art prints multi-material.
      useDocumentStore.getState().applyEdit(d => {
        applySvgToFeature(d, feature.id, text)
      })
    })
    e.target.value = ''
  }
  return (
    <Section title="Icon">
      <Row label="Width (mm)"><NumInput value={feature.width} step={0.5} onCommit={v => edit<IconFeature>(f => { f.width = v })} /></Row>
      <Row label="Height (mm)">
        <NumInput value={feature.height ?? feature.width} step={0.5} onCommit={v => edit<IconFeature>(f => { f.height = v })} />
      </Row>
      <Row label="Library" vertical>
        <IconPicker featureId={feature.id} />
      </Row>
      <Row label="SVG asset">
        <TextInput value={feature.svgAsset ?? ''} placeholder="asset key"
          onCommit={v => edit<IconFeature>(f => { if (v) { f.svgAsset = v; delete f.svgInline } else delete f.svgAsset })} />
      </Row>
      <Row label="Upload .svg">
        <input type="file" accept=".svg,image/svg+xml" onChange={handleUpload} style={{ fontSize: 11, color: '#8b949e', maxWidth: 160 }} />
      </Row>
      {feature.svgInline && (
        <Row label="Inline SVG"><ReadOnly value={`${feature.svgInline.length} chars`} /></Row>
      )}
      <Row label="Color map" vertical>
        <ColorMapEditor
          value={feature.colorMap ?? {}}
          materials={materials}
          onCommit={map => edit<IconFeature>(f => {
            if (Object.keys(map).length) f.colorMap = map
            else delete f.colorMap
          })}
        />
      </Row>
    </Section>
  )
}

// ── shape ────────────────────────────────────────────────────────────

const SHAPE_TYPES: Array<[string, string]> = [
  ['rect', 'Rectangle'], ['rounded-rect', 'Rounded rect'], ['circle', 'Circle'],
  ['ring', 'Ring'], ['frame', 'Frame'], ['corner-marks', 'Corner marks'], ['path', 'SVG path'],
]

const ShapeEditor: React.FC<{ feature: ShapeFeature; edit: EditFn }> = ({ feature, edit }) => {
  const t = feature.shapeType
  const num = (label: string, value: number, key: 'width' | 'height' | 'radius' | 'diameter' | 'strokeWidth' | 'inset' | 'length', step = 0.5) => (
    <Row label={label}>
      <NumInput value={value} step={step} onCommit={v => edit<ShapeFeature>(f => { f[key] = v })} />
    </Row>
  )
  return (
    <Section title="Shape">
      <Row label="Type">
        <Select value={t} options={SHAPE_TYPES}
          onCommit={v => edit<ShapeFeature>(f => { f.shapeType = v as ShapeFeature['shapeType'] })} />
      </Row>
      {(t === 'rect' || t === 'rounded-rect' || t === 'frame' || t === 'corner-marks') && (
        <>
          {num('Width (mm)', feature.width ?? 20, 'width')}
          {num('Height (mm)', feature.height ?? 10, 'height')}
        </>
      )}
      {(t === 'rounded-rect' || t === 'frame') && num('Radius (mm)', feature.radius ?? 2, 'radius')}
      {(t === 'circle' || t === 'ring') && num('Diameter (mm)', feature.diameter ?? 10, 'diameter')}
      {(t === 'ring' || t === 'frame') && num('Stroke width', feature.strokeWidth ?? 1.5, 'strokeWidth', 0.1)}
      {(t === 'frame' || t === 'corner-marks') && num('Inset (mm)', feature.inset ?? 0, 'inset', 0.5)}
      {t === 'corner-marks' && num('Length (mm)', feature.length ?? 5, 'length')}
      {t === 'path' && (
        <Row label="SVG path" vertical>
          <TextArea value={feature.svgPath ?? ''} rows={3} placeholder="M 0 0 L 10 0 ..."
            onCommit={v => edit<ShapeFeature>(f => { f.svgPath = v })} />
        </Row>
      )}
    </Section>
  )
}

// ── hole ─────────────────────────────────────────────────────────────

const HoleEditor: React.FC<{ feature: HoleFeature; edit: EditFn }> = ({ feature, edit }) => {
  const t = feature.holeType
  return (
    <Section title="Hole">
      <div style={{ fontSize: 11, color: '#8b949e', padding: '2px 0 6px' }}>
        Through-cut across the whole thickness. Enable the tab to add material
        around the hole — that lets it sit on (or past) the card edge.
      </div>
      <Row label="Type">
        <Select value={t} options={[['circle', 'Circle (keyring)'], ['slot', 'Slot (lanyard)']]}
          onCommit={v => edit<HoleFeature>(f => {
            f.holeType = v as HoleFeature['holeType']
            if (f.holeType === 'circle') {
              f.diameter = f.diameter ?? 5
              delete f.width; delete f.height
            } else {
              f.width = f.width ?? 14
              f.height = f.height ?? 5
              delete f.diameter
            }
          })} />
      </Row>
      {t === 'circle' && (
        <Row label="Diameter (mm)">
          <NumInput value={feature.diameter ?? 5} step={0.5} onCommit={v => edit<HoleFeature>(f => { f.diameter = v })} />
        </Row>
      )}
      {t === 'slot' && (
        <>
          <Row label="Width (mm)">
            <NumInput value={feature.width ?? 14} step={0.5} onCommit={v => edit<HoleFeature>(f => { f.width = v })} />
          </Row>
          <Row label="Height (mm)">
            <NumInput value={feature.height ?? 5} step={0.5} onCommit={v => edit<HoleFeature>(f => { f.height = v })} />
          </Row>
        </>
      )}
      <Row label="Tab (add material)">
        <input type="checkbox" checked={feature.tab === true}
          onChange={e => edit<HoleFeature>(f => { if (e.target.checked) f.tab = true; else { delete f.tab; delete f.tabMargin } })} />
      </Row>
      {feature.tab && (
        <Row label="Tab margin (mm)">
          <NumInput value={feature.tabMargin ?? 3} step={0.5} onCommit={v => edit<HoleFeature>(f => { f.tabMargin = v })} />
        </Row>
      )}
    </Section>
  )
}

// ── Document inspector (nothing selected) ────────────────────────────

// ── Corner radii (uniform + per-corner) ──────────────────────────────

type RoundedRect = Extract<Outline, { type: 'rounded-rect' }>

const CornerRadiusEditor: React.FC<{ outline: RoundedRect; applyEdit: ApplyEdit }> = ({ outline, applyEdit }) => {
  const corners = outline.corners
  const perCorner = corners != null
  const eff = (k: 'tl' | 'tr' | 'br' | 'bl') => corners?.[k] ?? outline.radius

  const setCorner = (k: 'tl' | 'tr' | 'br' | 'bl', v: number) => applyEdit(d => {
    const o = d.object.outline
    if (o.type !== 'rounded-rect') return
    // Materialise all four from the effective values, then set the one edited.
    const base = { tl: eff('tl'), tr: eff('tr'), br: eff('br'), bl: eff('bl') }
    base[k] = v
    o.corners = base
  })

  const cornerInput = (k: 'tl' | 'tr' | 'br' | 'bl') => (
    <NumInput value={eff(k)} step={0.5} onCommit={v => setCorner(k, v)} />
  )

  return (
    <>
      <Row label="Radius (mm)">
        <NumInput value={outline.radius} step={0.5} onCommit={v => applyEdit(d => {
          if (d.object.outline.type === 'rounded-rect') d.object.outline.radius = v
        })} />
      </Row>
      <Row label="Per-corner">
        <input type="checkbox" checked={perCorner}
          onChange={e => applyEdit(d => {
            const o = d.object.outline
            if (o.type !== 'rounded-rect') return
            if (e.target.checked) o.corners = { tl: o.radius, tr: o.radius, br: o.radius, bl: o.radius }
            else delete o.corners
          })} />
      </Row>
      {perCorner && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 6 }}>
          <div style={{ display: 'flex', gap: 4 }}>{cornerInput('tl')}{cornerInput('tr')}</div>
          <div style={{ display: 'flex', gap: 4 }}>{cornerInput('bl')}{cornerInput('br')}</div>
          <button
            onClick={() => applyEdit(d => {
              const o = d.object.outline
              if (o.type === 'rounded-rect') delete o.corners
            })}
            style={{ alignSelf: 'flex-start', background: '#21262d', color: '#8b949e', border: '1px solid #30363d', borderRadius: 4, padding: '2px 8px', fontSize: 11, cursor: 'pointer' }}
          >Reset to uniform</button>
        </div>
      )}
    </>
  )
}

// ── Fill (solid / lattice) ───────────────────────────────────────────

const LATTICE_DEFAULTS: Extract<Fill, { type: 'lattice' }> = { type: 'lattice', pattern: 'grid', spacing: 5, lineWidth: 1.2, border: 2.5 }

const FillEditor: React.FC<{ fill: Fill | undefined; applyEdit: ApplyEdit }> = ({ fill, applyEdit }) => {
  const mode = fill?.type === 'lattice' ? 'lattice' : 'solid'
  const lat = fill?.type === 'lattice' ? fill : LATTICE_DEFAULTS
  const editLattice = (fn: (f: Extract<Fill, { type: 'lattice' }>) => void) => applyEdit(d => {
    if (d.object.fill?.type !== 'lattice') return
    fn(d.object.fill)
  })
  return (
    <Section title="Fill">
      <Row label="Mode">
        <Select value={mode} options={[['solid', 'Solid'], ['lattice', 'Lattice']]}
          onCommit={v => applyEdit(d => {
            if (v === 'lattice') d.object.fill = { ...LATTICE_DEFAULTS }
            else delete d.object.fill
          })} />
      </Row>
      {mode === 'lattice' && (
        <>
          <Row label="Pattern">
            <Select value={lat.pattern} options={[['dots', 'Dots'], ['lines', 'Lines'], ['grid', 'Grid'], ['hex', 'Hex']]}
              onCommit={v => editLattice(f => { f.pattern = v as typeof f.pattern })} />
          </Row>
          <Row label="Spacing (mm)"><NumInput value={lat.spacing} step={0.5} onCommit={v => editLattice(f => { f.spacing = v })} /></Row>
          <Row label="Line width"><NumInput value={lat.lineWidth ?? 1.2} step={0.1} onCommit={v => editLattice(f => { f.lineWidth = v })} /></Row>
          <Row label="Border (mm)"><NumInput value={lat.border ?? 2.5} step={0.5} onCommit={v => editLattice(f => { f.border = v })} /></Row>
        </>
      )}
    </Section>
  )
}

// ── Manufacturing (nozzle / process / layer height) ──────────────────

const PROCESS_OPTIONS: Array<[string, string]> = [
  ['fdm', 'FDM'], ['sla', 'SLA'], ['laser', 'Laser'], ['cnc', 'CNC'],
]

const ManufacturingEditor: React.FC<{ doc: DocumentV2; applyEdit: ApplyEdit }> = ({ doc, applyEdit }) => {
  const mfg = doc.manufacturing
  const nozzle = mfg?.nozzle ?? 0.4
  const process = mfg?.process ?? 'fdm'
  const layerHeight = mfg?.layerHeight ?? 0.2

  // Mutate doc.manufacturing, creating it if missing.
  const editMfg = (fn: (m: NonNullable<DocumentV2['manufacturing']>) => void) => applyEdit(d => {
    if (!d.manufacturing) d.manufacturing = {}
    fn(d.manufacturing)
  })

  return (
    <Section title="Manufacturing">
      <Row label="Nozzle (mm)">
        <NumInput value={nozzle} step={0.05} onCommit={v => editMfg(m => { m.nozzle = v })} />
      </Row>
      <Row label="Process">
        <Select value={process} options={PROCESS_OPTIONS}
          onCommit={v => editMfg(m => { m.process = v as NonNullable<DocumentV2['manufacturing']>['process'] })} />
      </Row>
      <Row label="Layer height">
        <NumInput value={layerHeight} step={0.02} onCommit={v => editMfg(m => { m.layerHeight = v })} />
      </Row>
      <div style={{ fontSize: 11, color: '#484f58', padding: '2px 0' }}>
        Min detail ≈ nozzle — drives the detail-size alerts.
      </div>
    </Section>
  )
}

// Width/height helper — circle is width=height=diameter.
const outlineDims = (o: Outline): { width: number; height: number } =>
  o.type === 'circle' ? { width: o.diameter, height: o.diameter } : { width: o.width, height: o.height }

// The base material is the one tagged role 'base' (else the first) — same rule
// the Core uses to pick which material bodies the card.
const baseMaterialId = (doc: DocumentV2): string =>
  doc.materials.find(m => m.role === 'base')?.id ?? doc.materials[0]?.id ?? ''

const DocumentInspector: React.FC<{ doc: DocumentV2; applyEdit: ApplyEdit }> = ({ doc, applyEdit }) => {
  const outline = doc.object.outline
  const dims = outlineDims(outline)
  const fill = doc.object.fill
  return (
    <div>
      <Section title="Document">
        <Row label="Name">
          <TextInput value={doc.meta.name} onCommit={v => applyEdit(d => { d.meta.name = v })} />
        </Row>
        <Row label="ID"><ReadOnly value={doc.meta.id} /></Row>
      </Section>

      <Section title="Outline">
        <Row label="Shape">
          <Select value={outline.type} options={[['rect', 'Rectangle'], ['rounded-rect', 'Rounded rect'], ['circle', 'Circle'], ['path', 'SVG path']]}
            onCommit={v => applyEdit(d => {
              const o = d.object.outline
              const { width, height } = outlineDims(o)
              if (v === 'rect') d.object.outline = { type: 'rect', width, height }
              else if (v === 'rounded-rect') d.object.outline = { type: 'rounded-rect', width, height, radius: o.type === 'rounded-rect' ? o.radius : 4 }
              else if (v === 'circle') d.object.outline = { type: 'circle', diameter: o.type === 'circle' ? o.diameter : (Math.min(width, height) || 40) }
              else d.object.outline = { type: 'path', svgPath: o.type === 'path' ? o.svgPath : '', width, height }
            })} />
        </Row>

        {outline.type === 'circle' ? (
          <Row label="Diameter (mm)">
            <NumInput value={outline.diameter} step={1} onCommit={v => applyEdit(d => {
              if (d.object.outline.type === 'circle') d.object.outline.diameter = v
            })} />
          </Row>
        ) : (
          <>
            <Row label="Width (mm)"><NumInput value={dims.width} step={1} onCommit={v => applyEdit(d => {
              const o = d.object.outline
              if (o.type !== 'circle') o.width = v
            })} /></Row>
            <Row label="Height (mm)"><NumInput value={dims.height} step={1} onCommit={v => applyEdit(d => {
              const o = d.object.outline
              if (o.type !== 'circle') o.height = v
            })} /></Row>
          </>
        )}

        {outline.type === 'rounded-rect' && <CornerRadiusEditor outline={outline} applyEdit={applyEdit} />}

        {outline.type === 'path' && (
          <>
            <Row label="Upload .svg">
              <input type="file" accept=".svg,image/svg+xml" style={{ fontSize: 11, color: '#8b949e', maxWidth: 160 }}
                onChange={e => {
                  const file = e.target.files?.[0]
                  if (!file) return
                  void file.text().then(text => {
                    const dPath = extractSvgPathD(text)
                    if (dPath) applyEdit(d => {
                      if (d.object.outline.type === 'path') d.object.outline.svgPath = dPath
                    })
                  })
                  e.target.value = ''
                }} />
            </Row>
            <Row label="SVG path" vertical>
              <TextArea value={outline.svgPath} rows={3} onCommit={v => applyEdit(d => {
                if (d.object.outline.type === 'path') d.object.outline.svgPath = v
              })} />
            </Row>
          </>
        )}
      </Section>

      <Section title="Base">
        <Row label="Material">
          <MaterialSelect
            materials={doc.materials}
            value={baseMaterialId(doc)}
            onCommit={v => applyEdit(d => {
              // Exactly one material carries the base role: promote the pick,
              // demote whoever held it (the compiler bodies the card in it).
              for (const m of d.materials) {
                if (m.id === v) m.role = 'base'
                else if (m.role === 'base') delete m.role
              }
            })}
          />
        </Row>
        <Row label="Thickness"><NumInput value={doc.object.thickness} step={0.1} onCommit={v => applyEdit(d => { d.object.thickness = v })} /></Row>
      </Section>

      <FillEditor fill={fill} applyEdit={applyEdit} />

      <ManufacturingEditor doc={doc} applyEdit={applyEdit} />

      <Section title="Variables">
        <StringMapEditor
          value={doc.variables ?? {}}
          keyPlaceholder="name"
          valuePlaceholder="value"
          onCommit={vars => applyEdit(d => {
            if (Object.keys(vars).length) d.variables = vars
            else delete d.variables
          })}
        />
      </Section>
    </div>
  )
}

// ── Key/value editors ────────────────────────────────────────────────

const kvInputStyle: React.CSSProperties = {
  flex: 1, minWidth: 0, background: '#0d1117', color: '#c9d1d9',
  border: '1px solid #30363d', borderRadius: 4, padding: '3px 6px', fontSize: 11,
}

const StringMapEditor: React.FC<{
  value: Record<string, string>
  keyPlaceholder?: string
  valuePlaceholder?: string
  onCommit: (v: Record<string, string>) => void
}> = ({ value, keyPlaceholder, valuePlaceholder, onCommit }) => {
  const entries = Object.entries(value)
  const rename = (oldKey: string, newKey: string) => {
    if (!newKey || newKey === oldKey || newKey in value) return
    const next: Record<string, string> = {}
    for (const [k, v] of entries) next[k === oldKey ? newKey : k] = v
    onCommit(next)
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, width: '100%' }}>
      {entries.map(([k, v]) => (
        <div key={k} style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          <CommitInput style={kvInputStyle} value={k} placeholder={keyPlaceholder} onCommit={nk => rename(k, nk)} />
          <CommitInput style={kvInputStyle} value={v} placeholder={valuePlaceholder} onCommit={nv => onCommit({ ...value, [k]: nv })} />
          <IconBtn title="Remove" onClick={() => { const next = { ...value }; delete next[k]; onCommit(next) }}>✕</IconBtn>
        </div>
      ))}
      <button
        onClick={() => {
          let key = 'key'
          let i = 1
          while (key in value) key = `key${++i}`
          onCommit({ ...value, [key]: '' })
        }}
        style={{ alignSelf: 'flex-start', background: '#21262d', color: '#8b949e', border: '1px solid #30363d', borderRadius: 4, padding: '2px 8px', fontSize: 11, cursor: 'pointer' }}
      >+ Add</button>
    </div>
  )
}

const NumberMapEditor: React.FC<{
  value: Record<string, number>
  keyPlaceholder?: string
  onCommit: (v: Record<string, number>) => void
}> = ({ value, keyPlaceholder, onCommit }) => {
  const asStrings = Object.fromEntries(Object.entries(value).map(([k, v]) => [k, String(v)]))
  return (
    <StringMapEditor
      value={asStrings}
      keyPlaceholder={keyPlaceholder}
      valuePlaceholder="400"
      onCommit={strs => {
        const next: Record<string, number> = {}
        for (const [k, v] of Object.entries(strs)) {
          const n = parseFloat(v)
          next[k] = Number.isNaN(n) ? 0 : n
        }
        onCommit(next)
      }}
    />
  )
}

const ColorMapEditor: React.FC<{
  value: Record<string, string>
  materials: Material[]
  onCommit: (v: Record<string, string>) => void
}> = ({ value, materials, onCommit }) => {
  const entries = Object.entries(value)
  const rename = (oldKey: string, newKey: string) => {
    if (!newKey || newKey === oldKey || newKey in value) return
    const next: Record<string, string> = {}
    for (const [k, v] of entries) next[k === oldKey ? newKey : k] = v
    onCommit(next)
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, width: '100%' }}>
      {entries.map(([hex, matId]) => (
        <div key={hex} style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          <span style={{ width: 12, height: 12, borderRadius: 2, background: hex, border: '1px solid #30363d', flexShrink: 0 }} />
          <CommitInput style={{ ...kvInputStyle, maxWidth: 76 }} value={hex} placeholder="#ffffff" onCommit={nk => rename(hex, nk)} />
          <select
            value={matId}
            onChange={e => onCommit({ ...value, [hex]: e.target.value })}
            style={{ ...kvInputStyle, cursor: 'pointer' }}
          >
            {materials.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
          <IconBtn title="Remove" onClick={() => { const next = { ...value }; delete next[hex]; onCommit(next) }}>✕</IconBtn>
        </div>
      ))}
      <button
        onClick={() => {
          let hex = '#ffffff'
          let i = 0
          while (hex in value) hex = `#fffff${(++i).toString(16)}`
          onCommit({ ...value, [hex]: materials[0]?.id ?? '' })
        }}
        style={{ alignSelf: 'flex-start', background: '#21262d', color: '#8b949e', border: '1px solid #30363d', borderRadius: 4, padding: '2px 8px', fontSize: 11, cursor: 'pointer' }}
      >+ Add mapping</button>
    </div>
  )
}

// ── Small controls ───────────────────────────────────────────────────

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div style={{ marginBottom: 14 }}>
    <div style={{
      fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.6,
      color: '#8b949e', borderBottom: '1px solid #21262d', paddingBottom: 4, marginBottom: 8,
    }}>{title}</div>
    {children}
  </div>
)

const Row: React.FC<{ label: string; vertical?: boolean; children: React.ReactNode }> = ({ label, vertical, children }) => (
  <div style={{
    display: 'flex', flexDirection: vertical ? 'column' : 'row',
    alignItems: vertical ? 'stretch' : 'center', gap: vertical ? 4 : 8, marginBottom: 6,
  }}>
    <span style={{ width: vertical ? 'auto' : 88, flexShrink: 0, color: '#8b949e', fontSize: 11 }}>{label}</span>
    {children}
  </div>
)

const inputStyle: React.CSSProperties = {
  flex: 1, minWidth: 0, width: '100%', background: '#0d1117', color: '#c9d1d9',
  border: '1px solid #30363d', borderRadius: 4, padding: '3px 6px', fontSize: 12,
}

const ReadOnly: React.FC<{ value: string }> = ({ value }) => (
  <span style={{ fontSize: 11, color: '#484f58', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{value}</span>
)

/** Text input that commits on blur/Enter (avoids clobbering while typing). */
const CommitInput: React.FC<{
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

const TextInput: React.FC<{ value: string; placeholder?: string; onCommit: (v: string) => void }> = (props) => (
  <CommitInput {...props} />
)

const TextArea: React.FC<{ value: string; rows?: number; placeholder?: string; onCommit: (v: string) => void }> = ({ value, rows, placeholder, onCommit }) => {
  const [local, setLocal] = React.useState(value)
  React.useEffect(() => setLocal(value), [value])
  return (
    <textarea
      style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }}
      rows={rows ?? 3}
      value={local}
      placeholder={placeholder}
      onChange={e => setLocal(e.target.value)}
      onBlur={() => { if (local !== value) onCommit(local) }}
    />
  )
}

const stepBtnStyle: React.CSSProperties = {
  width: 26, flexShrink: 0, background: '#21262d', color: '#c9d1d9',
  border: '1px solid #30363d', cursor: 'pointer', fontSize: 16, lineHeight: 1,
  padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', userSelect: 'none',
}

/** Numeric field as a [−][ value ][+] stepper. Buttons nudge by `step`
 *  (respecting min/max); the value stays editable by typing. Used everywhere
 *  a number is edited, so the whole inspector gets the same control. */
const NumInput: React.FC<{ value: number; step?: number; min?: number; max?: number; placeholder?: string; onCommit: (v: number) => void }> = ({ value, step = 1, min, max, placeholder, onCommit }) => {
  const clamp = (n: number) => Math.min(max ?? Infinity, Math.max(min ?? -Infinity, n))
  // Snap to the step's decimal precision so 0.1 + 0.2 doesn't drift to 0.3000004.
  const decimals = (String(step).split('.')[1] ?? '').length
  const snap = (n: number) => Number(n.toFixed(decimals))
  const bump = (dir: 1 | -1) => onCommit(snap(clamp(value + dir * step)))
  const atMin = min != null && value <= min
  const atMax = max != null && value >= max
  return (
    <div className="cf-num-stepper" style={{ display: 'flex', flex: 1, minWidth: 0, height: 26 }}>
      <button type="button" title={`−${step}`} aria-label="decrement" disabled={atMin} onClick={() => bump(-1)}
        style={{ ...stepBtnStyle, borderRadius: '4px 0 0 4px', borderRight: 'none' }}>−</button>
      <input
        type="number"
        style={{ ...inputStyle, flex: 1, width: 'auto', borderRadius: 0, textAlign: 'center', fontSize: 13, fontVariantNumeric: 'tabular-nums' }}
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

const Select: React.FC<{ value: string; options: Array<[string, string]>; onCommit: (v: string) => void }> = ({ value, options, onCommit }) => (
  <select value={value} onChange={e => onCommit(e.target.value)} style={{ ...inputStyle, cursor: 'pointer' }}>
    {options.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
  </select>
)

const MaterialSelect: React.FC<{ materials: Material[]; value: string; allowEmpty?: boolean; emptyLabel?: string; onCommit: (v: string) => void }> = ({ materials, value, allowEmpty, emptyLabel, onCommit }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1, minWidth: 0 }}>
    <span style={{
      width: 12, height: 12, borderRadius: 2, flexShrink: 0,
      background: materials.find(m => m.id === value)?.color ?? 'transparent',
      border: '1px solid #30363d',
    }} />
    <select value={value} onChange={e => onCommit(e.target.value)} style={{ ...inputStyle, cursor: 'pointer' }}>
      {allowEmpty && <option value="">{emptyLabel ?? '(none)'}</option>}
      {materials.map(m => <option key={m.id} value={m.id}>{m.name} ({m.id})</option>)}
    </select>
  </div>
)

const ActionBtn: React.FC<{ title: string; onClick: () => void; children: React.ReactNode }> = ({ title, onClick, children }) => (
  <button title={title} onClick={onClick} style={{
    background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d', borderRadius: 4,
    padding: '2px 8px', fontSize: 12, cursor: 'pointer', lineHeight: '16px',
  }}>{children}</button>
)

const IconBtn: React.FC<{ title: string; onClick: () => void; children: React.ReactNode }> = ({ title, onClick, children }) => (
  <button title={title} onClick={onClick} style={{
    background: 'transparent', color: '#8b949e', border: 'none', cursor: 'pointer', fontSize: 11, padding: '0 2px', flexShrink: 0,
  }}>{children}</button>
)
