// Edit Commands — mutations on the Document
//
// All document editing goes through these commands.
// Executed via CommandManager for future undo/redo support.

import type { Command, CommandContext } from './CommandManager'
import type { CardForgeDocument } from '../../types/cardforge'
import { updateFeatureField, updateDocumentVariable } from '../document/DocumentEditor'

export class UpdateTextCommand implements Command {
  readonly id = 'update-text'
  readonly label = 'Update Text'

  constructor(
    private doc: { current: CardForgeDocument | null },
    private featureId: string,
    private lines: string[],
    private onChange: () => void,
  ) {}

  execute() {
    if (!this.doc.current) return
    updateFeatureField(this.doc.current, this.featureId, 'lines', this.lines)
    this.onChange()
  }
}

export class UpdateFontSizeCommand implements Command {
  readonly id = 'update-font-size'
  readonly label = 'Update Font Size'

  constructor(
    private doc: { current: CardForgeDocument | null },
    private featureId: string,
    private fontSize: number,
    private onChange: () => void,
  ) {}

  execute() {
    if (!this.doc.current) return
    updateFeatureField(this.doc.current, this.featureId, 'fontSize', this.fontSize)
    this.onChange()
  }
}

export class UpdateReliefCommand implements Command {
  readonly id = 'update-relief'
  readonly label = 'Update Relief'

  constructor(
    private doc: { current: CardForgeDocument | null },
    private featureId: string,
    private height: number,
    private onChange: () => void,
  ) {}

  execute() {
    if (!this.doc.current) return
    updateFeatureField(this.doc.current, this.featureId, 'reliefHeight', this.height)
    this.onChange()
  }
}

export class UpdateMaterialCommand implements Command {
  readonly id = 'update-material'
  readonly label = 'Update Material'

  constructor(
    private doc: { current: CardForgeDocument | null },
    private featureId: string,
    private material: string,
    private onChange: () => void,
  ) {}

  execute() {
    if (!this.doc.current) return
    updateFeatureField(this.doc.current, this.featureId, 'material', this.material)
    this.onChange()
  }
}

export class UpdateQRValueCommand implements Command {
  readonly id = 'update-qr-value'
  readonly label = 'Update QR Value'

  constructor(
    private doc: { current: CardForgeDocument | null },
    private featureId: string,
    private value: string,
    private onChange: () => void,
  ) {}

  execute() {
    if (!this.doc.current) return
    updateFeatureField(this.doc.current, this.featureId, 'value', this.value)
    this.onChange()
  }
}

export class UpdateQRSizeCommand implements Command {
  readonly id = 'update-qr-size'
  readonly label = 'Update QR Size'

  constructor(
    private doc: { current: CardForgeDocument | null },
    private featureId: string,
    private size: number,
    private onChange: () => void,
  ) {}

  execute() {
    if (!this.doc.current) return
    updateFeatureField(this.doc.current, this.featureId, 'size', this.size)
    this.onChange()
  }
}

export class UpdateVariableCommand implements Command {
  readonly id = 'update-variable'
  readonly label = 'Update Variable'

  constructor(
    private doc: { current: CardForgeDocument | null },
    private key: string,
    private value: string,
    private onChange: () => void,
  ) {}

  execute() {
    if (!this.doc.current) return
    updateDocumentVariable(this.doc.current, this.key, this.value)
    this.onChange()
  }
}
