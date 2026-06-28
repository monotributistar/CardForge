// PublishDialog — shows publish summary + CLI command + downloads document

import React, { useState } from 'react'
import type { PublishResult } from './PublishService'

interface PublishDialogProps {
  result: PublishResult | null
  documentJson: string | null
  documentId: string
  onClose: () => void
}

const S = {
  overlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 } as React.CSSProperties,
  dialog: { background: '#161b22', border: '1px solid #30363d', borderRadius: 12, padding: 24, maxWidth: 520, width: '90%', maxHeight: '85vh', overflow: 'auto', color: '#c9d1d9' } as React.CSSProperties,
  title: { fontSize: 18, fontWeight: 700, color: '#58a6ff', marginBottom: 16 } as React.CSSProperties,
  section: { marginBottom: 14 } as React.CSSProperties,
  st: { fontSize: 11, fontWeight: 600, color: '#8b949e', textTransform: 'uppercase' as const, marginBottom: 6 },
  row: { display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '2px 0' },
  label: { color: '#8b949e' },
  value: { color: '#c9d1d9' },
  cmdBox: { background: '#0d1117', border: '1px solid #30363d', borderRadius: 6, padding: 10, fontFamily: 'monospace', fontSize: 11, color: '#7ee787', marginTop: 4, overflowX: 'auto' as const, whiteSpace: 'pre-wrap' as const },
  btnRow: { display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 },
  btn: { background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d', padding: '6px 14px', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
  btnPrimary: { background: '#238636', color: '#fff', border: '1px solid #2ea043', padding: '6px 14px', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 600 },
  copied: { fontSize: 11, color: '#3fb950', marginLeft: 8 },
}

export const PublishDialog: React.FC<PublishDialogProps> = ({ result, documentJson, documentId, onClose }) => {
  const [copied, setCopied] = useState(false)

  if (!result) return null
  const m = result.manifest
  const cliCmd = `uv run python scripts/build.py ${documentId}.cardforge.json --prototype --clean`

  const copyCmd = async () => {
    try {
      await navigator.clipboard.writeText(cliCmd)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback: select text
    }
  }

  const downloadDocument = () => {
    if (!documentJson) return
    const blob = new Blob([documentJson], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${documentId}.cardforge.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div style={S.overlay} onClick={onClose}>
      <div style={S.dialog} onClick={e => e.stopPropagation()}>
        <div style={S.title}>Publish Manufacturing Package</div>

        <div style={S.section}>
          <div style={S.st}>Step 1 — Save Document</div>
          <div style={{ fontSize: 12, color: '#8b949e', marginBottom: 8 }}>
            Download your .cardforge.json file first.
          </div>
          <button style={S.btnPrimary} onClick={downloadDocument}>
            Download {documentId}.cardforge.json
          </button>
        </div>

        <div style={S.section}>
          <div style={S.st}>Step 2 — Generate STL Files</div>
          <div style={{ fontSize: 12, color: '#8b949e', marginBottom: 4 }}>
            Run this command in your terminal to generate all printable files:
          </div>
          <div style={S.cmdBox}>
            {cliCmd}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', marginTop: 6 }}>
            <button style={{ ...S.btn, fontSize: 11 }} onClick={copyCmd}>
              {copied ? 'Copied!' : 'Copy command'}
            </button>
            {copied && <span style={S.copied}>✓ Copied to clipboard</span>}
          </div>
        </div>

        <div style={S.section}>
          <div style={S.st}>Step 3 — What You'll Get</div>
          <div style={{ fontSize: 11, color: '#8b949e', lineHeight: 1.6 }}>
            exports/{documentId}/<br/>
            {'  '}├── document/resolved.cardforge.json<br/>
            {'  '}├── preview/front.svg · back.svg<br/>
            {'  '}├── reports/manufacturing_report.json · .md<br/>
            {'  '}├── scad/generated.scad<br/>
            {'  '}├── stl/card_single.stl<br/>
            {'  '}├── stl/parts/01_base_pla.stl<br/>
            {'  '}├── stl/parts/02_text_pla.stl<br/>
            {'  '}├── stl/parts/03_accent_pla.stl<br/>
            {'  '}├── print/README_PRINT.md<br/>
            {'  '}└── manifest.json
          </div>
        </div>

        {result.manifest.score < 80 && (
          <div style={{ ...S.section, background: '#da363322', borderRadius: 6, padding: 10 }}>
            <div style={{ fontSize: 12, color: '#f85149' }}>
              ⚠️ Score: {result.manifest.score}/100 — review warnings before printing
            </div>
          </div>
        )}

        <div style={S.btnRow}>
          <button style={S.btn} onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}
