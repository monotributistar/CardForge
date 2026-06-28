// MoveFeatureCommand — moves a feature on the canvas
import type { Command } from '../commands/CommandManager'
import { findFeature } from '../document/DocumentEditor'
import type { CardForgeDocument } from '../../types/cardforge'

export class MoveFeatureCommand implements Command {
  readonly id = 'move-feature'
  readonly label = 'Move Feature'

  private fromPosition: { x: number; y: number } | null = null

  constructor(
    private doc: { current: CardForgeDocument | null },
    private featureId: string,
    private toX: number,
    private toY: number,
    private onChange: () => void,
  ) {}

  execute() {
    if (!this.doc.current) return
    const feat = findFeature(this.doc.current, this.featureId)
    if (!feat?.position) return

    // Save fromPosition for future undo
    this.fromPosition = { x: feat.position.x, y: feat.position.y }

    feat.position.x = this.toX
    feat.position.y = this.toY
    this.onChange()
  }
}
