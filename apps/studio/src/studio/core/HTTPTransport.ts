// HTTPTransport — connects Studio to Core API via HTTP
//
// Replaces CLI bridge when API server is running.

const API_BASE = 'http://localhost:9000'

export interface ApiPreviewResponse {
  ok: boolean
  error?: string
  preview: { frontSvg: string; backSvg: string }
  manufacturing: {
    score: number; scoreLabel: string; isManufacturable: boolean
    errorCount: number; warningCount: number
    warnings: Array<{ code: string; message: string; suggestion?: string }>
    errors: Array<{ code: string; message: string }>
    suggestions: string[]
  }
}

export interface ApiManufactureResponse {
  ok: boolean
  error?: string
  jobId?: string
  status?: string
  package?: {
    manifest: any
    files: ApiFileEntry[]
  }
}

export interface ApiFileEntry {
  name: string
  type: string
  url: string
}

export interface ApiJobResponse {
  ok: boolean
  jobId: string
  status: string
  progress?: number
  steps?: Array<{ name: string; status: string }>
}

export class HTTPTransport {
  private base: string

  constructor(base: string = API_BASE) {
    this.base = base
  }

  async health(): Promise<boolean> {
    try {
      const res = await fetch(`${this.base}/api/health`)
      const data = await res.json()
      return data.ok === true
    } catch { return false }
  }

  async preview(document: any, profile?: string): Promise<ApiPreviewResponse> {
    const res = await fetch(`${this.base}/api/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document, profile }),
    })
    return res.json()
  }

  async manufacture(document: any, options?: { singleStl?: boolean; parts?: boolean }): Promise<ApiManufactureResponse> {
    const res = await fetch(`${this.base}/api/manufacture`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document, options }),
    })
    return res.json()
  }

  async jobStatus(jobId: string): Promise<ApiJobResponse> {
    const res = await fetch(`${this.base}/api/jobs/${jobId}`)
    return res.json()
  }

  getFileUrl(jobId: string, path: string): string {
    return `${this.base}/api/files/${jobId}/${path}`
  }

  async downloadFile(url: string): Promise<ArrayBuffer> {
    const res = await fetch(url)
    return res.arrayBuffer()
  }
}
