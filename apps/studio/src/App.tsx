import React, { useState, useCallback, useRef } from 'react'
import { Workspace } from './studio/workspace/Workspace'
import { Scene } from './studio/scene/Scene'
import { SelectionModel } from './studio/selection/Selection'
import { Viewport } from './studio/viewport/Viewport'
import { CommandManager, OpenDocumentCommand } from './studio/commands/CommandManager'
import { InteractiveCanvas } from './studio/canvas/InteractiveCanvas'
import { Inspector } from './studio/inspector/Inspector'
import { ManufacturingPanel } from './studio/manufacturing/ManufacturingPanel'
import { BuildConsole } from './studio/build/BuildConsole'
import { createNewDocument, findFeature } from './studio/document/DocumentEditor'
import { compileLive, type CompileResult } from './studio/services/CompileService'
import { previewPublish, type PublishResult } from './studio/publish/PublishService'
import { PublishDialog } from './studio/publish/PublishDialog'
import type { CardForgeDocument, ManufacturingReport, Feature } from './types/cardforge'

// ── Singletons ────────────────────────────────────────────────────────
const workspace = new Workspace()
const scene = new Scene()
const selection = new SelectionModel()
const viewport = new Viewport()
const cmdCtx = { workspace, scene, selection, viewport }
const commandManager = new CommandManager(cmdCtx)

// ── Layout ────────────────────────────────────────────────────────────
const S: Record<string, React.CSSProperties> = {
  container: { display: 'flex', flexDirection: 'column', height: '100vh', background: '#0d1117', color: '#c9d1d9' },
  topBar: { height: 42, background: '#161b22', borderBottom: '1px solid #30363d', display: 'flex', alignItems: 'center', padding: '0 12px', gap: 8 },
  main: { display: 'flex', flex: 1, overflow: 'hidden' },
  left: { width: 240, background: '#161b22', borderRight: '1px solid #30363d', overflow: 'auto', padding: 12 },
  center: { flex: 1, background: '#0d1117', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'auto' },
  right: { width: 280, background: '#161b22', borderLeft: '1px solid #30363d', overflow: 'auto', padding: 12 },
  bottom: { minHeight: 80, background: '#161b22', borderTop: '1px solid #30363d', padding: '0 16px', display: 'flex', flexDirection: 'column' },
}

const btn = (primary?: boolean): React.CSSProperties => ({
  background: primary ? '#238636' : '#21262d', color: primary ? '#fff' : '#c9d1d9',
  border: `1px solid ${primary ? '#2ea043' : '#30363d'}`,
  padding: '4px 12px', borderRadius: 6, cursor: 'pointer', fontSize: 12, whiteSpace: 'nowrap',
})

export default function App() {
  const fileRef = useRef<HTMLInputElement>(null)
  const [doc, setDoc] = useState<CardForgeDocument | null>(null)
  const [frontSvg, setFrontSvg] = useState<string | null>(null)
  const [backSvg, setBackSvg] = useState<string | null>(null)
  const [report, setReport] = useState<ManufacturingReport | null>(null)
  const [publishResult, setPublishResult] = useState<PublishResult | null>(null)
  const [reliefPreset, setReliefPreset] = useState('standard')
  const [theme, setTheme] = useState('dark-luxury')
  const [, forceUpdate] = useState(0)
  const rerender = () => forceUpdate(n => n + 1)

  // ── Compile ────────────────────────────────────────────────────────
  const compile = useCallback((d: CardForgeDocument) => {
    try {
      const result = compileLive(JSON.parse(JSON.stringify(d)))
      setFrontSvg(result.frontSvg)
      setBackSvg(result.backSvg)
      setReport(result.report)
    } catch (e) {
      console.error('Compile error:', e)
    }
  }, [])

  // ── New Document ───────────────────────────────────────────────────
  const handleNew = () => {
    const newDoc = createNewDocument()
    setDoc(newDoc)
    selection.actions.clear()
    compile(newDoc)
  }

  const loadTemplate = (template: string) => {
    const doc = createNewDocument()
    const colors: Record<string, any> = {
      minimal: { base: 'white', text: 'black', accent: 'black' },
      'dark-luxury': { base: 'black', text: 'white', accent: 'gold' },
      tech: { base: '#0a0a0a', text: '#00ff88', accent: '#00ff88' },
    }
    const c = colors[template] || colors['dark-luxury']
    if (doc.objects[0]?.theme) {
      doc.objects[0].theme.baseColor = c.base
      doc.objects[0].theme.textColor = c.text
      doc.objects[0].theme.accentColor = c.accent
      doc.objects[0].theme.name = template
    }
    setTheme(template)
    setDoc(doc)
    selection.actions.clear()
    compile(doc)
  }

  // ── Load ───────────────────────────────────────────────────────────
  const handleLoad = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files; if (!files) return
    for (const file of Array.from(files)) {
      try {
        const text = await file.text()
        const data = JSON.parse(text)
        if (data.objects || data.document) {
          const d = data as CardForgeDocument
          setDoc(d); selection.actions.clear(); compile(d)
        } else if (data.project && data.faces) {
          // Legacy config
          const d: CardForgeDocument = {
            document: { id: data.project?.name?.toLowerCase?.()?.replace(/\s+/g, '-') ?? 'legacy', name: data.project?.name ?? 'Legacy', version: '0.1.0' },
            manufacturing: { profile: 'fdm-standard', process: data.manufacturing?.process ?? 'fdm', nozzle: data.manufacturing?.nozzle ?? 0.4, layerHeight: data.manufacturing?.layerHeight ?? 0.2, material: 'PLA' },
            variables: data.owner ?? {}, objects: [{ id: 'main-card', type: 'business-card', width: data.object?.width ?? 85, height: data.object?.height ?? 54, thickness: data.object?.thickness ?? 1.8, cornerRadius: data.object?.cornerRadius ?? 4, theme: data.theme, faces: data.faces }],
            exports: { preview: true, manufacturingReport: true, singleStl: true, colorSeparatedStl: false, threeMf: false },
          }
          setDoc(d); selection.actions.clear(); compile(d)
        }
      } catch (err: any) { console.error(err) }
    }
    if (fileRef.current) fileRef.current.value = ''
  }

  // ── Save ───────────────────────────────────────────────────────────
  const handleSave = () => {
    if (!doc) return
    const blob = new Blob([JSON.stringify(doc, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `${doc.document.id}.cardforge.json`; a.click()
    URL.revokeObjectURL(url)
  }

  // ── Edits (trigger compile after each) ─────────────────────────────
  const edit = useCallback((fn: () => void) => {
    if (!doc) return
    fn()
    const copy = JSON.parse(JSON.stringify(doc))
    setDoc(copy)
    compile(copy)
    rerender()
  }, [doc, compile])

  // ── Selected feature ───────────────────────────────────────────────
  const selectedFeature: Feature | null = doc && selection.selectedFeatureId
    ? findFeature(doc, selection.selectedFeatureId) : null

  return (
    <div style={S.container}>
      {/* TopBar */}
      <div style={S.topBar}>
        <span style={{ fontWeight: 700, fontSize: 14, color: '#58a6ff' }}>CardForge Studio</span>
        <span style={{ fontSize: 10, background: '#238636', color: '#fff', padding: '1px 6px', borderRadius: 8 }}>MVP</span>
        <span style={{ fontSize: 13, color: '#8b949e', flex: 1 }}>
          {doc ? doc.document.name : 'No document'}
        </span>
        <button style={btn()} onClick={handleNew}>New Card</button>
        <button style={btn()} onClick={() => { loadTemplate('minimal') }}>Minimal</button>
        <button style={btn()} onClick={() => { loadTemplate('dark-luxury') }}>Luxury</button>
        <button style={btn()} onClick={() => { loadTemplate('tech') }}>Tech</button>
        <input ref={fileRef} type="file" accept=".json,.cardforge.json" onChange={handleLoad} style={{ display: 'none' }} id="fi" />
        <button style={btn()} onClick={() => fileRef.current?.click()}>Open</button>
        <button style={btn()} onClick={handleSave} disabled={!doc}>Save</button>
        <button style={btn(true)} onClick={() => {
          if (doc && report) setPublishResult(previewPublish(doc, report))
        }} disabled={!doc || !report}>Publish</button>
      </div>

      {/* Main */}
      <div style={S.main}>
        {/* LeftPanel */}
        <div style={S.left}>
          <DocTree doc={doc} sel={selection.selectedFeatureId}
            onSel={(id: string) => { selection.actions.select(id); rerender() }} />
          <VariablesPanel doc={doc} onUpdate={(k, v) => edit(() => {
            if (doc) doc.variables[k] = v
          })} />
        </div>

        {/* Canvas */}
        <div style={S.center}>
          <InteractiveCanvas
            frontSvg={frontSvg} backSvg={backSvg} activeFace={scene.activeFace}
            zoom={viewport.zoom} offsetX={viewport.state.offsetX} offsetY={viewport.state.offsetY}
            document={doc} selectedFeatureId={selection.selectedFeatureId}
            onToggleFace={() => { scene.actions.toggleActiveFace(); rerender() }}
            onZoomIn={() => { viewport.actions.zoomIn(); rerender() }}
            onZoomOut={() => { viewport.actions.zoomOut(); rerender() }}
            onResetZoom={() => { viewport.actions.resetZoom(); rerender() }}
            onSelectFeature={(id: string) => { selection.actions.select(id || null); rerender() }}
            onMoveFeature={(featureId, x, y) => {
              if (!doc) return
              const feat = findFeature(doc, featureId)
              if (feat?.position) {
                feat.position.x = Math.round(x * 10) / 10
                feat.position.y = Math.round(y * 10) / 10
                const copy = JSON.parse(JSON.stringify(doc))
                setDoc(copy)
                compile(copy)
                rerender()
              }
            }}
          />
        </div>

        {/* RightPanel */}
        <div style={S.right}>
          <Inspector
            selectedFeature={selectedFeature}
            document={doc}
            reliefPreset={reliefPreset}
            onReliefPreset={setReliefPreset}
            theme={theme}
            onTheme={(t) => {
              setTheme(t)
              if (!doc) return
              const colors: Record<string, any> = { minimal: { base: 'white', text: 'black', accent: 'black' }, 'dark-luxury': { base: 'black', text: 'white', accent: 'gold' }, tech: { base: '#0a0a0a', text: '#00ff88', accent: '#00ff88' }, industrial: { base: '#2a2a2a', text: '#ff6b35', accent: '#ff6b35' } }
              const c = colors[t] || colors['dark-luxury']
              if (doc.objects[0]?.theme) { doc.objects[0].theme.baseColor = c.base; doc.objects[0].theme.textColor = c.text; doc.objects[0].theme.accentColor = c.accent }
              compile(doc)
            }}
            onUpdatePosX={(id, x) => edit(() => { if (!doc) return; const f = findFeature(doc, id); if (f?.position) f.position.x = x })}
            onUpdatePosY={(id, y) => edit(() => { if (!doc) return; const f = findFeature(doc, id); if (f?.position) f.position.y = y })}
            onReplaceLogo={(id, svg) => {
              if (!doc) return
              const f = findFeature(doc, id)
              if (f) { (f as any).file = 'logo.svg'; (f as any)._svgContent = svg }
              compile(doc); rerender()
            }}
            onUpdateText={(id, lines) => edit(() => {
              if (!doc) return
              const f = findFeature(doc, id)
              if (f) (f as any).lines = lines
            })}
            onUpdateFont={(id, font) => edit(() => {
              if (!doc) return
              const f = findFeature(doc, id)
              if (f) (f as any).font = font
            })}
            onUpdateFontSize={(id, size) => edit(() => {
              if (!doc) return
              const f = findFeature(doc, id)
              if (f) (f as any).fontSize = size
            })}
            onUpdateRelief={(id, h) => edit(() => {
              if (!doc) return
              const f = findFeature(doc, id)
              if (f?.relief) f.relief.height = h
            })}
            onUpdateMaterial={(id, mat) => edit(() => {
              if (!doc) return
              const f = findFeature(doc, id)
              if (f) (f as any).material = mat
            })}
            onUpdateQRValue={(id, val) => edit(() => {
              if (!doc) return
              const f = findFeature(doc, id)
              if (f) (f as any).value = val
            })}
            onUpdateQRSize={(id, sz) => edit(() => {
              if (!doc) return
              const f = findFeature(doc, id)
              if (f) {
                if (typeof f.size === 'number') (f as any).size = sz
                else if (f.size) (f.size as any).width = sz
              }
            })}
          />
        </div>
      </div>

      {/* Bottom */}
      <div style={S.bottom}>
        <ManufacturingPanel report={report} errors={[]} />
        <BuildConsole isBuilding={false} messages={[]} />
      </div>

      {/* Publish Dialog */}
      <PublishDialog
        result={publishResult}
        documentJson={doc ? JSON.stringify(doc, null, 2) : null}
        documentId={doc?.document?.id ?? 'document'}
        onClose={() => setPublishResult(null)}
      />
    </div>
  )
}

// ── DocTree ────────────────────────────────────────────────────────────
function DocTree({ doc, sel, onSel }: { doc: CardForgeDocument | null; sel: string | null; onSel: (id: string) => void }) {
  if (!doc) return <div style={{ fontSize: 12, color: '#484f58', fontStyle: 'italic' }}>New Card to start</div>
  const st = { s: { marginBottom: 12 }, t: { fontSize: 11, fontWeight: 600, color: '#8b949e', textTransform: 'uppercase' as const, marginBottom: 4 },
    i: { fontSize: 12, padding: '3px 8px', borderRadius: 4, cursor: 'pointer', color: '#c9d1d9' },
    a: { fontSize: 12, padding: '3px 8px', borderRadius: 4, cursor: 'pointer', background: '#1f6feb33', color: '#58a6ff' } }
  return <div>{doc.objects.map((obj: any) => <div key={obj.id} style={st.s}>
    <div style={st.t}>{obj.type}</div>
    {Object.entries(obj.faces).map(([fid, face]: [string, any]) => <div key={fid} style={{ marginLeft: 8 }}>
      <div style={{ fontSize: 11, color: '#8b949e', marginTop: 4 }}>{fid}</div>
      {face.features.map((feat: any) => <div key={feat.id} style={sel === feat.id ? st.a : st.i} onClick={() => onSel(feat.id)}>{feat.type} — {feat.id}</div>)}
    </div>)}</div>)}</div>
}

// ── VariablesPanel ────────────────────────────────────────────────────
function VariablesPanel({ doc, onUpdate }: { doc: CardForgeDocument | null; onUpdate: (k: string, v: string) => void }) {
  if (!doc) return null
  const st = { s: { marginTop: 16 }, t: { fontSize: 11, fontWeight: 600, color: '#8b949e', textTransform: 'uppercase' as const, marginBottom: 6 },
    r: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12, padding: '2px 0' },
    l: { color: '#8b949e', fontSize: 11 }, inp: { background: '#0d1117', color: '#c9d1d9', border: '1px solid #30363d', borderRadius: 4, padding: '2px 6px', fontSize: 11, width: 140 } }
  const vars = doc.variables ?? {}
  return <div style={st.s}>
    <div style={st.t}>Variables</div>
    {['name', 'title', 'email', 'website', 'phone'].map(k => (
      <div key={k} style={st.r}>
        <span style={st.l}>{k}</span>
        <input style={st.inp} value={vars[k] ?? ''}
          onChange={e => onUpdate(k, e.target.value)} />
      </div>
    ))}
  </div>
}
