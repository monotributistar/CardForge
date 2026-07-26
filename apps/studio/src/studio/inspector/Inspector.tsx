// Inspector — per-type property editors bound to the selected feature.
// When nothing is selected, shows the document properties instead.
// Every change goes through DocumentStore.applyEdit (undoable).

import React from 'react'
import type {
  DocumentV2, Feature, Material, ReliefMode, Outline, Fill,
  TextBlockFeature, TextPatternFeature, PatternFeature, QRFeature, IconFeature, ShapeFeature, HoleFeature, PocketFeature,
} from '../../types/cardforge'
import { DEFAULT_POCKET_CLEARANCE, DEFAULT_POCKET_DEPTH_CLEARANCE } from '../../types/cardforge'
import { useDocumentStore, getActiveTab, findFeature, removeFeatures } from '../../state/DocumentStore'
import { FIELD_DEFS, QR_TYPE_LABELS, type QRType } from '../services/QRFields'
import { applySvgOutline, applySvgToFeature, clampColorDepth, DEFAULT_COLOR_DEPTH } from '../services/SvgImport'
import { ICON_LIBRARY, ICON_CATEGORY_LABELS, libraryIconSvg, type IconCategory, type LibraryIcon } from '../services/IconLibrary'
import { listFonts, type FontInfo } from '../core/CoreClient'
import {
  Section, Row, inputStyle, ReadOnly, CommitInput, TextInput, TextArea, NumInput,
  Select, MaterialSelect, ActionBtn,
} from '../../components/ui'

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
        <Row label="Name" hint="Display name — shown in the layers list and exported part names">
          <TextInput value={feature.name ?? ''} placeholder={feature.id}
            onCommit={v => edit(f => { if (v) f.name = v; else delete f.name })} />
        </Row>
        <Row label="X (mm)" hint="Horizontal position from the card's left edge, in mm"><NumInput value={feature.transform.x} step={0.1} onCommit={v => edit(f => { f.transform.x = v })} /></Row>
        <Row label="Y (mm)" hint="Vertical position from the card's top edge, in mm"><NumInput value={feature.transform.y} step={0.1} onCommit={v => edit(f => { f.transform.y = v })} /></Row>
        <Row label="Rotation" hint="Rotation in degrees, clockwise around the feature center"><NumInput value={feature.transform.rotation ?? 0} step={1} onCommit={v => edit(f => { f.transform.rotation = v })} /></Row>
        <Row label="Material" hint="Which material (filament color) this element prints in"><MaterialSelect materials={doc.materials} value={feature.material} onCommit={v => edit(f => { f.material = v })} /></Row>
        <Row label="Z-order" hint="Layer priority — the higher feature wins where two overlap"><NumInput value={feature.zOrder ?? 0} step={1} onCommit={v => edit(f => { f.zOrder = v })} /></Row>
        <Row label="Visible" hint="Hidden features stay in the file but are not compiled">
          <input type="checkbox" checked={feature.visible !== false}
            onChange={e => edit(f => { f.visible = e.target.checked })} />
        </Row>
      </Section>

      {/* Holes and pockets own their own z geometry (through-cut / blind
          cavity), so relief and backing don't apply to them. */}
      {feature.type !== 'hole' && feature.type !== 'pocket' && (
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
      {feature.type === 'pocket' && (
        <PocketEditor feature={feature} edit={edit}
          thickness={doc.object.thickness}
          layerHeight={doc.manufacturing?.layerHeight ?? 0.2}
          isBack={doc.faces.back?.features.some(f => f.id === feature.id) ?? false} />
      )}
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
      <Row label="Mode" hint="How it meets the surface: raised, carved, inlaid or cut through">
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
        <Row label="Height (mm)" hint="Height in millimeters"><NumInput value={relief.height ?? 0.4} step={0.1} onCommit={v => edit(f => { f.relief.height = v })} /></Row>
      )}
      {(relief.mode === 'deboss' || relief.mode === 'deboss-backed') && (
        <Row label="Depth (mm)" hint="How deep it sinks into the base, in mm"><NumInput value={relief.depth ?? 0.4} step={0.1} onCommit={v => edit(f => { f.relief.depth = v })} /></Row>
      )}
      {relief.mode === 'deboss' && (
        <Row label="Background" hint="Give the cavity floor a contrasting color">
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
          <Row label="Floor material" hint="Contrasting material at the bottom of the cavity">
            <MaterialSelect materials={materials.filter(m => m.id !== feature.material)}
              value={relief.floorMaterial ?? ''} allowEmpty emptyLabel="None → plain deboss"
              onCommit={v => edit(f => {
                if (v) { f.relief.floorMaterial = v; return }
                f.relief = { mode: 'deboss', depth: f.relief.depth ?? 0.4 }
              })} />
          </Row>
          <Row label="Floor thickness" hint="Thickness of the colored floor inside the cavity, in mm"><NumInput value={relief.floorThickness ?? 0.4} step={0.1} onCommit={v => edit(f => { f.relief.floorThickness = v })} /></Row>
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
      <Row label="Mode" hint="How it meets the surface: raised, carved, inlaid or cut through">
        <Select value={mode} options={[['auto', 'Auto'], ['on', 'Always on'], ['off', 'Off']]}
          onCommit={v => edit(f => {
            if (v === 'auto') delete f.backing
            else f.backing = { ...(f.backing ?? {}), mode: v as 'on' | 'off' }
          })} />
      </Row>
      {mode !== 'off' && (
        <>
          <Row label="Shape" hint="Outline shape">
            <Select value={feature.backing?.shape ?? 'rect'} options={[['rect', 'Rectangle'], ['circle', 'Circle']]}
              onCommit={v => edit(f => {
                if (!f.backing) f.backing = { mode }
                if (v === 'circle') f.backing.shape = 'circle'; else delete f.backing.shape
              })} />
          </Row>
          <Row label="Thickness" hint="Thickness in mm (0 = automatic)">
            <NumInput value={feature.backing?.thickness ?? 0} step={0.1} placeholder="0 = auto"
              onCommit={v => edit(f => {
                if (!f.backing) f.backing = { mode }
                if (v > 0) f.backing.thickness = v; else delete f.backing.thickness
              })} />
          </Row>
          <Row label="Material" hint="Which material (filament color) this element prints in">
            <MaterialSelect materials={materials} value={feature.backing?.material ?? ''} allowEmpty emptyLabel="Base (default)"
              onCommit={v => edit(f => {
                if (!f.backing) f.backing = { mode }
                if (v) f.backing.material = v; else delete f.backing.material
              })} />
          </Row>
          <Row label="Padding (mm)" hint="Extra margin around the feature bounds, in mm">
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
      <Row label="Align" hint="Text alignment inside the block">
        <Select value={feature.align ?? 'left'} options={[['left', 'Left'], ['center', 'Center'], ['right', 'Right']]}
          onCommit={v => edit<TextBlockFeature>(f => { f.align = v as TextBlockFeature['align'] })} />
      </Row>
      <Row label="Line height" hint="Line spacing as a multiple of the font size"><NumInput value={feature.lineHeight ?? 1.2} step={0.05} onCommit={v => edit<TextBlockFeature>(f => { f.lineHeight = v })} /></Row>
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
    <Row label="Family" hint="Font family — only fonts the Core can render are listed">
      {fonts.length > 0
        ? <Select value={current} options={options}
            onCommit={v => edit<TextBlockFeature | TextPatternFeature>(f => { f.font.family = v })} />
        : <TextInput value={current}
            onCommit={v => edit<TextBlockFeature | TextPatternFeature>(f => { f.font.family = v })} />}
    </Row>
    <Row label="Size (mm)" hint="Size in mm. Text has a 6mm floor so strokes stay printable"><NumInput value={feature.font.size} step={0.5} min={minSize} onCommit={v => edit<TextBlockFeature | TextPatternFeature>(f => { f.font.size = v })} /></Row>
    {weight && (
      <Row label="Weight" hint="Font weight 100–900 — heavier prints more reliably">
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
    <Row label="Italic" hint="Slanted style (needs an italic font file)">
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
      <Row label="Text" hint="Text repeated across the pattern area"><TextInput value={feature.text} onCommit={v => edit<TextPatternFeature>(f => { f.text = v })} /></Row>
      <Row label="Gap X (mm)" hint="Horizontal gap between repetitions, in mm"><NumInput value={feature.spacing} step={0.5} min={0.1} onCommit={v => edit<TextPatternFeature>(f => { f.spacing = v })} /></Row>
      <Row label="Gap Y (mm)" hint="Vertical gap between repetitions (empty = same as X)">
        <NumInput value={feature.spacingY ?? feature.spacing} step={0.5} min={0.1}
          onCommit={v => edit<TextPatternFeature>(f => {
            if (v === f.spacing) delete f.spacingY
            else f.spacingY = v
          })} />
      </Row>
      <Row label="Angle" hint="Pattern rotation in degrees"><NumInput value={feature.angle ?? 0} step={1} onCommit={v => edit<TextPatternFeature>(f => { f.angle = v })} /></Row>
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
    <Row label="Type" hint="Kind of element">
      <Select value={feature.patternType} options={[['dots', 'Dots'], ['lines', 'Lines'], ['grid', 'Grid'], ['hex', 'Hex'], ['svg', 'SVG motif']]}
        onCommit={v => edit<PatternFeature>(f => { f.patternType = v as PatternFeature['patternType'] })} />
    </Row>
    {feature.patternType === 'svg' && (
      <>
        <Row label="Library" vertical>
          <IconPicker featureId={feature.id} />
        </Row>
        <Row label="Upload .svg" hint="Load an SVG file from your computer">
          <input type="file" accept=".svg,image/svg+xml" onChange={handleSvgUpload} style={{ fontSize: 11, color: '#8b949e', maxWidth: 160 }} />
        </Row>
        {feature.svgInline && (
          <Row label="Motif" hint="SVG artwork repeated as the pattern motif"><ReadOnly value={`${Object.keys(feature.colorMap ?? {}).length || 1} color(s), ${feature.svgInline.length} chars`} /></Row>
        )}
      </>
    )}
    <Row label={feature.patternType === 'svg' ? 'Gap X (mm)' : 'Spacing (mm)'}><NumInput value={feature.spacing} step={0.5} min={0.1} onCommit={v => edit<PatternFeature>(f => { f.spacing = v })} /></Row>
    {feature.patternType === 'svg' && (
      <Row label="Gap Y (mm)" hint="Vertical gap between repetitions (empty = same as X)">
        <NumInput value={feature.spacingY ?? feature.spacing} step={0.5} min={0.1}
          onCommit={v => edit<PatternFeature>(f => {
            if (v === f.spacing) delete f.spacingY
            else f.spacingY = v
          })} />
      </Row>
    )}
    <Row label={feature.patternType === 'svg' ? 'Motif size (mm)' : 'Element size'}><NumInput value={feature.elementSize ?? 1} step={0.1} min={0.1} onCommit={v => edit<PatternFeature>(f => { f.elementSize = v })} /></Row>
    <Row label="Angle" hint="Pattern rotation in degrees"><NumInput value={feature.angle ?? 0} step={1} onCommit={v => edit<PatternFeature>(f => { f.angle = v })} /></Row>
    <Row label="Region" hint="Tile the whole face, or only this box">
      <Select value={feature.region ?? 'bounds'} options={[['face', 'Whole face'], ['bounds', 'Bounds']]}
        onCommit={v => edit<PatternFeature>(f => { f.region = v as PatternFeature['region'] })} />
    </Row>
    {(feature.region ?? 'bounds') === 'bounds' && (
      <>
        <Row label="Width (mm)" hint="Width in millimeters"><NumInput value={feature.width ?? 20} step={1} onCommit={v => edit<PatternFeature>(f => { f.width = v })} /></Row>
        <Row label="Height (mm)" hint="Height in millimeters"><NumInput value={feature.height ?? 20} step={1} onCommit={v => edit<PatternFeature>(f => { f.height = v })} /></Row>
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
      <Row label="Type" hint="Kind of element">
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
      <Row label="Size (mm)" hint="Size in mm. Text has a 6mm floor so strokes stay printable"><NumInput value={feature.size} step={1} onCommit={v => edit<QRFeature>(f => { f.size = v })} /></Row>
      <Row label="Error corr." hint="Redundancy level — higher survives damage, adds modules">
        <Select value={feature.errorCorrection ?? 'M'} options={[['L', 'L (7%)'], ['M', 'M (15%)'], ['Q', 'Q (25%)'], ['H', 'H (30%)']]}
          onCommit={v => edit<QRFeature>(f => { f.errorCorrection = v as QRFeature['errorCorrection'] })} />
      </Row>
      <Row label="Quiet zone" hint="Blank margin around the QR — required for scanning, in mm"><NumInput value={feature.quietZone ?? 2} step={1} onCommit={v => edit<QRFeature>(f => { f.quietZone = v })} /></Row>
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
      <Row label="Width (mm)" hint="Width in millimeters"><NumInput value={feature.width} step={0.5} onCommit={v => edit<IconFeature>(f => { f.width = v })} /></Row>
      <Row label="Height (mm)" hint="Height in millimeters">
        <NumInput value={feature.height ?? feature.width} step={0.5} onCommit={v => edit<IconFeature>(f => { f.height = v })} />
      </Row>
      <Row label="Library" vertical>
        <IconPicker featureId={feature.id} />
      </Row>
      <Row label="SVG asset" hint="Reference to an SVG registered in document assets">
        <TextInput value={feature.svgAsset ?? ''} placeholder="asset key"
          onCommit={v => edit<IconFeature>(f => { if (v) { f.svgAsset = v; delete f.svgInline } else delete f.svgAsset })} />
      </Row>
      <Row label="Upload .svg" hint="Load an SVG file from your computer">
        <input type="file" accept=".svg,image/svg+xml" onChange={handleUpload} style={{ fontSize: 11, color: '#8b949e', maxWidth: 160 }} />
      </Row>
      {feature.svgInline && (
        <Row label="Inline SVG" hint="SVG stored inside the document"><ReadOnly value={`${feature.svgInline.length} chars`} /></Row>
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
      <Row label="Type" hint="Kind of element">
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
      <Row label="Type" hint="Kind of element">
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
        <Row label="Diameter (mm)" hint="Diameter in millimeters">
          <NumInput value={feature.diameter ?? 5} step={0.5} onCommit={v => edit<HoleFeature>(f => { f.diameter = v })} />
        </Row>
      )}
      {t === 'slot' && (
        <>
          <Row label="Width (mm)" hint="Width in millimeters">
            <NumInput value={feature.width ?? 14} step={0.5} onCommit={v => edit<HoleFeature>(f => { f.width = v })} />
          </Row>
          <Row label="Height (mm)" hint="Height in millimeters">
            <NumInput value={feature.height ?? 5} step={0.5} onCommit={v => edit<HoleFeature>(f => { f.height = v })} />
          </Row>
        </>
      )}
      <Row label="Tab (add material)" hint="Adds a material lug around the hole so it can sit on the edge">
        <input type="checkbox" checked={feature.tab === true}
          onChange={e => edit<HoleFeature>(f => { if (e.target.checked) f.tab = true; else { delete f.tab; delete f.tabMargin } })} />
      </Row>
      {feature.tab && (
        <Row label="Tab margin (mm)" hint="Ring of material around the hole, in mm">
          <NumInput value={feature.tabMargin ?? 3} step={0.5} onCommit={v => edit<HoleFeature>(f => { f.tabMargin = v })} />
        </Row>
      )}
    </Section>
  )
}

// ── pocket ───────────────────────────────────────────────────────────

/** Stock inserts, so the common cases are one click instead of a caliper.
 *  [label, nominal diameter mm, nominal thickness mm] */
const INSERT_SIZES: Record<string, Array<[string, number, number]>> = {
  magnet: [
    ['Ø3 × 1 mm', 3, 1], ['Ø4 × 2 mm', 4, 2], ['Ø5 × 2 mm', 5, 2],
    ['Ø6 × 2 mm', 6, 2], ['Ø6 × 3 mm', 6, 3], ['Ø8 × 3 mm', 8, 3],
    ['Ø10 × 2 mm', 10, 2], ['Ø10 × 3 mm', 10, 3],
  ],
  rfid: [
    ['Ø18 × 0.9 mm (NTAG)', 18, 0.9], ['Ø25 × 0.9 mm (NTAG213)', 25, 0.9],
    ['Ø30 × 1 mm', 30, 1], ['Ø38 × 1 mm', 38, 1],
  ],
  other: [],
}

/** Fit presets — how much slack the bore gets over the insert's nominal
 *  size. A printed hole comes out undersized, so even a "press" fit needs
 *  some: these are starting points to tune per printer, not laws. */
const FIT_PRESETS: Array<[string, string, number, number]> = [
  ['press', 'Press fit (tight, needs force)', 0.1, 0.05],
  ['snug', 'Snug (push in by hand)', 0.2, 0.1],
  ['loose', 'Loose (drops in, glue it)', 0.35, 0.15],
]

const PocketEditor: React.FC<{
  feature: PocketFeature; edit: EditFn
  thickness: number; layerHeight: number; isBack: boolean
}> = ({ feature, edit, thickness, layerHeight, isBack }) => {
  const insert = feature.insert ?? 'magnet'
  const clearance = feature.clearance ?? DEFAULT_POCKET_CLEARANCE
  const depthClearance = feature.depthClearance ?? DEFAULT_POCKET_DEPTH_CLEARANCE
  const ceiling = feature.ceiling ?? 0

  // What actually gets cut, and what is left holding it together.
  const bore = feature.diameter + clearance
  const cavityDepth = feature.depth + depthClearance
  const floor = thickness - ceiling - cavityDepth
  const minWall = Math.max(0.8, 2 * layerHeight)
  // Mirrors the Core's slack (kernel/constraints.py): the floor is a
  // difference of authored millimetres, so hitting the minimum exactly lands
  // a few ulps under it and must not read as too thin.
  const thinnerThanMin = (v: number) => v < minWall - 1e-6
  const pauseZ = isBack ? ceiling + cavityDepth : thickness - ceiling

  const sizes = INSERT_SIZES[insert] ?? []
  const currentSize = sizes.find(([, d, h]) => d === feature.diameter && h === feature.depth)
  const currentFit = FIT_PRESETS.find(([, , c, dc]) => c === clearance && dc === depthClearance)

  const note = (text: string, color: string) => (
    <div style={{ fontSize: 11, color, padding: '2px 0' }}>{text}</div>
  )

  return (
    <Section title="Pocket">
      <div style={{ fontSize: 11, color: '#8b949e', padding: '2px 0 6px' }}>
        A blind cavity that houses an insert. Give it the insert's real size —
        the clearance below is what opens the bore up so it actually fits.
      </div>
      <Row label="Insert" hint="What goes in the pocket — a label for the build notes, it doesn't change the geometry">
        <Select value={insert} options={[['magnet', 'Magnet'], ['rfid', 'RFID / NFC tag'], ['other', 'Other']]}
          onCommit={v => edit<PocketFeature>(f => { f.insert = v as PocketFeature['insert'] })} />
      </Row>
      {sizes.length > 0 && (
        <Row label="Stock size" hint="Fills in the diameter and thickness of a common off-the-shelf insert">
          <Select value={currentSize?.[0] ?? ''}
            options={[['', 'Custom…'], ...sizes.map(([label]) => [label, label] as [string, string])]}
            onCommit={v => {
              const hit = sizes.find(([label]) => label === v)
              if (!hit) return
              edit<PocketFeature>(f => { f.diameter = hit[1]; f.depth = hit[2] })
            }} />
        </Row>
      )}
      <Row label="Insert Ø (mm)" hint="The insert's nominal diameter, before clearance">
        <NumInput value={feature.diameter} step={0.5} min={0.1}
          onCommit={v => edit<PocketFeature>(f => { f.diameter = v })} />
      </Row>
      <Row label="Insert thickness (mm)" hint="The insert's nominal thickness, before clearance">
        <NumInput value={feature.depth} step={0.1} min={0.1}
          onCommit={v => edit<PocketFeature>(f => { f.depth = v })} />
      </Row>

      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 0.6, textTransform: 'uppercase', color: '#8b949e', margin: '10px 0 6px' }}>
        Tolerance
      </div>
      <Row label="Fit" hint="Preset slack for the bore — tune the numbers below for your printer">
        <Select value={currentFit?.[0] ?? ''}
          options={[['', 'Custom…'], ...FIT_PRESETS.map(([id, label]) => [id, label] as [string, string])]}
          onCommit={v => {
            const hit = FIT_PRESETS.find(([id]) => id === v)
            if (!hit) return
            edit<PocketFeature>(f => { f.clearance = hit[2]; f.depthClearance = hit[3] })
          }} />
      </Row>
      <Row label="Ø clearance (mm)" hint="Added to the insert diameter. Printed holes come out undersized — 0 will not fit">
        <NumInput value={clearance} step={0.05} min={0}
          onCommit={v => edit<PocketFeature>(f => { f.clearance = v })} />
      </Row>
      <Row label="Depth clearance (mm)" hint="Added to the insert thickness, so it sits below the surface instead of proud of it">
        <NumInput value={depthClearance} step={0.05} min={0}
          onCommit={v => edit<PocketFeature>(f => { f.depthClearance = v })} />
      </Row>
      {clearance <= 0 && note('No clearance: the bore is cut at the exact nominal diameter and the insert will not go in.', '#d29922')}

      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 0.6, textTransform: 'uppercase', color: '#8b949e', margin: '10px 0 6px' }}>
        Placement
      </div>
      <Row label="Ceiling (mm)" hint="Material left over the pocket. 0 opens it at the surface; more than 0 seals the insert inside and the print must be paused to drop it in">
        <NumInput value={ceiling} step={0.1} min={0}
          onCommit={v => edit<PocketFeature>(f => { if (v > 0) f.ceiling = v; else delete f.ceiling })} />
      </Row>

      <Row label="Bore cut"><ReadOnly value={`Ø${bore.toFixed(2)} × ${cavityDepth.toFixed(2)} mm deep`} /></Row>
      <Row label="Floor left"><ReadOnly value={`${floor.toFixed(2)} mm`} /></Row>
      {floor <= 0
        ? note(`The pocket needs ${(ceiling + cavityDepth).toFixed(2)}mm but the object is only ${thickness}mm thick — it breaks through the other face.`, '#f85149')
        : thinnerThanMin(floor)
          ? note(`Only ${floor.toFixed(2)}mm of floor is left; use at least ${minWall}mm or it will crack.`, '#d29922')
          : null}
      {ceiling > 0 && (
        <>
          {thinnerThanMin(ceiling) && note(`The ${ceiling.toFixed(2)}mm lid has to bridge the whole bore; use at least ${minWall}mm.`, '#d29922')}
          {note(`Sealed pocket: pause the print at z = ${pauseZ.toFixed(2)}mm to place the ${insert === 'rfid' ? 'tag' : insert}, then resume.`, '#8b949e')}
        </>
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
      <Row label="Radius (mm)" hint="Corner rounding radius, in mm">
        <NumInput value={outline.radius} step={0.5} onCommit={v => applyEdit(d => {
          if (d.object.outline.type === 'rounded-rect') d.object.outline.radius = v
        })} />
      </Row>
      <Row label="Per-corner" hint="Set a different radius on each corner">
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

// ── Color layer (multicolor SVG outline) ─────────────────────────────

type PathOutline = Extract<Outline, { type: 'path' }>

/** Where the artwork's colors live in Z. A depth-limited layer on one face
 *  leaves the rest of the body in base material, so the other face is a
 *  clean canvas for text/QR; 'through' colors the whole thickness. */
const ColorLayerEditor: React.FC<{ outline: PathOutline; thickness: number; applyEdit: ApplyEdit }> =
  ({ outline, thickness, applyEdit }) => {
  const side = outline.colorDepth ? (outline.colorFace ?? 'front') : 'through'
  const depth = outline.colorDepth ?? DEFAULT_COLOR_DEPTH

  const write = (nextSide: typeof side, nextDepth: number) => applyEdit(d => {
    const o = d.object.outline
    if (o.type !== 'path') return
    if (nextSide === 'through') {
      delete o.colorDepth
      delete o.colorFace
      return
    }
    // The Core rejects a layer as deep as the body — that IS 'through'.
    o.colorDepth = clampColorDepth(nextDepth, d.object.thickness) ?? DEFAULT_COLOR_DEPTH
    if (nextSide === 'front') delete o.colorFace
    else o.colorFace = nextSide
  })

  return (
    <>
      <Row label="Colors on" hint="Face that shows the artwork. The other face prints solid base material — room for text and QR">
        <Select value={side}
          options={[['front', 'Front only'], ['back', 'Back only'], ['both', 'Both faces'], ['through', 'Through (solid colors)']]}
          onCommit={v => write(v as typeof side, depth)} />
      </Row>
      {side !== 'through' && (
        <Row label="Color depth (mm)" hint="Depth of the colored layer. Under two print layers the base below shows through">
          <NumInput value={depth} step={0.2} min={0.2} max={Math.max(0.2, thickness / 2)}
            onCommit={v => write(side, v)} />
        </Row>
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
      <Row label="Mode" hint="How it meets the surface: raised, carved, inlaid or cut through">
        <Select value={mode} options={[['solid', 'Solid'], ['lattice', 'Lattice']]}
          onCommit={v => applyEdit(d => {
            if (v === 'lattice') d.object.fill = { ...LATTICE_DEFAULTS }
            else delete d.object.fill
          })} />
      </Row>
      {mode === 'lattice' && (
        <>
          <Row label="Pattern" hint="Motif used to fill the area">
            <Select value={lat.pattern} options={[['dots', 'Dots'], ['lines', 'Lines'], ['grid', 'Grid'], ['hex', 'Hex']]}
              onCommit={v => editLattice(f => { f.pattern = v as typeof f.pattern })} />
          </Row>
          <Row label="Spacing (mm)" hint="Gap between repetitions, in mm"><NumInput value={lat.spacing} step={0.5} onCommit={v => editLattice(f => { f.spacing = v })} /></Row>
          <Row label="Line width" hint="Lattice strut width, in mm"><NumInput value={lat.lineWidth ?? 1.2} step={0.1} onCommit={v => editLattice(f => { f.lineWidth = v })} /></Row>
          <Row label="Border (mm)" hint="Solid rim width around the lattice, in mm"><NumInput value={lat.border ?? 2.5} step={0.5} onCommit={v => editLattice(f => { f.border = v })} /></Row>
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
      <Row label="Nozzle (mm)" hint="Printer nozzle diameter — sets the minimum printable detail">
        <NumInput value={nozzle} step={0.05} onCommit={v => editMfg(m => { m.nozzle = v })} />
      </Row>
      <Row label="Process" hint="Manufacturing process the checks validate against">
        <Select value={process} options={PROCESS_OPTIONS}
          onCommit={v => editMfg(m => { m.process = v as NonNullable<DocumentV2['manufacturing']>['process'] })} />
      </Row>
      <Row label="Layer height" hint="Printing layer height, in mm">
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
        <Row label="Name" hint="Display name — shown in the layers list and exported part names">
          <TextInput value={doc.meta.name} onCommit={v => applyEdit(d => { d.meta.name = v })} />
        </Row>
        <Row label="ID"><ReadOnly value={doc.meta.id} /></Row>
      </Section>

      <Section title="Outline">
        <Row label="Shape" hint="Outline shape">
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
          <Row label="Diameter (mm)" hint="Diameter in millimeters">
            <NumInput value={outline.diameter} step={1} onCommit={v => applyEdit(d => {
              if (d.object.outline.type === 'circle') d.object.outline.diameter = v
            })} />
          </Row>
        ) : (
          <>
            <Row label="Width (mm)" hint="Width in millimeters"><NumInput value={dims.width} step={1} onCommit={v => applyEdit(d => {
              const o = d.object.outline
              if (o.type !== 'circle') o.width = v
            })} /></Row>
            <Row label="Height (mm)" hint="Height in millimeters"><NumInput value={dims.height} step={1} onCommit={v => applyEdit(d => {
              const o = d.object.outline
              if (o.type !== 'circle') o.height = v
            })} /></Row>
          </>
        )}

        {outline.type === 'rounded-rect' && <CornerRadiusEditor outline={outline} applyEdit={applyEdit} />}

        {outline.type === 'path' && (
          <>
            <Row label="Upload .svg" hint="Use an SVG file as the card shape — its colors extrude in their own materials">
              <input type="file" accept=".svg,image/svg+xml" style={{ fontSize: 11, color: '#8b949e', maxWidth: 160 }}
                onChange={e => {
                  const file = e.target.files?.[0]
                  if (!file) return
                  void file.text().then(text => {
                    applyEdit(d => { applySvgOutline(d, text) })
                  })
                  e.target.value = ''
                }} />
            </Row>
            {outline.svgInline ? (
              <>
                <Row label="SVG" hint="SVG artwork stored inside the document">
                  <ReadOnly value={`${Object.keys(outline.colorMap ?? {}).length || 1} color(s), ${outline.svgInline.length} chars`} />
                </Row>
                <Row label="Color map" hint="Each SVG color prints in its own material" vertical>
                  <ColorMapEditor
                    value={outline.colorMap ?? {}}
                    materials={doc.materials}
                    onCommit={map => applyEdit(d => {
                      const o = d.object.outline
                      if (o.type !== 'path') return
                      if (Object.keys(map).length) o.colorMap = map
                      else delete o.colorMap
                    })}
                  />
                </Row>
                <ColorLayerEditor outline={outline} thickness={doc.object.thickness} applyEdit={applyEdit} />
              </>
            ) : (
              <Row label="SVG path" vertical>
                <TextArea value={outline.svgPath} rows={3} onCommit={v => applyEdit(d => {
                  if (d.object.outline.type === 'path') d.object.outline.svgPath = v
                })} />
              </Row>
            )}
          </>
        )}
      </Section>

      <Section title="Base">
        <Row label="Material" hint="Which material (filament color) this element prints in">
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
        <Row label="Thickness" hint="Thickness in mm (0 = automatic)"><NumInput value={doc.object.thickness} step={0.1} onCommit={v => applyEdit(d => { d.object.thickness = v })} /></Row>
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


const IconBtn: React.FC<{ title: string; onClick: () => void; children: React.ReactNode }> = ({ title, onClick, children }) => (
  <button title={title} onClick={onClick} style={{
    background: 'transparent', color: '#8b949e', border: 'none', cursor: 'pointer', fontSize: 11, padding: '0 2px', flexShrink: 0,
  }}>{children}</button>
)
