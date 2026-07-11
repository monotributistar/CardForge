// Splash — design-app style welcome screen: new-card wizard, open file,
// recent documents, donations placeholder. Shown at startup (preference)
// and reopenable from the MenuBar brand.

import React, { useState } from 'react'
import { listStoredDocuments, openStoredDocument, deleteStoredDocument, type StoredDocInfo } from '../state/DocumentStore'
import { openDocumentViaDialog } from '../state/fileio'
import { useUIStore, splashEnabledAtStartup, setSplashEnabledAtStartup } from '../state/UIStore'
import { Overlay, Btn, useIsNarrow } from './ui'

// Donations link — placeholder until a real page exists. When empty, the
// chip renders disabled with a “coming soon” note.
const DONATION_URL = ''

export const Splash: React.FC = () => {
  const closeSplash = useUIStore(s => s.closeSplash)
  const openWizard = useUIStore(s => s.openWizard)
  const narrow = useIsNarrow()
  const [docs, setDocs] = useState<StoredDocInfo[]>(() => listStoredDocuments())
  const [showAtStartup, setShowAtStartup] = useState(() => splashEnabledAtStartup())

  const openRecent = (id: string) => { openStoredDocument(id); closeSplash() }
  const openFile = () => { closeSplash(); void openDocumentViaDialog() }

  return (
    <Overlay onClose={closeSplash}>
      <div style={{
        width: 760, maxWidth: '94vw', maxHeight: '90vh', overflowY: 'auto',
        background: '#161b22', border: '1px solid #30363d', borderRadius: 12,
        boxShadow: '0 12px 40px rgba(0,0,0,0.6)', display: 'flex', flexDirection: 'column',
      }}>
        <div style={{ display: 'flex', flexDirection: narrow ? 'column' : 'row' }}>
          {/* ── Left: brand + actions ─────────────────────────────── */}
          <div style={{ flex: 1.1, padding: '28px 28px 20px', display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 2 }}>
              <span style={{ fontSize: 34, lineHeight: 1 }}>◨</span>
              <div>
                <div style={{ fontSize: 20, fontWeight: 700, color: '#e6edf3' }}>CardForge <span style={{ color: '#58a6ff' }}>Studio</span></div>
                <div style={{ fontSize: 12, color: '#8b949e' }}>Design multicolor 3D-printed cards, tags & badges</div>
              </div>
            </div>

            <Btn primary onClick={openWizard} style={{ justifyContent: 'flex-start', textAlign: 'left', display: 'flex', gap: 10, alignItems: 'center', padding: '12px 14px' }}>
              <span style={{ fontSize: 18 }}>✚</span>
              <span>
                <div style={{ fontWeight: 600 }}>New card…</div>
                <div style={{ fontSize: 11, opacity: 0.85 }}>Guided setup: template, size, materials</div>
              </span>
            </Btn>

            <Btn onClick={openFile} style={{ justifyContent: 'flex-start', textAlign: 'left', display: 'flex', gap: 10, alignItems: 'center', padding: '12px 14px' }}>
              <span style={{ fontSize: 18 }}>📂</span>
              <span>
                <div style={{ fontWeight: 600 }}>Open file…</div>
                <div style={{ fontSize: 11, color: '#8b949e' }}>Load a .cardforge.json document</div>
              </span>
            </Btn>

            {/* Donations placeholder */}
            <Btn
              disabled={!DONATION_URL}
              onClick={() => { if (DONATION_URL) window.open(DONATION_URL, '_blank', 'noopener') }}
              title={DONATION_URL ? 'Support the project' : 'Donations page coming soon'}
              style={{ justifyContent: 'flex-start', textAlign: 'left', display: 'flex', gap: 10, alignItems: 'center', padding: '12px 14px', borderStyle: 'dashed' }}
            >
              <span style={{ fontSize: 18 }}>☕</span>
              <span>
                <div style={{ fontWeight: 600 }}>Support CardForge</div>
                <div style={{ fontSize: 11, color: '#8b949e' }}>{DONATION_URL ? 'Buy the project a coffee' : 'Donations — coming soon'}</div>
              </span>
            </Btn>
          </div>

          {/* ── Right: recent documents ───────────────────────────── */}
          <div style={{
            flex: 1, padding: '28px 24px 20px', borderLeft: narrow ? 'none' : '1px solid #21262d',
            borderTop: narrow ? '1px solid #21262d' : 'none', minWidth: 0,
          }}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.6, color: '#8b949e', marginBottom: 10 }}>
              Recent
            </div>
            {docs.length === 0 && (
              <div style={{ fontSize: 12, color: '#484f58', padding: '8px 0' }}>
                Nothing here yet — documents auto-save in your browser as you work.
              </div>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2, maxHeight: 300, overflowY: 'auto' }}>
              {docs.map(d => (
                <div
                  key={d.id}
                  onClick={() => openRecent(d.id)}
                  style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 8px', cursor: 'pointer', borderRadius: 6, fontSize: 13, color: '#c9d1d9' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = '#21262d' }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent' }}
                >
                  <span style={{ color: '#8b949e', flexShrink: 0 }}>🗂</span>
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.name}</span>
                  <span style={{ fontSize: 10, color: '#484f58', flexShrink: 0 }}>{d.savedAt.slice(0, 16).replace('T', ' ')}</span>
                  <button
                    title="Delete from browser storage"
                    onClick={e => { e.stopPropagation(); deleteStoredDocument(d.id); setDocs(listStoredDocuments()) }}
                    style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: 12, padding: '2px 4px', flexShrink: 0 }}
                  >🗑</button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── Footer ────────────────────────────────────────────────── */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10, padding: '10px 28px',
          borderTop: '1px solid #21262d', fontSize: 12, color: '#8b949e',
        }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 7, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={showAtStartup}
              onChange={e => { setShowAtStartup(e.target.checked); setSplashEnabledAtStartup(e.target.checked) }}
              style={{ width: 15, height: 15 }}
            />
            Show at startup
          </label>
          <span style={{ flex: 1 }} />
          <button
            onClick={closeSplash}
            style={{ background: 'transparent', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: 12, padding: '6px 10px' }}
          >Close ✕</button>
        </div>
      </div>
    </Overlay>
  )
}
