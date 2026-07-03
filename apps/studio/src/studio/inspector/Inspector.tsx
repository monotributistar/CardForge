// Inspector — per-type property editors bound to the selected feature.
// When nothing is selected, shows the document properties instead.
// Every change goes through DocumentStore.applyEdit (undoable).

import React from 'react'
import type {
  DocumentV2, Feature, Material, ReliefMode,
  TextBlockFeature, TextPatternFeature, PatternFeature, QRFeature, IconFeature, ShapeFeature,
} from '../../types/cardforge'
import { useDocumentStore, getActiveTab, findFeature, removeFeatures } from '../../state/DocumentStore'
import { FIELD_DEFS, QR_TYPE_LABELS, type QRType } from '../services/QRFields'

type ApplyEdit = (mutator: (doc: DocumentV2) => void) => void

// ── Root ─────────────────────────────────────────────────────────────

export const Inspector: React.FC = () => {
  const tab = useDocumentStore(getActiveTab)
  const applyEdit = useDocumentStore(s => s.applyEdit)

  if (!tab) {
    return <Empty text="No document open" />
  }
  const doc = tab.doc
  const found = tab.selectedFeatureId ? findFeature(doc, tab.selectedFeatureId) : null

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

      <ReliefEditor feature={feature} materials={doc.materials} edit={edit}
        isBack={doc.faces.back?.features.some(f => f.id === feature.id) ?? false} />

      {feature.type === 'text-block' && <TextBlockEditor feature={feature} edit={edit} />}
      {feature.type === 'text-pattern' && <TextPatternEditor feature={feature} edit={edit} />}
      {feature.type === 'pattern' && <PatternEditor feature={feature} edit={edit} />}
      {feature.type === 'qr' && <QREditor feature={feature} edit={edit} />}
      {feature.type === 'icon' && <IconEditor feature={feature} materials={doc.materials} edit={edit} />}
      {feature.type === 'shape' && <ShapeEditor feature={feature} edit={edit} />}
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
            f.relief.mode = v as ReliefMode
            if (v === 'emboss' && f.relief.height == null) f.relief.height = 0.4
            if ((v === 'deboss' || v === 'deboss-backed') && f.relief.depth == null) f.relief.depth = 0.4
            if (v === 'flush' && f.relief.depth == null) f.relief.depth = 0.4
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
      {relief.mode === 'deboss-backed' && (
        <>
          <Row label="Floor material">
            <MaterialSelect materials={materials} value={relief.floorMaterial ?? ''} allowEmpty
              onCommit={v => edit(f => { if (v) f.relief.floorMaterial = v; else delete f.relief.floorMaterial })} />
          </Row>
          <Row label="Floor thickness"><NumInput value={relief.floorThickness ?? 0.4} step={0.1} onCommit={v => edit(f => { f.relief.floorThickness = v })} /></Row>
        </>
      )}
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
    <FontEditor feature={feature} edit={edit} weight />
  </>
)

const FontEditor: React.FC<{ feature: TextBlockFeature | TextPatternFeature; edit: EditFn; weight?: boolean }> = ({ feature, edit, weight }) => (
  <Section title="Font">
    <Row label="Family">
      <TextInput value={feature.font.family}
        onCommit={v => edit<TextBlockFeature | TextPatternFeature>(f => { f.font.family = v })} />
    </Row>
    <Row label="Size (mm)"><NumInput value={feature.font.size} step={0.5} onCommit={v => edit<TextBlockFeature | TextPatternFeature>(f => { f.font.size = v })} /></Row>
    {weight && (
      <Row label="Weight">
        <NumInput value={feature.font.weight ?? 400} step={50} min={100} max={900}
          onCommit={v => edit<TextBlockFeature>(f => { f.font.weight = v })} />
      </Row>
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

// ── text-pattern ─────────────────────────────────────────────────────

const TextPatternEditor: React.FC<{ feature: TextPatternFeature; edit: EditFn }> = ({ feature, edit }) => (
  <>
    <Section title="Text pattern">
      <Row label="Text"><TextInput value={feature.text} onCommit={v => edit<TextPatternFeature>(f => { f.text = v })} /></Row>
      <Row label="Spacing (mm)"><NumInput value={feature.spacing} step={0.5} onCommit={v => edit<TextPatternFeature>(f => { f.spacing = v })} /></Row>
      <Row label="Angle"><NumInput value={feature.angle ?? 0} step={1} onCommit={v => edit<TextPatternFeature>(f => { f.angle = v })} /></Row>
    </Section>
    <FontEditor feature={feature} edit={edit} />
  </>
)

// ── pattern ──────────────────────────────────────────────────────────

const PatternEditor: React.FC<{ feature: PatternFeature; edit: EditFn }> = ({ feature, edit }) => (
  <Section title="Pattern">
    <Row label="Type">
      <Select value={feature.patternType} options={[['dots', 'Dots'], ['lines', 'Lines'], ['grid', 'Grid'], ['hex', 'Hex']]}
        onCommit={v => edit<PatternFeature>(f => { f.patternType = v as PatternFeature['patternType'] })} />
    </Row>
    <Row label="Spacing (mm)"><NumInput value={feature.spacing} step={0.5} onCommit={v => edit<PatternFeature>(f => { f.spacing = v })} /></Row>
    <Row label="Element size"><NumInput value={feature.elementSize ?? 1} step={0.1} onCommit={v => edit<PatternFeature>(f => { f.elementSize = v })} /></Row>
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

// ── icon ─────────────────────────────────────────────────────────────

const IconEditor: React.FC<{ feature: IconFeature; materials: Material[]; edit: EditFn }> = ({ feature, materials, edit }) => {
  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    void file.text().then(text => {
      edit<IconFeature>(f => {
        f.svgInline = text
        delete f.svgAsset
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

// ── Document inspector (nothing selected) ────────────────────────────

const DocumentInspector: React.FC<{ doc: DocumentV2; applyEdit: ApplyEdit }> = ({ doc, applyEdit }) => {
  const outline = doc.object.outline
  return (
    <div>
      <Section title="Document">
        <Row label="Name">
          <TextInput value={doc.meta.name} onCommit={v => applyEdit(d => { d.meta.name = v })} />
        </Row>
        <Row label="ID"><ReadOnly value={doc.meta.id} /></Row>
      </Section>

      <Section title="Object">
        <Row label="Outline">
          <Select value={outline.type} options={[['rect', 'Rectangle'], ['rounded-rect', 'Rounded rect'], ['path', 'SVG path']]}
            onCommit={v => applyEdit(d => {
              const o = d.object.outline
              if (v === 'rect') d.object.outline = { type: 'rect', width: o.width, height: o.height }
              else if (v === 'rounded-rect') d.object.outline = { type: 'rounded-rect', width: o.width, height: o.height, radius: o.type === 'rounded-rect' ? o.radius : 4 }
              else d.object.outline = { type: 'path', svgPath: o.type === 'path' ? o.svgPath : '', width: o.width, height: o.height }
            })} />
        </Row>
        <Row label="Width (mm)"><NumInput value={outline.width} step={1} onCommit={v => applyEdit(d => { d.object.outline.width = v })} /></Row>
        <Row label="Height (mm)"><NumInput value={outline.height} step={1} onCommit={v => applyEdit(d => { d.object.outline.height = v })} /></Row>
        {outline.type === 'rounded-rect' && (
          <Row label="Radius (mm)">
            <NumInput value={outline.radius} step={0.5} onCommit={v => applyEdit(d => {
              if (d.object.outline.type === 'rounded-rect') d.object.outline.radius = v
            })} />
          </Row>
        )}
        {outline.type === 'path' && (
          <Row label="SVG path" vertical>
            <TextArea value={outline.svgPath} rows={3} onCommit={v => applyEdit(d => {
              if (d.object.outline.type === 'path') d.object.outline.svgPath = v
            })} />
          </Row>
        )}
        <Row label="Thickness"><NumInput value={doc.object.thickness} step={0.1} onCommit={v => applyEdit(d => { d.object.thickness = v })} /></Row>
      </Section>

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

const NumInput: React.FC<{ value: number; step?: number; min?: number; max?: number; onCommit: (v: number) => void }> = ({ value, step, min, max, onCommit }) => (
  <input
    type="number"
    style={{ ...inputStyle, maxWidth: 90 }}
    value={value}
    step={step}
    min={min}
    max={max}
    onChange={e => {
      const n = e.target.valueAsNumber
      if (!Number.isNaN(n)) onCommit(n)
    }}
  />
)

const Select: React.FC<{ value: string; options: Array<[string, string]>; onCommit: (v: string) => void }> = ({ value, options, onCommit }) => (
  <select value={value} onChange={e => onCommit(e.target.value)} style={{ ...inputStyle, cursor: 'pointer' }}>
    {options.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
  </select>
)

const MaterialSelect: React.FC<{ materials: Material[]; value: string; allowEmpty?: boolean; onCommit: (v: string) => void }> = ({ materials, value, allowEmpty, onCommit }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1, minWidth: 0 }}>
    <span style={{
      width: 12, height: 12, borderRadius: 2, flexShrink: 0,
      background: materials.find(m => m.id === value)?.color ?? 'transparent',
      border: '1px solid #30363d',
    }} />
    <select value={value} onChange={e => onCommit(e.target.value)} style={{ ...inputStyle, cursor: 'pointer' }}>
      {allowEmpty && <option value="">(none)</option>}
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
