import React, { useRef } from 'react'
import { useStudio } from '../state/studioStore'
import { readFileAsText, parseDocumentFile, parseReportFile, detectFileType } from '../utils/loader'

const BAR_STYLE: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex', alignItems: 'center', gap: 12,
    width: '100%', justifyContent: 'space-between',
  },
  left: { display: 'flex', alignItems: 'center', gap: 8 },
  title: { fontWeight: 700, fontSize: 14, color: '#58a6ff' },
  badge: { fontSize: 10, background: '#238636', color: '#fff', padding: '1px 6px', borderRadius: 8 },
  project: { fontSize: 13, color: '#8b949e' },
  btn: {
    background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d',
    padding: '3px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 12,
  },
  btnPrimary: {
    background: '#238636', color: '#fff', border: '1px solid #2ea043',
    padding: '3px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 12,
  },
}

export default function TopBar() {
  const { state, actions } = useStudio()
  const fileRef = useRef<HTMLInputElement>(null)

  const handleLoad = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files) return
    actions.clearErrors()

    for (const file of Array.from(files)) {
      try {
        const content = await readFileAsText(file)
        const type = detectFileType(file.name)

        if (type === 'document' || type === 'config') {
          const doc = parseDocumentFile(content)
          actions.setDocument(doc)
        } else if (type === 'report') {
          const report = parseReportFile(content)
          actions.setManufacturingReport(report)
        } else if (type === 'svg') {
          if (file.name.toLowerCase().includes('front') || files.length === 1) {
            actions.setFrontSvg(content)
          }
          if (file.name.toLowerCase().includes('back')) {
            actions.setBackSvg(content)
          }
          // If only one SVG loaded without front/back indicator, use as both
          if (files.length === 1 && !file.name.toLowerCase().includes('front') && !file.name.toLowerCase().includes('back')) {
            actions.setFrontSvg(content)
          }
        } else {
          actions.addError(`Unknown file type: ${file.name}`)
        }
      } catch (err: any) {
        actions.addError(`${file.name}: ${err.message}`)
      }
    }
    // Reset input
    if (fileRef.current) fileRef.current.value = ''
  }

  const projectName = state.document?.document?.name ?? 'No document loaded'

  return (
    <div style={BAR_STYLE.container}>
      <div style={BAR_STYLE.left}>
        <span style={BAR_STYLE.title}>CardForge Studio</span>
        <span style={BAR_STYLE.badge}>v0.1</span>
        <span style={BAR_STYLE.project}>— {projectName}</span>
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          ref={fileRef}
          type="file"
          multiple
          accept=".json,.svg,.cardforge.json"
          onChange={handleLoad}
          style={{ display: 'none' }}
          id="file-input"
        />
        <button style={BAR_STYLE.btnPrimary} onClick={() => fileRef.current?.click()}>
          Load Files
        </button>
      </div>
    </div>
  )
}
