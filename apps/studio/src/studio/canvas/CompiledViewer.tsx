// CompiledViewer — renders the EXACT 3MF bytes the Core returned.
//
// Fidelity guarantee: no geometry is reimplemented here. The base64 3MF
// from CompileStore is parsed with three's ThreeMFLoader and displayed
// with orbit controls, render modes, per-part visibility and explode view.
// Parts are clickable: picking a mesh selects its feature in the
// DocumentStore, so the Inspector (right panel) shows it — same flow as
// the 2D design canvas. The grid is a 10 mm reference resting at y=0 and
// the model sits on top of it like on the printer bed.

import React, { useRef, useEffect, useState, useCallback } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { ThreeMFLoader } from 'three/examples/jsm/loaders/3MFLoader.js'
import { useCompileStore } from '../../state/CompileStore'
import { useDocumentStore, getActiveTab } from '../../state/DocumentStore'
import type { PartReport } from '../core/CoreClient'

type RenderMode = 'solid' | 'wireframe' | 'solid-edges'

const GRID_MM = 10 // one grid cell = 10 mm

interface PartInfo { name: string; color: string }

function base64ToArrayBuffer(b64: string): ArrayBuffer {
  const bin = atob(b64)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
  return bytes.buffer
}

interface SceneRefs {
  scene: THREE.Scene
  camera: THREE.PerspectiveCamera
  renderer: THREE.WebGLRenderer
  controls: OrbitControls
  model: THREE.Group | null
  /** part name → meshes (with original local z stored in userData.baseZ) */
  partMeshes: Map<string, THREE.Mesh[]>
  fittedOnce: boolean
}

export const CompiledViewer: React.FC = () => {
  const model3mfB64 = useCompileStore(s => s.model3mfB64)
  const status = useCompileStore(s => s.status)
  const compileError = useCompileStore(s => s.error)
  const compiledParts = useCompileStore(s => s.parts)
  const materials = useCompileStore(s => s.materials)

  const select = useDocumentStore(s => s.select)
  const selectObject = useDocumentStore(s => s.selectObject)
  const activeTab = useDocumentStore(getActiveTab)
  const selectedFeatureId = activeTab?.selectedFeatureId ?? null
  const objectSelected = activeTab?.objectSelected ?? false

  const containerRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<SceneRefs | null>(null)
  const animRef = useRef<number>(0)
  // Live values for the (once-attached) pointer handlers
  const pickRef = useRef<{ parts: PartReport[]; select: typeof select; selectObject: typeof selectObject }>({
    parts: [], select, selectObject,
  })
  pickRef.current = { parts: compiledParts, select, selectObject }

  const [renderMode, setRenderMode] = useState<RenderMode>('solid')
  const [explosion, setExplosion] = useState(0)
  const [hiddenParts, setHiddenParts] = useState<Set<string>>(new Set())
  const [parts, setParts] = useState<PartInfo[]>([])
  const [parseError, setParseError] = useState<string | null>(null)

  // ── Init Three.js ─────────────────────────────────────────────────
  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#0d1117')

    const camera = new THREE.PerspectiveCamera(45, el.clientWidth / Math.max(1, el.clientHeight), 0.1, 1000)
    camera.position.set(80, 40, 120)
    camera.lookAt(0, 0, 0)

    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true })
    renderer.setSize(el.clientWidth, el.clientHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    el.appendChild(renderer.domElement)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.1
    controls.target.set(0, 0, 0)

    scene.add(new THREE.AmbientLight(0x404060, 2))
    const dir1 = new THREE.DirectionalLight(0xffffff, 1.5)
    dir1.position.set(1, 1, 1)
    scene.add(dir1)
    const dir2 = new THREE.DirectionalLight(0x8899cc, 0.8)
    dir2.position.set(-1, -0.5, -0.5)
    scene.add(dir2)

    // Bed reference: grid at y=0, one cell = GRID_MM millimeters
    const grid = new THREE.GridHelper(160, 160 / GRID_MM, '#3d444d', '#21262d')
    grid.position.y = 0
    scene.add(grid)

    sceneRef.current = { scene, camera, renderer, controls, model: null, partMeshes: new Map(), fittedOnce: false }

    // ── Click-to-select (click = press+release without dragging) ────
    const raycaster = new THREE.Raycaster()
    let downAt: { x: number; y: number } | null = null
    const onDown = (e: PointerEvent) => { downAt = { x: e.clientX, y: e.clientY } }
    const onUp = (e: PointerEvent) => {
      const s = sceneRef.current
      if (!s || !downAt) return
      const moved = Math.hypot(e.clientX - downAt.x, e.clientY - downAt.y)
      downAt = null
      if (moved > 5) return // it was an orbit drag
      const rect = renderer.domElement.getBoundingClientRect()
      const ndc = new THREE.Vector2(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1,
      )
      raycaster.setFromCamera(ndc, s.camera)
      const meshes: THREE.Mesh[] = []
      s.partMeshes.forEach(list => list.forEach(m => { if (m.visible) meshes.push(m) }))
      const hits = raycaster.intersectObjects(meshes, false)
      const { parts: manifest, select: doSelect, selectObject: doSelectObject } = pickRef.current
      if (!hits.length) return
      // resolve the part label of the hit mesh (name lives on mesh or ancestor)
      let node: THREE.Object3D | null = hits[0].object
      let label = ''
      while (node && !label) { label = node.name; node = node.parent }
      const part = manifest.find(p => p.label === label)
      if (!part) return
      if (part.featureId) doSelect(part.featureId)
      else doSelectObject()
    }
    renderer.domElement.addEventListener('pointerdown', onDown)
    renderer.domElement.addEventListener('pointerup', onUp)

    const animate = () => {
      animRef.current = requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    const obs = new ResizeObserver(() => {
      const s = sceneRef.current
      if (!s || !el.clientWidth || !el.clientHeight) return
      s.camera.aspect = el.clientWidth / el.clientHeight
      s.camera.updateProjectionMatrix()
      s.renderer.setSize(el.clientWidth, el.clientHeight)
    })
    obs.observe(el)

    return () => {
      cancelAnimationFrame(animRef.current)
      obs.disconnect()
      renderer.domElement.removeEventListener('pointerdown', onDown)
      renderer.domElement.removeEventListener('pointerup', onUp)
      controls.dispose()
      renderer.dispose()
      if (el.contains(renderer.domElement)) el.removeChild(renderer.domElement)
      sceneRef.current = null
    }
  }, [])

  // ── (Re)load the 3MF whenever the compiled bytes change ──────────
  useEffect(() => {
    const s = sceneRef.current
    if (!s) return

    // Remove previous model
    if (s.model) {
      s.scene.remove(s.model)
      s.model.traverse(o => {
        if (o instanceof THREE.Mesh || o instanceof THREE.LineSegments) {
          o.geometry.dispose()
          const mat = o.material as THREE.Material | THREE.Material[]
          if (Array.isArray(mat)) mat.forEach(m => m.dispose())
          else mat.dispose()
        }
      })
      s.model = null
    }
    s.partMeshes.clear()

    if (!model3mfB64) {
      setParts([])
      setParseError(null)
      return
    }

    try {
      const loader = new ThreeMFLoader()
      const group = loader.parse(base64ToArrayBuffer(model3mfB64))

      // 3MF is z-up; three.js is y-up.
      group.rotation.x = -Math.PI / 2

      // Collect named meshes (names come from the 3MF object names)
      const partList: PartInfo[] = []
      let unnamed = 0
      group.traverse(obj => {
        if (!(obj instanceof THREE.Mesh)) return
        let name = obj.name
        if (!name) {
          // fall back to nearest named ancestor, else a numbered part
          let p: THREE.Object3D | null = obj.parent
          while (p && p !== group && !p.name) p = p.parent
          name = (p && p !== group && p.name) || `part-${++unnamed}`
        }
        obj.userData.baseZ = obj.position.z
        // Own material instance per mesh so selection highlight stays local
        obj.material = (Array.isArray(obj.material) ? obj.material[0] : obj.material).clone()
        const existing = s.partMeshes.get(name)
        if (existing) {
          existing.push(obj)
        } else {
          s.partMeshes.set(name, [obj])
          const mat = obj.material as THREE.MeshPhongMaterial
          const color = mat?.color ? `#${mat.color.getHexString()}` : '#8b949e'
          partList.push({ name, color })
        }
        // Edge overlay (as child so it inherits the mesh transform)
        const edges = new THREE.LineSegments(
          new THREE.EdgesGeometry(obj.geometry, 15),
          new THREE.LineBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.35 }),
        )
        edges.name = '__edges'
        obj.add(edges)
      })

      // Rest the model on the bed plane (y=0), centered in x/z — like the
      // printer plate. z in kernel space is already bed-normalized.
      const box = new THREE.Box3().setFromObject(group)
      const center = box.getCenter(new THREE.Vector3())
      group.position.x -= center.x
      group.position.z -= center.z
      group.position.y -= box.min.y

      s.scene.add(group)
      s.model = group
      setParts(partList)
      setParseError(null)
      // Prune stale hidden entries but keep user's choices for stable names
      setHiddenParts(prev => {
        const next = new Set([...prev].filter(n => s.partMeshes.has(n)))
        return next.size === prev.size ? prev : next
      })

      // Fit camera only on the very first load — keep it across reloads
      if (!s.fittedOnce) {
        const size = box.getSize(new THREE.Vector3())
        const maxDim = Math.max(size.x, size.y, size.z, 1)
        s.camera.position.set(maxDim * 1.2, maxDim * 0.9, maxDim * 1.5)
        s.controls.target.set(0, 0, 0)
        s.controls.update()
        s.fittedOnce = true
      }
    } catch (e) {
      setParts([])
      setParseError(e instanceof Error ? e.message : String(e))
    }
  }, [model3mfB64])

  // ── Apply render mode / visibility / explosion ────────────────────
  useEffect(() => {
    const s = sceneRef.current
    if (!s) return
    let idx = 0
    s.partMeshes.forEach((meshes, name) => {
      const visible = !hiddenParts.has(name)
      for (const mesh of meshes) {
        mesh.visible = visible
        const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material]
        for (const m of mats) (m as THREE.MeshPhongMaterial).wireframe = renderMode === 'wireframe'
        const edges = mesh.children.find(c => c.name === '__edges')
        if (edges) edges.visible = renderMode === 'solid-edges'
        mesh.position.z = (mesh.userData.baseZ as number ?? 0) + idx * explosion * 5
      }
      idx++
    })
  }, [renderMode, hiddenParts, explosion, parts])

  // ── Highlight the selected part (mirrors 2D/tree selection) ───────
  const selectedLabels = new Set(
    compiledParts
      .filter(p => (p.featureId ? p.featureId === selectedFeatureId
                    : objectSelected && p.id === 'base'))
      .map(p => p.label),
  )
  const selectedKey = [...selectedLabels].sort().join('|')
  useEffect(() => {
    const s = sceneRef.current
    if (!s) return
    s.partMeshes.forEach((meshes, name) => {
      const on = selectedLabels.has(name)
      for (const mesh of meshes) {
        const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material]
        for (const m of mats) {
          const pm = m as THREE.MeshPhongMaterial
          if (pm.emissive) pm.emissive.setHex(on ? 0x1f4d8f : 0x000000)
        }
      }
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedKey, parts])

  const togglePart = useCallback((name: string) => {
    setHiddenParts(prev => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }, [])

  const resetCamera = useCallback(() => {
    const s = sceneRef.current
    if (!s) return
    s.camera.position.set(80, 40, 120)
    s.controls.target.set(0, 0, 0)
    s.controls.update()
  }, [])

  const fitCamera = useCallback(() => {
    const s = sceneRef.current
    if (!s || !s.model) return
    const box = new THREE.Box3().setFromObject(s.model)
    if (box.isEmpty()) return
    const size = box.getSize(new THREE.Vector3())
    const center = box.getCenter(new THREE.Vector3())
    const maxDim = Math.max(size.x, size.y, size.z, 1)
    s.camera.position.set(center.x + maxDim * 1.2, center.y + maxDim * 0.9, center.z + maxDim * 1.5)
    s.controls.target.copy(center)
    s.controls.update()
  }, [])

  const cycleMode = () => setRenderMode(m => m === 'solid' ? 'solid-edges' : m === 'solid-edges' ? 'wireframe' : 'solid')

  // Selected part(s) info for the dimensions overlay
  const selectedParts = compiledParts.filter(p => selectedLabels.has(p.label))
  const matById = new Map(materials.map(m => [m.id, m]))
  const fmt = (n: number) => (Math.round(n * 100) / 100).toString()

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', position: 'relative', minHeight: 0 }}>
      {/* Toolbar */}
      <div style={{ position: 'absolute', top: 8, left: 8, zIndex: 10, display: 'flex', gap: 4, alignItems: 'center' }}>
        <Btn onClick={resetCamera}>Reset</Btn>
        <Btn onClick={fitCamera}>Fit</Btn>
        <Btn onClick={cycleMode}>
          {renderMode === 'solid' ? 'Solid' : renderMode === 'wireframe' ? 'Wire' : 'Solid+E'}
        </Btn>
        <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: '#8b949e', background: '#161b22', border: '1px solid #30363d', borderRadius: 4, padding: '2px 8px' }}>
          Explode
          <input
            type="range" min={0} max={1} step={0.01} value={explosion}
            onChange={e => setExplosion(Number(e.target.value))}
            style={{ width: 70 }}
          />
        </label>
        <span style={{ fontSize: 10, color: '#484f58', background: '#161b22', border: '1px solid #30363d', borderRadius: 4, padding: '2px 8px' }}>
          Grid {GRID_MM} mm
        </span>
      </div>

      {/* Part legend — click a part in the 3D view or here to inspect it */}
      {parts.length > 0 && (
        <div style={{ position: 'absolute', top: 8, right: 8, zIndex: 10, background: '#161b22', border: '1px solid #30363d', borderRadius: 6, padding: 8 }}>
          {parts.map(p => {
            const visible = !hiddenParts.has(p.name)
            const info = compiledParts.find(cp => cp.label === p.name)
            const isSel = selectedLabels.has(p.name)
            const size = info ? `${fmt(info.sizeMm[0])} × ${fmt(info.sizeMm[1])} × ${fmt(info.sizeMm[2])} mm` : ''
            return (
              <div key={p.name}
                title={size}
                style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '2px 4px', cursor: 'pointer', borderRadius: 4, background: isSel ? 'rgba(88,166,255,0.15)' : 'transparent' }}
                onClick={() => {
                  if (info) { if (info.featureId) select(info.featureId); else selectObject() }
                }}>
                <span
                  onClick={e => { e.stopPropagation(); togglePart(p.name) }}
                  title="Show/hide part"
                  style={{
                    width: 12, height: 12, borderRadius: 2,
                    background: visible ? p.color : '#30363d',
                    border: `1px solid ${p.color}`,
                  }} />
                <span style={{ fontSize: 11, color: isSel ? '#58a6ff' : visible ? '#c9d1d9' : '#484f58' }}>{p.name}</span>
              </div>
            )
          })}
        </div>
      )}

      {/* Selected part dimensions (mm) */}
      {selectedParts.length > 0 && (
        <div style={{ position: 'absolute', bottom: 8, right: 8, zIndex: 10, background: '#161b22', border: '1px solid #30363d', borderRadius: 6, padding: '6px 10px', fontSize: 11, color: '#c9d1d9' }}>
          {selectedParts.map(p => {
            const mat = matById.get(p.material)
            return (
              <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '1px 0' }}>
                <span style={{ width: 10, height: 10, borderRadius: 2, background: mat?.color ?? '#8b949e', flexShrink: 0 }} />
                <span style={{ color: '#8b949e' }}>{p.label}</span>
                <span>{fmt(p.sizeMm[0])} × {fmt(p.sizeMm[1])} × {fmt(p.sizeMm[2])} mm</span>
                <span style={{ color: '#484f58' }}>z {fmt(p.zMm[0])}–{fmt(p.zMm[1])}</span>
              </div>
            )
          })}
        </div>
      )}

      {/* Status overlays */}
      {status === 'compiling' && (
        <div style={{ position: 'absolute', bottom: 8, left: 8, zIndex: 10, color: '#d29922', fontSize: 11, background: '#161b22', border: '1px solid #30363d', borderRadius: 4, padding: '2px 8px' }}>
          Compiling…
        </div>
      )}
      {parseError && (
        <div style={{ position: 'absolute', bottom: 8, left: 8, right: 8, zIndex: 10, color: '#f85149', fontSize: 11, background: '#161b22', border: '1px solid #f85149', borderRadius: 4, padding: '4px 8px' }}>
          Failed to parse 3MF: {parseError}
        </div>
      )}
      {!model3mfB64 && !parseError && (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 5, color: '#484f58', fontSize: 13, pointerEvents: 'none' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>📦</div>
            <div>{status === 'error' ? 'Compile failed' : 'No compiled model yet'}</div>
            {status === 'error' && compileError && (
              <div style={{ fontSize: 11, marginTop: 4, maxWidth: 360 }}>{compileError}</div>
            )}
          </div>
        </div>
      )}

      <div ref={containerRef} style={{ flex: 1, minHeight: 0 }} />
    </div>
  )
}

const Btn: React.FC<{ onClick: () => void; children: React.ReactNode; style?: React.CSSProperties }> = ({ onClick, children, style }) => (
  <button onClick={onClick} style={{
    background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d',
    padding: '2px 10px', borderRadius: 4, cursor: 'pointer', fontSize: 11, ...style,
  }}>{children}</button>
)
