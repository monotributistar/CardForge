// Selection — selection model for the Studio
//
// All feature selection flows through this module.
// Components should never use raw strings for selection state.

import type { FeatureId } from '../types'

export interface SelectionState {
  selectedFeatureId: FeatureId | null
}

export interface SelectionActions {
  select: (featureId: FeatureId | null) => void
  clear: () => void
  isSelected: (featureId: FeatureId) => boolean
}

export class SelectionModel {
  state: SelectionState
  actions: SelectionActions

  constructor() {
    this.state = { selectedFeatureId: null }
    this.actions = {
      select: (id) => { this.state = { selectedFeatureId: id } },
      clear: () => { this.state = { selectedFeatureId: null } },
      isSelected: (id) => this.state.selectedFeatureId === id,
    }
  }

  get selectedFeatureId() { return this.state.selectedFeatureId }
  get hasSelection() { return this.state.selectedFeatureId !== null }
}
