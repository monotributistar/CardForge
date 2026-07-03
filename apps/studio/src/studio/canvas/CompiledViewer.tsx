// CompiledViewer — 3D STL inspector using Three.js
//
// Renders compiled STL files with orbit controls, render modes,
// exploded view, material visibility toggles.

import React, { useRef, useEffect, useState, useCallback } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js'

// ── Types ────────────────────────────────────────────────────────────

export interface STLPart {
  name: string
  color: string
  data: ArrayBuffer
}

export interface CompiledViewerProps {
  parts: STLPart[]
  visibleParts: Set<string>
  onTogglePart: (name: string) => void
  explosion: number // 0–1
  renderMode: 'solid' | 'wireframe' | 'solid-edges'
}

// ── Component ────────────────────────────────────────────────────────

export const CompiledViewer: React.FC<CompiledViewerProps> = ({
  parts, visibleParts, onTogglePart, explosion, renderMode,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const [loading, setLoading] = useState(false)
  const sceneRef = useRef<{ scene: THREE.Scene; camera: THREE.PerspectiveCamera; renderer: THREE.WebGLRenderer; controls: OrbitControls; meshes: Map<string, THREE.Group> } | null>(null)
  const animRef = useRef<number>(0)

  // Init Three.js
  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#0d1117')

    const camera = new THREE.PerspectiveCamera(45, el.clientWidth / el.clientHeight, 0.1, 500)
    camera.position.set(80, 40, 120)
    camera.lookAt(0, 0, 0)

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(el.clientWidth, el.clientHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    el.appendChild(renderer.domElement)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.1
    controls.target.set(0, 0, 0)

    // Lights
    scene.add(new THREE.AmbientLight(0x404060, 2))
    const dir1 = new THREE.DirectionalLight(0xffffff, 1.5)
    dir1.position.set(1, 1, 1)
    scene.add(dir1)
    const dir2 = new THREE.DirectionalLight(0x8899cc, 0.8)
    dir2.position.set(-1, -0.5, -0.5)
    scene.add(dir2)

    // Grid helper
    const grid = new THREE.GridHelper(120, 20, '#30363d', '#21262d')
    scene.add(grid)

    sceneRef.current = { scene, camera, renderer, controls, meshes: new Map() }

    const animate = () => {
      animRef.current = requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    const handleResize = () => {
      if (!el || !sceneRef.current) return
      const { camera: cam, renderer: r } = sceneRef.current
      cam.aspect = el.clientWidth / el.clientHeight
      cam.updateProjectionMatrix()
      r.setSize(el.clientWidth, el.clientHeight)
    }
    window.addEventListener('resize', handleResize)

    return () => {
      cancelAnimationFrame(animRef.current)
      window.removeEventListener('resize', handleResize)
      renderer.dispose()
      if (el.contains(renderer.domElement)) el.removeChild(renderer.domElement)
    }
  }, [])

  // Load STL parts
  useEffect(() => {
    const s = sceneRef.current
    if (!s) return
    const { scene, meshes } = s

    // Remove old meshes
    meshes.forEach(g => scene.remove(g))
    meshes.clear()

    if (parts.length === 0) return
    setLoading(true)

    const loader = new STLLoader()
    let loaded = 0

    const expY = explosion * 5 // mm separation per unit

    parts.forEach((part, idx) => {
      const geometry = loader.parse(part.data)
      const material = new THREE.MeshPhongMaterial({
        color: new THREE.Color(part.color),
        specular: 0x111111,
        shininess: 30,
        flatShading: false,
      })

      const mesh = new THREE.Mesh(geometry, material)
      mesh.name = part.name
      mesh.visible = visibleParts.has(part.name)

      // Center geometry
      geometry.computeBoundingBox()
      const box = geometry.boundingBox!
      const cx = (box.max.x + box.min.x) / 2
      const cy = (box.max.y + box.min.y) / 2
      const cz = (box.max.z + box.min.z) / 2
      mesh.position.set(-cx, -cy + idx * expY, -cz)

      // Edges for solid-edges mode
      const edgesGeo = new THREE.EdgesGeometry(geometry, 15)
      const edgesMat = new THREE.LineBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.3 })
      const edges = new THREE.LineSegments(edgesGeo, edgesMat)
      edges.name = part.name + '-edges'
      edges.visible = renderMode === 'solid-edges'

      const group = new THREE.Group()
      group.add(mesh)
      group.add(edges)
      group.name = part.name

      scene.add(group)
      meshes.set(part.name, group)
      loaded++
      if (loaded >= parts.length) setLoading(false)
    })

    // Fit camera
    if (parts.length > 0) {
      const box = new THREE.Box3()
      meshes.forEach(g => {
        g.children.forEach(c => {
          if (c instanceof THREE.Mesh) box.expandByObject(c)
        })
      })
      const size = box.getSize(new THREE.Vector3())
      const center = box.getCenter(new THREE.Vector3())
      const maxDim = Math.max(size.x, size.y, size.z)
      const cam = s.camera
      cam.position.set(center.x + maxDim * 1.5, center.y + maxDim * 0.8, center.z + maxDim * 1.5)
      s.controls.target.copy(center)
      s.controls.update()
    }
  }, [parts, explosion])

  // Update visibility
  useEffect(() => {
    const s = sceneRef.current
    if (!s) return
    s.meshes.forEach((group, name) => {
      const visible = visibleParts.has(name)
      group.children.forEach(c => {
        if (c instanceof THREE.Mesh) c.visible = visible
        if (c instanceof THREE.LineSegments) c.visible = visible && renderMode === 'solid-edges'
      })
    })
  }, [visibleParts])

  // Update render mode
  useEffect(() => {
    const s = sceneRef.current
    if (!s) return
    s.meshes.forEach((group, name) => {
      group.children.forEach(c => {
        if (c instanceof THREE.Mesh) {
          const mat = c.material as THREE.MeshPhongMaterial
          mat.wireframe = renderMode === 'wireframe'
        }
        if (c instanceof THREE.LineSegments) {
          c.visible = renderMode === 'solid-edges' && visibleParts.has(name)
        }
      })
    })
  }, [renderMode, visibleParts])

  // Update explosion positions
  useEffect(() => {
    const s = sceneRef.current
    if (!s) return
    const expY = explosion * 5
    let idx = 0
    s.meshes.forEach((group, name) => {
      group.children.forEach(c => {
        if (c instanceof THREE.Mesh) {
          const box = new THREE.Box3().setFromObject(c)
          const cy = (box.max.y + box.min.y) / 2
          c.position.y = -cy + idx * expY
        }
      })
      idx++
    })
  }, [explosion])

  const resetCamera = useCallback(() => {
    const s = sceneRef.current
    if (!s) return
    s.camera.position.set(80, 40, 120)
    s.controls.target.set(0, 0, 0)
    s.controls.update()
  }, [])

  const fitCamera = useCallback(() => {
    const s = sceneRef.current
    if (!s) return
    const box = new THREE.Box3()
    s.meshes.forEach(g => {
      g.children.forEach(c => {
        if (c instanceof THREE.Mesh && c.visible) box.expandByObject(c)
      })
    })
    if (box.isEmpty()) return
    const size = box.getSize(new THREE.Vector3())
    const center = box.getCenter(new THREE.Vector3())
    const maxDim = Math.max(size.x, size.y, size.z)
    s.camera.position.set(center.x + maxDim * 1.5, center.y + maxDim * 0.8, center.z + maxDim * 1.5)
    s.controls.target.copy(center)
    s.controls.update()
  }, [])

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', position: 'relative' }}>
      {/* Toolbar */}
      <div style={{ position: 'absolute', top: 8, left: 8, zIndex: 10, display: 'flex', gap: 4 }}>
        <Btn onClick={resetCamera}>Reset</Btn>
        <Btn onClick={fitCamera}>Fit</Btn>
        <Btn onClick={() => {}} style={{ color: '#484f58', cursor: 'default' }}>
          {renderMode === 'solid' ? 'Solid' : renderMode === 'wireframe' ? 'Wire' : 'Solid+E'}
        </Btn>
      </div>

      {/* Part legend */}
      {parts.length > 0 && (
        <div style={{ position: 'absolute', top: 8, right: 8, zIndex: 10, background: '#161b22', border: '1px solid #30363d', borderRadius: 6, padding: 8 }}>
          {parts.map(p => (
            <div key={p.name} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '2px 0', cursor: 'pointer' }}
              onClick={() => onTogglePart(p.name)}>
              <span style={{
                width: 12, height: 12, borderRadius: 2,
                background: visibleParts.has(p.name) ? p.color : '#30363d',
                border: `1px solid ${p.color}`,
              }} />
              <span style={{ fontSize: 11, color: visibleParts.has(p.name) ? '#c9d1d9' : '#484f58' }}>{p.name}</span>
            </div>
          ))}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 5 }}>
          <span style={{ color: '#8b949e', fontSize: 14 }}>Loading STL...</span>
        </div>
      )}

      {/* Empty state */}
      {!loading && parts.length === 0 && (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 5, color: '#484f58', fontSize: 13 }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>📦</div>
            <div>No compiled output loaded</div>
            <div style={{ fontSize: 11, marginTop: 4 }}>Load STL files to inspect</div>
          </div>
        </div>
      )}

      <div ref={containerRef} style={{ flex: 1 }} />
    </div>
  )
}

const Btn: React.FC<{ onClick: () => void; children: React.ReactNode; style?: React.CSSProperties }> = ({ onClick, children, style }) => (
  <button onClick={onClick} style={{
    background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d',
    padding: '2px 10px', borderRadius: 4, cursor: 'pointer', fontSize: 11, ...style,
  }}>{children}</button>
)
