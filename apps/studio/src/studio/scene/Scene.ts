// Scene — represents what is being visualized in the Canvas
//
// The Scene is a Studio-layer concept. It does NOT modify Geometry IR.
// It tracks which face is visible, zoom/pan state, and selection context.

import type { FaceId } from '../types'

export interface SceneState {
  /** Currently visible face */
  activeFace: FaceId

  /** Feature currently under hover (future) */
  hoveredFeatureId: string | null

  /** Features that should be hidden */
  hiddenFeatures: Set<string>
}

export interface SceneActions {
  setActiveFace: (face: FaceId) => void
  toggleActiveFace: () => void
  setHovered: (featureId: string | null) => void
  hideFeature: (featureId: string) => void
  showFeature: (featureId: string) => void
}

export class Scene {
  state: SceneState
  actions: SceneActions

  constructor() {
    this.state = {
      activeFace: 'front',
      hoveredFeatureId: null,
      hiddenFeatures: new Set(),
    }
    this.actions = {
      setActiveFace: (face) => { this.state = { ...this.state, activeFace: face } },
      toggleActiveFace: () => {
        this.state = {
          ...this.state,
          activeFace: this.state.activeFace === 'front' ? 'back' : 'front',
        }
      },
      setHovered: (id) => { this.state = { ...this.state, hoveredFeatureId: id } },
      hideFeature: (id) => {
        const next = new Set(this.state.hiddenFeatures)
        next.add(id)
        this.state = { ...this.state, hiddenFeatures: next }
      },
      showFeature: (id) => {
        const next = new Set(this.state.hiddenFeatures)
        next.delete(id)
        this.state = { ...this.state, hiddenFeatures: next }
      },
    }
  }

  get activeFace() { return this.state.activeFace }
  get hoveredFeatureId() { return this.state.hoveredFeatureId }
  isVisible(featureId: string) { return !this.state.hiddenFeatures.has(featureId) }
}
