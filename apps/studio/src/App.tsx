import React from 'react'
import { StudioProvider } from './state/studioStore'
import TopBar from './components/TopBar'
import LeftPanel from './components/LeftPanel'
import Canvas from './components/Canvas'
import RightPanel from './components/RightPanel'
import BottomPanel from './components/BottomPanel'

const STUDIO_STYLE: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex', flexDirection: 'column', height: '100vh',
    background: '#0d1117', color: '#c9d1d9',
  },
  topBar: {
    height: 40, background: '#161b22', borderBottom: '1px solid #30363d',
    display: 'flex', alignItems: 'center', padding: '0 12px',
  },
  main: {
    display: 'flex', flex: 1, overflow: 'hidden',
  },
  leftPanel: {
    width: 220, background: '#161b22', borderRight: '1px solid #30363d',
    overflow: 'auto', padding: 12,
  },
  canvas: {
    flex: 1, background: '#0d1117', display: 'flex',
    alignItems: 'center', justifyContent: 'center', overflow: 'auto',
  },
  rightPanel: {
    width: 260, background: '#161b22', borderLeft: '1px solid #30363d',
    overflow: 'auto', padding: 12,
  },
  bottomPanel: {
    minHeight: 80, background: '#161b22', borderTop: '1px solid #30363d',
    display: 'flex', alignItems: 'center', padding: '0 16px',
  },
}

export default function App() {
  return (
    <StudioProvider>
      <div style={STUDIO_STYLE.container}>
        <div style={STUDIO_STYLE.topBar}>
          <TopBar />
        </div>
        <div style={STUDIO_STYLE.main}>
          <div style={STUDIO_STYLE.leftPanel}>
            <LeftPanel />
          </div>
          <div style={STUDIO_STYLE.canvas}>
            <Canvas />
          </div>
          <div style={STUDIO_STYLE.rightPanel}>
            <RightPanel />
          </div>
        </div>
        <div style={STUDIO_STYLE.bottomPanel}>
          <BottomPanel />
        </div>
      </div>
    </StudioProvider>
  )
}
