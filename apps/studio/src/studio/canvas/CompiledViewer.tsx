// CompiledViewer — renders the EXACT 3MF bytes the Core returned.
//
// Fidelity guarantee: no geometry is reimplemented here. The base64 3MF
// from CompileStore is parsed with three's ThreeMFLoader and displayed
// with orbit controls, render modes, per-part visibility and explode view.

import React, { useRef, useEffect, useState, useCallback } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { ThreeMFLoader } from 'three/examples/jsm/loaders/3MFLoader.js'
import { useCompileStore } from '../../state/CompileStore'

type RenderMode = 'solid' | 'wireframe' | 'solid-edges'

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

  const containerRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<SceneRefs | null>(null)
  const animRef = useRef<number>(0)

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

    const grid = new THREE.GridHelper(120, 20, '#30363d', '#21262d')
    grid.position.y = -2
    scene.add(grid)

    sceneRef.current = { scene, camera, renderer, controls, model: null, partMeshes: new Map(), fittedOnce: false }

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
        const existing = s.partMeshes.get(name)
        if (existing) {
          existing.push(obj)
        } else {
          s.partMeshes.set(name, [obj])
          const mat = (Array.isArray(obj.material) ? obj.material[0] : obj.material) as THREE.MeshPhongMaterial
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

      // Center the model at the origin
      const box = new THREE.Box3().setFromObject(group)
      const center = box.getCenter(new THREE.Vector3())
      group.position.sub(center)

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
      </div>

      {/* Part legend */}
      {parts.length > 0 && (
        <div style={{ position: 'absolute', top: 8, right: 8, zIndex: 10, background: '#161b22', border: '1px solid #30363d', borderRadius: 6, padding: 8 }}>
          {parts.map(p => {
            const visible = !hiddenParts.has(p.name)
            return (
              <div key={p.name} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '2px 0', cursor: 'pointer' }}
                onClick={() => togglePart(p.name)}>
                <span style={{
                  width: 12, height: 12, borderRadius: 2,
                  background: visible ? p.color : '#30363d',
                  border: `1px solid ${p.color}`,
                }} />
                <span style={{ fontSize: 11, color: visible ? '#c9d1d9' : '#484f58' }}>{p.name}</span>
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
