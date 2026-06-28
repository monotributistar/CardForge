import { useState } from 'react'
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
    height: 100, background: '#161b22', borderTop: '1px solid #30363d',
    display: 'flex', alignItems: 'center', padding: '0 16px',
  },
}

export default function App() {
  const [project, setProject] = useState('card-minimal')

  return (
    <div style={STUDIO_STYLE.container}>
      <div style={STUDIO_STYLE.topBar}>
        <TopBar project={project} onBuild={() => {}} />
      </div>
      <div style={STUDIO_STYLE.main}>
        <div style={STUDIO_STYLE.leftPanel}>
          <LeftPanel />
        </div>
        <div style={STUDIO_STYLE.canvas}>
          <Canvas project={project} />
        </div>
        <div style={STUDIO_STYLE.rightPanel}>
          <RightPanel />
        </div>
      </div>
      <div style={STUDIO_STYLE.bottomPanel}>
        <BottomPanel />
      </div>
    </div>
  )
}
