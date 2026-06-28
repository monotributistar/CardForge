// Commands — command pattern infrastructure for all user actions
//
// Every user action goes through a Command. This enables:
//   - Undo / Redo (future)
//   - Macros (future)
//   - Keyboard shortcuts (future)
//   - AI actions (future)
//   - Collaboration (future)
//
// The CommandManager is the central dispatcher for the Studio.

import type { FeatureId, FaceId } from '../types'
import type { Workspace } from '../workspace/Workspace'
import type { Scene } from '../scene/Scene'
import type { SelectionModel } from '../selection/Selection'
import type { Viewport } from '../viewport/Viewport'

// ── Command interface ──────────────────────────────────────────────────────

export interface Command {
  readonly id: string
  readonly label: string
  execute(): void
  undo?(): void
  redo?(): void
}

// ── Command context ────────────────────────────────────────────────────────

/** Context passed to all commands — gives access to Studio state */
export interface CommandContext {
  workspace: Workspace
  scene: Scene
  selection: SelectionModel
  viewport: Viewport
}

// ── Concrete commands (placeholders) ───────────────────────────────────────

export class SelectFeatureCommand implements Command {
  readonly id = 'select-feature'
  readonly label = 'Select Feature'

  constructor(
    private ctx: CommandContext,
    private featureId: FeatureId | null,
  ) {}

  execute() {
    this.ctx.selection.actions.select(this.featureId)
  }
}

export class OpenDocumentCommand implements Command {
  readonly id = 'open-document'
  readonly label = 'Open Document'

  constructor(
    private ctx: CommandContext,
    private document: any,
  ) {}

  execute() {
    this.ctx.workspace.actions.openDocument(this.document)
    this.ctx.selection.actions.clear()
  }
}

export class ZoomCommand implements Command {
  readonly id = 'zoom'
  readonly label = 'Zoom'

  constructor(
    private ctx: CommandContext,
    private direction: 'in' | 'out' | 'reset',
  ) {}

  execute() {
    if (this.direction === 'in') this.ctx.viewport.actions.zoomIn()
    else if (this.direction === 'out') this.ctx.viewport.actions.zoomOut()
    else this.ctx.viewport.actions.resetZoom()
  }
}

export class FitCanvasCommand implements Command {
  readonly id = 'fit-canvas'
  readonly label = 'Fit Canvas'

  constructor(private ctx: CommandContext) {}

  execute() {
    this.ctx.viewport.actions.fitToView()
  }
}

export class ToggleFaceCommand implements Command {
  readonly id = 'toggle-face'
  readonly label = 'Toggle Face'

  constructor(private ctx: CommandContext) {}

  execute() {
    this.ctx.scene.actions.toggleActiveFace()
  }
}

// ── Command manager ────────────────────────────────────────────────────────

export interface CommandManagerState {
  history: Command[]
  historyIndex: number
  maxHistory: number
}

export class CommandManager {
  state: CommandManagerState

  constructor(private ctx: CommandContext) {
    this.state = {
      history: [],
      historyIndex: -1,
      maxHistory: 100,
    }
  }

  /** Execute a command and add it to history */
  execute(command: Command): void {
    command.execute()
    // Trim future history if we're not at the end
    this.state.history = this.state.history.slice(0, this.state.historyIndex + 1)
    this.state.history.push(command)
    if (this.state.history.length > this.state.maxHistory) {
      this.state.history.shift()
    }
    this.state.historyIndex = this.state.history.length - 1
  }

  /** Undo the last command (placeholder — not implemented) */
  undo(): void {
    throw new Error('Undo not implemented')
  }

  /** Redo the last undone command (placeholder — not implemented) */
  redo(): void {
    throw new Error('Redo not implemented')
  }

  get canUndo(): boolean { return false }
  get canRedo(): boolean { return false }
  get historyLength(): number { return this.state.history.length }
}
