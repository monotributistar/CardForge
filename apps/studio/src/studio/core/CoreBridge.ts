// CoreBridge — connects Studio to the Core Compiler
//
// Currently uses CLI subprocess (via local shell).
// In the future, can be replaced with HTTP, WebSocket, or IPC
// without changing any React component.

import type { CorePreviewResponse, CoreCompileResponse, CorePublishResponse } from './CoreProtocol'

export interface BridgeOptions {
  /** CLI command to invoke */
  command: string
  /** Working directory */
  cwd?: string
  /** Timeout in ms */
  timeout?: number
}

/** Parse raw JSON from CLI stdout into typed response */
function parseResponse<T>(stdout: string): T {
  try {
    return JSON.parse(stdout) as T
  } catch {
    throw new Error(`Failed to parse Core response: ${stdout.slice(0, 200)}`)
  }
}

/** Execute a Core CLI command via the Bridge */
async function executeCoreCli(command: string, documentPath: string): Promise<string> {
  // In a real browser environment, this would call a local server or use
  // a WASM build. For now, we provide the interface.
  //
  // Future implementations:
  //   - HTTP: fetch('http://localhost:9000/preview', { body: document })
  //   - WASM: wasmCore.preview(documentJson)
  //   - IPC:  electron.ipcRenderer.invoke('core:preview', documentPath)

  throw new Error(
    `Core CLI not available in browser. Run from terminal:\n` +
    `  uv run python scripts/core_cli.py ${command} ${documentPath}`
  )
}

/** CoreBridge — the single entry point for Studio→Core communication */
export class CoreBridge {
  /**
   * Request a preview (SVG + manufacturing report) from the Core.
   * Falls back to CompileService if bridge is unavailable.
   */
  static async preview(documentPath: string): Promise<CorePreviewResponse> {
    const stdout = await executeCoreCli('preview', documentPath)
    return parseResponse<CorePreviewResponse>(stdout)
  }

  /**
   * Request a full compile (preview + geometry info) from the Core.
   */
  static async compile(documentPath: string): Promise<CoreCompileResponse> {
    const stdout = await executeCoreCli('compile', documentPath)
    return parseResponse<CoreCompileResponse>(stdout)
  }

  /**
   * Request a publish manifest from the Core.
   */
  static async publish(documentPath: string): Promise<CorePublishResponse> {
    const stdout = await executeCoreCli('publish', documentPath)
    return parseResponse<CorePublishResponse>(stdout)
  }
}
