// Services — bridge between Studio UI and Core compiler
//
// Placeholder services. In future phases these will:
//   - DocumentService: load/save .cardforge.json
//   - BuildService: trigger Core builds via API
//   - PreviewService: manage SVG previews

export class DocumentService {
  static loadFromFile(file: File): Promise<any> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => {
        try { resolve(JSON.parse(reader.result as string)) }
        catch (e) { reject(e) }
      }
      reader.onerror = () => reject(new Error(`Failed to read ${file.name}`))
      reader.readAsText(file)
    })
  }
}

export class BuildService {
  static async build(documentId: string): Promise<void> {
    // Placeholder — future: POST to local Core API
    console.log(`Build requested for: ${documentId}`)
  }
}

export class PreviewService {
  static getPreviewPath(documentId: string, face: 'front' | 'back'): string {
    return `exports/${documentId}/preview/${face}.svg`
  }
}
