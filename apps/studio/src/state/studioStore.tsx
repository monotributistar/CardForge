// CardForge Studio — React Context state store

import { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import type { CardForgeDocument, ManufacturingReport, DocumentObject, Feature, Face } from '../types/cardforge'

export interface StudioState {
  document: CardForgeDocument | null
  legacyConfig: any | null
  frontSvg: string | null
  backSvg: string | null
  manufacturingReport: ManufacturingReport | null
  selectedFeatureId: string | null
  errors: string[]
}

interface StudioActions {
  setDocument: (doc: CardForgeDocument) => void
  setLegacyConfig: (config: any) => void
  setFrontSvg: (svg: string) => void
  setBackSvg: (svg: string) => void
  setManufacturingReport: (report: ManufacturingReport) => void
  selectFeature: (featureId: string | null) => void
  addError: (error: string) => void
  clearErrors: () => void
  getObjects: () => DocumentObject[]
  getFaces: (obj: DocumentObject) => Record<string, Face>
  getFeatures: (obj: DocumentObject, faceId: string) => Feature[]
  getSelectedFeature: () => Feature | null
}

const StudioContext = createContext<{
  state: StudioState
  actions: StudioActions
} | null>(null)

const emptyState: StudioState = {
  document: null,
  legacyConfig: null,
  frontSvg: null,
  backSvg: null,
  manufacturingReport: null,
  selectedFeatureId: null,
  errors: [],
}

export function StudioProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<StudioState>(emptyState)

  const setDocument = useCallback((doc: CardForgeDocument) =>
    setState(s => ({ ...s, document: doc, errors: [] })), [])

  const setLegacyConfig = useCallback((config: any) =>
    setState(s => ({ ...s, legacyConfig: config })), [])

  const setFrontSvg = useCallback((svg: string) =>
    setState(s => ({ ...s, frontSvg: svg })), [])

  const setBackSvg = useCallback((svg: string) =>
    setState(s => ({ ...s, backSvg: svg })), [])

  const setManufacturingReport = useCallback((report: ManufacturingReport) =>
    setState(s => ({ ...s, manufacturingReport: report })), [])

  const selectFeature = useCallback((featureId: string | null) =>
    setState(s => ({ ...s, selectedFeatureId: featureId })), [])

  const addError = useCallback((error: string) =>
    setState(s => ({ ...s, errors: [...s.errors, error] })), [])

  const clearErrors = useCallback(() =>
    setState(s => ({ ...s, errors: [] })), [])

  const getObjects = useCallback(() =>
    state.document?.objects ?? [], [state.document])

  const getFaces = useCallback((obj: DocumentObject) =>
    obj.faces ?? {}, [])

  const getFeatures = useCallback((obj: DocumentObject, faceId: string) =>
    obj.faces[faceId]?.features ?? [], [])

  const getSelectedFeature = useCallback((): Feature | null => {
    if (!state.selectedFeatureId || !state.document) return null
    for (const obj of state.document.objects) {
      for (const face of Object.values(obj.faces)) {
        for (const feat of face.features) {
          if (feat.id === state.selectedFeatureId) return feat
        }
      }
    }
    // Also check legacy config
    if (state.legacyConfig) {
      for (const faceId of ['front', 'back']) {
        const face = state.legacyConfig.faces?.[faceId]
        if (face?.features) {
          for (const feat of face.features) {
            if (feat.id === state.selectedFeatureId) return feat
          }
        }
      }
    }
    return null
  }, [state.selectedFeatureId, state.document, state.legacyConfig])

  const actions: StudioActions = {
    setDocument, setLegacyConfig, setFrontSvg, setBackSvg,
    setManufacturingReport, selectFeature, addError, clearErrors,
    getObjects, getFaces, getFeatures, getSelectedFeature,
  }

  return (
    <StudioContext.Provider value={{ state, actions }}>
      {children}
    </StudioContext.Provider>
  )
}

export function useStudio() {
  const ctx = useContext(StudioContext)
  if (!ctx) throw new Error('useStudio must be used within StudioProvider')
  return ctx
}
