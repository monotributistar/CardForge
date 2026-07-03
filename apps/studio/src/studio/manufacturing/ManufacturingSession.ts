// ManufacturingSession — orchestrates the full manufacture flow
//
// Handles: API call → job polling → manifest parsing → STL download → compiled view

import { HTTPTransport, type ApiManufactureResponse, type ApiJobResponse } from '../core/HTTPTransport'
import type { STLPart } from '../canvas/CompiledViewer'
import type { ManufacturingConfig } from './ManufacturingPipeline'

export interface SessionStep {
  name: string
  status: 'pending' | 'running' | 'done' | 'failed'
  durationMs?: number
}

export interface ManufacturingSession {
  jobId: string | null
  status: 'idle' | 'compiling' | 'manufacturing' | 'loading' | 'done' | 'failed'
  progress: number
  steps: SessionStep[]
  manifest: any | null
  parts: STLPart[]
  error: string | null
  logs: string[]
}

const DEFAULT_SESSION: ManufacturingSession = {
  jobId: null,
  status: 'idle',
  progress: 0,
  steps: [],
  manifest: null,
  parts: [],
  error: null,
  logs: [],
}

export type SessionUpdateFn = (patch: Partial<ManufacturingSession>) => void

const PART_COLORS = ['#3a3a3a', '#e0e0e0', '#d4af37', '#00cc66', '#ff6b35']

function log(msg: string, update: SessionUpdateFn) {
  const ts = new Date().toLocaleTimeString()
  update({ logs: [`[${ts}] ${msg}`] })
}

export async function runManufactureFlow(
  document: any,
  config: ManufacturingConfig,
  api: HTTPTransport,
  update: SessionUpdateFn,
): Promise<void> {
  const start = Date.now()
  const steps: SessionStep[] = [
    { name: 'Compiling document', status: 'pending' },
    { name: 'Manufacturing analysis', status: 'pending' },
    { name: 'Generating OpenSCAD', status: 'pending' },
    { name: 'Generating STL', status: 'pending' },
    { name: 'Generating reports', status: 'pending' },
    { name: 'Loading compiled preview', status: 'pending' },
  ]

  update({ status: 'compiling', progress: 5, steps: [...steps], error: null, logs: [] })

  // Step 1: Submit manufacture job
  steps[0].status = 'running'
  update({ steps: [...steps] })
  log('Submitting manufacture job...', update)

  let result: ApiManufactureResponse
  try {
    result = await api.manufacture(document, {
      singleStl: config.outputs.stl,
      parts: config.outputs.separatedStl,
    })
  } catch (e: any) {
    steps[0].status = 'failed'
    update({ status: 'failed', steps: [...steps], error: `API unavailable: ${e.message}` })
    log(`Failed: ${e.message}`, update)
    return
  }

  if (!result.ok || !result.jobId) {
    steps[0].status = 'failed'
    update({ status: 'failed', steps: [...steps], error: result.error || 'Manufacture failed' })
    log(`Failed: ${result.error}`, update)
    return
  }

  steps[0].status = 'done'
  update({ jobId: result.jobId, progress: 15, steps: [...steps] })
  log(`Job created: ${result.jobId}`, update)

  // Step 2: Poll for job completion
  steps[1].status = 'running'
  update({ steps: [...steps] })
  log('Waiting for job...', update)

  let completed = false
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 1000))
    try {
      const job = await api.jobStatus(result.jobId)
      if (job.status === 'completed') {
        completed = true
        break
      }
      if (job.status === 'failed') {
        steps[1].status = 'failed'
        update({ status: 'failed', steps: [...steps], error: 'Job failed on server' })
        return
      }
      update({ progress: 15 + Math.min(i * 2, 40) })
    } catch {
      // Keep polling
    }
  }

  if (!completed) {
    steps[1].status = 'failed'
    update({ status: 'failed', steps: [...steps], error: 'Job timed out' })
    return
  }

  steps[1].status = 'done'
  steps[2].status = 'done'
  steps[3].status = 'done'
  steps[4].status = 'done'
  update({ progress: 70, steps: [...steps] })

  // Step 3: Download manifest and STL files
  const files = result.package?.files ?? []
  const stlFiles = files.filter(f => f.type === 'stl' || f.type === 'stl_part')
  const manifest = result.package?.manifest ?? {}

  // Step 4: Load STL parts
  steps[5].status = 'running'
  update({ progress: 75, steps: [...steps] })
  log(`Loading ${stlFiles.length} STL files...`, update)

  const parts: STLPart[] = []
  for (let i = 0; i < stlFiles.length; i++) {
    const f = stlFiles[i]
    try {
      const url = api.getFileUrl(result.jobId, f.name)
      const buf = await api.downloadFile(url)
      const rawName = f.name.split('/').pop()?.replace('.stl', '') ?? `part-${i}`
      const matName = rawName.includes('base') ? 'Base · PLA' :
                      rawName.includes('text') ? 'Text · PLA' :
                      rawName.includes('accent') ? 'Accent · PLA' : rawName
      parts.push({ name: matName, color: PART_COLORS[i % PART_COLORS.length], data: buf })
      log(`Loaded: ${matName}`, update)
      update({ progress: 80 + Math.round((i / stlFiles.length) * 15) })
    } catch (e: any) {
      log(`Failed to load ${f.name}: ${e.message}`, update)
    }
  }

  steps[5].status = parts.length > 0 ? 'done' : 'failed'
  const totalMs = Date.now() - start
  update({
    status: 'done', progress: 100, steps: [...steps],
    manifest, parts,
    logs: [],
  })
  log(`Done in ${(totalMs / 1000).toFixed(1)}s — ${parts.length} parts loaded`, update)
}
