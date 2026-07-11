// UIStore — cross-cutting UI chrome state: splash, wizard, issues drawer,
// mobile panel drawer. Document data stays in DocumentStore.

import { create } from 'zustand'

const SPLASH_PREF_KEY = 'cardforge.splash.show'

/** User preference: show the welcome splash at startup (default on). */
export function splashEnabledAtStartup(): boolean {
  try { return localStorage.getItem(SPLASH_PREF_KEY) !== '0' } catch { return true }
}

export function setSplashEnabledAtStartup(on: boolean): void {
  try { localStorage.setItem(SPLASH_PREF_KEY, on ? '1' : '0') } catch { /* storage unavailable */ }
}

interface UIState {
  splashOpen: boolean
  wizardOpen: boolean
  /** Issues drawer above the status bar. */
  issuesOpen: boolean
  /** Right side panel as overlay drawer (narrow viewports). */
  panelOpen: boolean
  openSplash: () => void
  closeSplash: () => void
  openWizard: () => void
  closeWizard: () => void
  toggleIssues: () => void
  setPanelOpen: (open: boolean) => void
}

export const useUIStore = create<UIState>(set => ({
  splashOpen: splashEnabledAtStartup(),
  wizardOpen: false,
  issuesOpen: false,
  panelOpen: false,
  openSplash: () => set({ splashOpen: true }),
  closeSplash: () => set({ splashOpen: false }),
  openWizard: () => set({ wizardOpen: true, splashOpen: false }),
  closeWizard: () => set({ wizardOpen: false }),
  toggleIssues: () => set(s => ({ issuesOpen: !s.issuesOpen })),
  setPanelOpen: (open) => set({ panelOpen: open }),
}))
