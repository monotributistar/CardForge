// Viewport — controls the visual viewport state (zoom, offset, fit)
//
// Manages how the Canvas is viewed. Independent of Scene content.

export interface ViewportState {
  zoom: number
  offsetX: number
  offsetY: number
  showGrid: boolean
  showBounds: boolean
}

export interface ViewportActions {
  setZoom: (zoom: number) => void
  zoomIn: (step?: number) => void
  zoomOut: (step?: number) => void
  resetZoom: () => void
  setOffset: (x: number, y: number) => void
  fitToView: () => void
  toggleGrid: () => void
  toggleBounds: () => void
}

const MIN_ZOOM = 0.25
const MAX_ZOOM = 4.0
const DEFAULT_ZOOM = 1.0

export class Viewport {
  state: ViewportState
  actions: ViewportActions

  constructor() {
    this.state = {
      zoom: DEFAULT_ZOOM,
      offsetX: 0,
      offsetY: 0,
      showGrid: false,
      showBounds: false,
    }
    this.actions = {
      setZoom: (z) => {
        this.state = { ...this.state, zoom: Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, z)) }
      },
      zoomIn: (step = 0.25) => {
        this.actions.setZoom(this.state.zoom + step)
      },
      zoomOut: (step = 0.25) => {
        this.actions.setZoom(this.state.zoom - step)
      },
      resetZoom: () => {
        this.state = { ...this.state, zoom: DEFAULT_ZOOM, offsetX: 0, offsetY: 0 }
      },
      setOffset: (x, y) => {
        this.state = { ...this.state, offsetX: x, offsetY: y }
      },
      fitToView: () => {
        // Placeholder — future: compute zoom to fit card in viewport
        this.state = { ...this.state, zoom: 1.0, offsetX: 0, offsetY: 0 }
      },
      toggleGrid: () => {
        this.state = { ...this.state, showGrid: !this.state.showGrid }
      },
      toggleBounds: () => {
        this.state = { ...this.state, showBounds: !this.state.showBounds }
      },
    }
  }

  get zoom() { return this.state.zoom }
}
